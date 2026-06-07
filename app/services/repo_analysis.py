from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from app.schemas.analyze_repo import (
    AnalyzeRepoRequest,
    AnalyzeRepoResponse,
    DetectedTechnology,
    RepositoryScanSummary,
    TechnologyEvidence,
)
from app.services.technologies import Technology, match_technology


MAX_FILE_BYTES = 750_000
MAX_SCANNED_FILES = 2_000
MAX_EVIDENCE_PER_TECH = 12
CLONE_TIMEOUT_SECONDS = 300

SKIP_DIRS = {
    ".git",
    ".next",
    ".nuxt",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java"}
DEPENDENCY_FILENAMES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}

PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\.]+))")
JS_IMPORT_RE = re.compile(
    r"(?:from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|require\(\s*['\"]([^'\"]+)['\"]\s*\))"
)
JAVA_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_\.]+)")


@dataclass
class ScanState:
    evidence_by_key: dict[str, list[TechnologyEvidence]] = field(default_factory=lambda: defaultdict(list))
    tech_by_key: dict[str, Technology] = field(default_factory=dict)
    scanned_files: int = 0
    truncated: bool = False

    @property
    def evidence_count(self) -> int:
        return sum(len(items) for items in self.evidence_by_key.values())


def analyze_repository(request: AnalyzeRepoRequest) -> AnalyzeRepoResponse:
    repo_url = normalize_github_url(request.repo_url)
    start = time.monotonic()

    with TemporaryDirectory(prefix="phase2-repo-") as tmp_dir:
        repo_dir = Path(tmp_dir) / "repo"
        clone_repository(repo_url, repo_dir)
        clone_seconds = round(time.monotonic() - start, 2)
        state = scan_repository(repo_dir)

    return AnalyzeRepoResponse(
        projectId=request.project_id,
        repoUrl=repo_url,
        detectedTechs=build_detected_technologies(state),
        repository=RepositoryScanSummary(
            scannedFiles=state.scanned_files,
            evidenceCount=state.evidence_count,
            truncated=state.truncated,
            cloneSeconds=clone_seconds,
        ),
    )


def normalize_github_url(repo_url: str) -> str:
    parsed = urlparse(repo_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        raise ValueError("repoUrl must be a public GitHub HTTPS URL.")

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("repoUrl must include an owner and repository name.")

    owner, repo = parts[0], parts[1].removesuffix(".git")
    return f"https://github.com/{owner}/{repo}.git"


def clone_repository(repo_url: str, destination: Path) -> None:
    git_path = shutil.which("git")
    if not git_path:
        raise ValueError("git is required to analyze repositories.")

    command = [git_path, "clone", "--depth", "1", repo_url, str(destination)]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=CLONE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Repository clone timed out after 5 minutes.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Repository clone failed: {stderr}") from exc


def scan_repository(repo_dir: Path) -> ScanState:
    state = ScanState()
    for path in walk_repo_files(repo_dir):
        if state.scanned_files >= MAX_SCANNED_FILES:
            state.truncated = True
            break

        state.scanned_files += 1
        relative_path = path.relative_to(repo_dir).as_posix()
        scan_file(path, relative_path, state)

    return state


def walk_repo_files(repo_dir: Path):
    for path in repo_dir.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        if path.name in DEPENDENCY_FILENAMES or path.suffix in SOURCE_SUFFIXES or ".github/workflows" in path.as_posix():
            yield path


def scan_file(path: Path, relative_path: str, state: ScanState) -> None:
    if path.name == "package.json":
        scan_package_json(path, relative_path, state)
        return
    if path.name == "requirements.txt":
        scan_requirements(path, relative_path, state)
        return
    if path.name == "pyproject.toml":
        scan_pyproject(path, relative_path, state)
        return
    if path.name == "Dockerfile":
        add_detection("docker", relative_path, 1, "Dockerfile present", "dockerfile", state)
        return
    if path.name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}:
        add_detection("docker-compose", relative_path, 1, f"{path.name} present", "docker-compose", state)
        return
    if ".github/workflows" in relative_path:
        add_detection("github-actions", relative_path, 1, "GitHub Actions workflow present", "workflow", state)
        return

    scan_imports(path, relative_path, state)


def scan_package_json(path: Path, relative_path: str, state: ScanState) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    dependency_blocks = [
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ]
    for block in dependency_blocks:
        for name, version in data.get(block, {}).items():
            add_detection(name, relative_path, find_line(path, f'"{name}"'), f'"{name}": "{version}"', block, state)

    scripts = data.get("scripts", {})
    if any("next" in command for command in scripts.values()):
        add_detection("next", relative_path, find_line(path, '"scripts"'), "package script references next", "package-script", state)


def scan_requirements(path: Path, relative_path: str, state: ScanState) -> None:
    for line_number, line in enumerate(read_lines(path), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name = re.split(r"[<>=~!\[]", stripped, maxsplit=1)[0].strip()
        add_detection(name, relative_path, line_number, stripped, "requirements", state)


def scan_pyproject(path: Path, relative_path: str, state: ScanState) -> None:
    for line_number, line in enumerate(read_lines(path), start=1):
        stripped = line.strip().strip(",").strip("\"'")
        if not stripped or stripped.startswith("#"):
            continue
        name = re.split(r"[<>=~!\[]", stripped, maxsplit=1)[0].strip()
        add_detection(name, relative_path, line_number, line.strip(), "pyproject", state)


def scan_imports(path: Path, relative_path: str, state: ScanState) -> None:
    for line_number, line in enumerate(read_lines(path), start=1):
        modules = extract_import_modules(line, path.suffix)
        for module in modules:
            add_detection(module, relative_path, line_number, line.strip(), "import", state)


def extract_import_modules(line: str, suffix: str) -> list[str]:
    if suffix == ".py":
        match = PY_IMPORT_RE.search(line)
        return [part for part in match.groups() if part] if match else []
    if suffix == ".java":
        match = JAVA_IMPORT_RE.search(line)
        return [match.group(1)] if match else []
    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        modules: list[str] = []
        for match in JS_IMPORT_RE.finditer(line):
            modules.extend(part for part in match.groups() if part)
        return modules
    return []


def add_detection(
    candidate: str,
    relative_path: str,
    line: int,
    snippet: str,
    source: str,
    state: ScanState,
) -> None:
    tech = match_technology(candidate)
    if tech is None:
        return

    evidence = state.evidence_by_key[tech.key]
    if len(evidence) >= MAX_EVIDENCE_PER_TECH:
        return

    state.tech_by_key[tech.key] = tech
    if not any(item.file == relative_path and item.line == line and item.snippet == snippet for item in evidence):
        evidence.append(
            TechnologyEvidence(
                file=relative_path,
                line=line,
                snippet=snippet[:240],
                source=source,
            )
        )


def build_detected_technologies(state: ScanState) -> list[DetectedTechnology]:
    results: list[DetectedTechnology] = []
    for key in sorted(state.evidence_by_key):
        tech = state.tech_by_key[key]
        results.append(
            DetectedTechnology(
                key=tech.key,
                name=tech.name,
                category=tech.category,
                confidence=confidence_for_evidence(state.evidence_by_key[key]),
                evidence=state.evidence_by_key[key],
            )
        )
    return results


def confidence_for_evidence(evidence: list[TechnologyEvidence]) -> str:
    sources = {item.source for item in evidence}
    if sources & {"dependencies", "devDependencies", "peerDependencies", "optionalDependencies", "requirements", "pyproject"}:
        return "high"
    if sources & {"dockerfile", "docker-compose", "workflow", "import", "package-script"}:
        return "medium"
    return "low"


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def find_line(path: Path, needle: str) -> int:
    for line_number, line in enumerate(read_lines(path), start=1):
        if needle in line:
            return line_number
    return 1
