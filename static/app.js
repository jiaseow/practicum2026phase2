const state = {
  projectId: null,
  repoUrl: null,
  description: null,
  videoPath: null,
  transcriptFile: null,
  transcriptText: null,
  transcriptSourceName: null,
  transcription: null,
  comparison: null,
  report: null,
};

const OPENAI_AUDIO_UPLOAD_LIMIT_BYTES = 25 * 1024 * 1024;

const projectIdInput = document.querySelector("#projectId");
const repoInput = document.querySelector("#repoUrl");
const fileInput = document.querySelector("#videoFile");
const transcriptFileInput = document.querySelector("#transcriptFile");
const readmeInput = document.querySelector("#readmeFile");
const descriptionPreview = document.querySelector("#descriptionPreview");
const inputSummary = document.querySelector("#inputSummary");
const serverStatus = document.querySelector("#serverStatus");
const step1Status = document.querySelector("#step1Status");
const step2Status = ensureHiddenElement("step2Status", "span");
const step3Status = ensureHiddenElement("step3Status", "span");
const step4Status = document.querySelector("#step4Status");
const step1Button = document.querySelector("#step1Button");
const loadDefaultsButton = document.querySelector("#loadDefaultsButton");
const step2Button = ensureHiddenElement("step2Button", "button");
const step3Button = ensureHiddenElement("step3Button", "button");
const step4Button = ensureHiddenElement("step4Button", "button");
const searchButton = ensureHiddenElement("searchButton", "button");
const searchQuery = ensureHiddenElement("searchQuery", "input");
const transcriptViewer = ensureHiddenElement("transcriptViewer", "pre");
const searchResults = ensureHiddenElement("searchResults", "div");
const chunkCount = ensureHiddenElement("chunkCount", "span");
const durationValue = ensureHiddenElement("durationValue", "span");
const embeddingValue = ensureHiddenElement("embeddingValue", "span");
const claimedTechs = ensureHiddenElement("claimedTechs", "div");
const detectedTechs = ensureHiddenElement("detectedTechs", "div");
const verificationSummary = ensureHiddenElement("verificationSummary", "div");
const metricsGrid = document.querySelector("#metricsGrid");
const jsonViewer = document.querySelector("#jsonViewer");
const reportList = document.querySelector("#reportList");
const downloadButton = document.querySelector("#downloadReportButton");
const refreshReportsButton = document.querySelector("#refreshReportsButton");

function ensureHiddenElement(id, tagName) {
  const existing = document.querySelector(`#${id}`);
  if (existing) return existing;

  const element = document.createElement(tagName);
  element.id = id;
  element.hidden = true;
  element.setAttribute("aria-hidden", "true");
  if (tagName === "button") element.type = "button";
  document.body.appendChild(element);
  return element;
}

function init() {
  projectIdInput.value = `proj-${new Date().toISOString().slice(0, 10)}-${Math.floor(Math.random() * 1000)}`;
  repoInput.value = "https://github.com/pallets/flask";
  readmeInput.addEventListener("change", previewReadmeFile);
  loadDefaultsButton.addEventListener("click", loadDefaultInputs);
  step1Button.addEventListener("click", uploadInputs);
  step2Button.addEventListener("click", transcribeAndStore);
  step3Button.addEventListener("click", runAgentComparison);
  step4Button.addEventListener("click", generateReport);
  searchButton.addEventListener("click", searchTranscriptVectors);
  downloadButton.addEventListener("click", downloadReport);
  refreshReportsButton.addEventListener("click", loadReports);
  checkHealth();
  loadReports();
}

async function checkHealth() {
  try {
    await requestJson("/health");
    setPill(serverStatus, "Ready", "ok");
  } catch (error) {
    setPill(serverStatus, "Offline", "error");
  }
}

async function uploadInputs() {
  setBusy(true);
  setPill(step1Status, "Running", "busy");
  inputSummary.innerHTML = `
    <strong>Reading inputs...</strong>
    <p>Validating files and preparing the evidence workflow.</p>
  `;
  jsonViewer.textContent = "{}";
  try {
    const projectId = projectIdInput.value.trim();
    const repoUrl = repoInput.value.trim();
    if (!projectId) throw new Error("Project ID is required.");
    if (!repoUrl) throw new Error("GitHub repo URL is required.");
    const videoFile = fileInput.files[0] || null;
    const transcriptFile = transcriptFileInput.files[0] || null;
    const canUseLoadedDefaults = state.projectId === projectId && state.repoUrl === repoUrl;
    const loadedVideoPath = canUseLoadedDefaults ? state.videoPath : null;
    const loadedTranscriptText = canUseLoadedDefaults ? state.transcriptText : null;
    const loadedTranscriptSourceName = canUseLoadedDefaults ? state.transcriptSourceName : null;
    if (!videoFile && !transcriptFile && !loadedVideoPath && !loadedTranscriptText) {
      throw new Error("Upload an MP4 demo video or a transcript TXT file.");
    }
    if (videoFile && videoFile.size > OPENAI_AUDIO_UPLOAD_LIMIT_BYTES) {
      throw new Error("OpenAI transcription accepts files up to 25 MB in this MVP.");
    }
    if (transcriptFile && !transcriptFile.name.toLowerCase().endsWith(".txt")) {
      throw new Error("Transcript upload must be a .txt file.");
    }

    const description = await readRunDescription(projectId, repoUrl);
    const videoPath = videoFile ? await uploadVideo(projectId, videoFile) : loadedVideoPath;

    Object.assign(state, {
      projectId,
      repoUrl,
      description,
      videoPath,
      transcriptFile,
      transcriptText: transcriptFile ? null : loadedTranscriptText,
      transcriptSourceName: transcriptFile?.name || loadedTranscriptSourceName,
      transcription: null,
      comparison: null,
      report: null,
    });

    resetWorkflowOutput();
    inputSummary.innerHTML = `
      <strong>${escapeHtml(projectId)}</strong>
      <p>Inputs accepted. The system is analyzing the evidence and producing JSON.</p>
      <p>README processed: ${description.length.toLocaleString()} characters.</p>
      ${videoFile ? `<p>Video uploaded: ${escapeHtml(videoFile.name)}.</p>` : ""}
      ${!videoFile && videoPath ? `<p>Video path loaded from defaults.</p>` : ""}
      ${transcriptFile ? `<p>Transcript ready: ${escapeHtml(transcriptFile.name)}.</p>` : ""}
      ${!transcriptFile && state.transcriptText ? `<p>Transcript loaded from defaults: ${escapeHtml(state.transcriptSourceName || "default transcript")}.</p>` : ""}
      <p>${escapeHtml(repoUrl)}</p>
    `;
    setPill(step1Status, "Complete", "ok");
    await runFullWorkflow();
  } catch (error) {
    setPill(step1Status, "Error", "error");
    inputSummary.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function transcribeAndStore() {
  requireStep(state.videoPath || state.transcriptFile || state.transcriptText, "Upload inputs first.");
  setBusy(true);
  try {
    await processCurrentTranscript();
  } catch (error) {
    setPill(step2Status, "Error", "error");
    transcriptViewer.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function searchTranscriptVectors() {
  requireStep(state.transcription, "Transcribe and store the transcript first.");
  setBusy(true);
  searchResults.textContent = "Searching...";
  try {
    const data = await requestJson("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        projectId: state.projectId,
        query: searchQuery.value.trim() || state.repoUrl,
        limit: 5,
        similarityThreshold: 0,
      }),
    });
    searchResults.innerHTML = data.results.length
      ? data.results.map((item) => `
          <article class="search-result">
            <strong>${escapeHtml(item.id)} · ${item.similarity}</strong>
            <p>${escapeHtml(item.text)}</p>
          </article>
        `).join("")
      : "No matching transcript chunks found.";
  } catch (error) {
    searchResults.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function processTranscriptFile(projectId, file) {
  const body = new FormData();
  body.append("projectId", projectId);
  body.append("file", file);
  return requestJson("/api/process-transcript-file", {
    method: "POST",
    body,
  });
}

async function processTranscriptText(projectId, transcript, sourceName) {
  return requestJson("/api/process-transcript-text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      projectId,
      transcript,
      sourceName: sourceName || "default-transcript.txt",
    }),
  });
}

async function loadDefaultInputs() {
  setBusy(true);
  setPill(step1Status, "Running", "busy");
  try {
    const defaults = await requestJson("/api/default-inputs");
    const generatedProjectId = `proj-${new Date().toISOString().slice(0, 10)}-${Math.floor(Math.random() * 1000)}`;
    const projectId = defaults.projectId || generatedProjectId;
    const repoUrl = defaults.repoUrl || repoInput.value.trim();
    const description = defaults.readme || "";

    if (!repoUrl) throw new Error("Set DEFAULT_REPO_URL in .env or enter a repo URL.");
    if (!description) throw new Error("Set DEFAULT_README_PATH in .env or upload a README.");
    if (!defaults.videoPath && !defaults.transcript) {
      throw new Error("Set DEFAULT_VIDEO_PATH or DEFAULT_TRANSCRIPT_PATH in .env.");
    }

    projectIdInput.value = projectId;
    repoInput.value = repoUrl;
    descriptionPreview.value = description;

    Object.assign(state, {
      projectId,
      repoUrl,
      description,
      videoPath: defaults.videoPath || null,
      transcriptFile: null,
      transcriptText: defaults.transcript || null,
      transcriptSourceName: defaults.transcriptFilename || defaults.videoFilename || "default-input",
      transcription: null,
      comparison: null,
      report: null,
    });

    inputSummary.innerHTML = `
      <strong>${escapeHtml(projectId)}</strong>
      <p>README loaded: ${escapeHtml(defaults.readmeFilename || "configured default")} (${description.length.toLocaleString()} characters).</p>
      ${defaults.videoPath ? `<p>Video path loaded: ${escapeHtml(defaults.videoFilename)}.</p>` : ""}
      ${defaults.transcript ? `<p>Transcript loaded: ${escapeHtml(defaults.transcriptFilename)}.</p>` : ""}
      ${defaults.errors.length ? `<p>${escapeHtml(defaults.errors.join(" "))}</p>` : ""}
    `;
    setPill(step1Status, "Complete", "ok");
    setPill(step2Status, "Ready", "ok");
    step2Button.disabled = false;
    step3Button.disabled = true;
    step4Button.disabled = true;
    jsonViewer.textContent = "{}";
  } catch (error) {
    setPill(step1Status, "Error", "error");
    inputSummary.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function renderProcessingVerification() {
  try {
    const status = await requestJson(`/api/projects/${encodeURIComponent(state.projectId)}`);
    const transcript = status.transcript;
    searchResults.innerHTML = `
      <strong>Processed</strong>
      <p>Storage available: ${transcript.storageAvailable ? "yes" : "no"}</p>
      <p>Stored chunks: ${transcript.chunkCount}</p>
      <p>Semantic search: ${transcript.available && transcript.chunkCount > 0 ? "ready" : "not ready"}</p>
      ${transcript.error ? `<p>${escapeHtml(transcript.error)}</p>` : ""}
    `;
  } catch (error) {
    searchResults.textContent = `Processed transcript, but project status check failed: ${error.message}`;
  }
}

async function runAgentComparison() {
  requireStep(state.transcription, "Transcribe and store the transcript first.");
  setBusy(true);
  try {
    await compareCurrentInputs();
  } catch (error) {
    setPill(step3Status, "Error", "error");
    verificationSummary.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function generateReport() {
  requireStep(state.comparison, "Run the agent comparison first.");
  setBusy(true);
  try {
    await generateCurrentReport();
  } catch (error) {
    setPill(step4Status, "Error", "error");
    jsonViewer.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function previewReadmeFile() {
  try {
    descriptionPreview.value = await readReadmeDescription();
  } catch (error) {
    descriptionPreview.value = "";
    inputSummary.textContent = error.message;
  }
}

async function runFullWorkflow() {
  try {
    await processCurrentTranscript({ enableControls: false });
    await compareCurrentInputs({ enableControls: false });
    await generateCurrentReport();
    inputSummary.innerHTML += `<p><strong>Final JSON is ready to download.</strong></p>`;
  } catch (error) {
    markActiveWorkflowStepFailed(error.message);
    inputSummary.innerHTML += `<p><strong>Run stopped:</strong> ${escapeHtml(error.message)}</p>`;
    jsonViewer.textContent = error.message;
  }
}

async function processCurrentTranscript({ enableControls = true } = {}) {
  setPill(step2Status, "Running", "busy");
  transcriptViewer.textContent = state.transcriptFile || state.transcriptText
    ? "Processing transcript, chunking, and embedding..."
    : "Transcribing, chunking, and embedding...";

  const transcription = state.transcriptText
    ? await processTranscriptText(state.projectId, state.transcriptText, state.transcriptSourceName)
    : state.transcriptFile
      ? await processTranscriptFile(state.projectId, state.transcriptFile)
      : await requestJson("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: state.projectId,
          videoPath: state.videoPath,
        }),
      });

  state.transcription = transcription;
  chunkCount.textContent = transcription.chunks.length;
  durationValue.textContent = transcription.duration ? `${Math.round(transcription.duration)}s` : "-";
  embeddingValue.textContent = transcription.chunks[0]?.embedding?.length || "-";
  transcriptViewer.textContent = transcription.transcript || "No transcript text returned.";
  await renderProcessingVerification();
  if (enableControls) {
    searchButton.disabled = false;
    step2Button.disabled = false;
    step3Button.disabled = false;
  }
  setPill(step2Status, "Complete", "ok");
  setPill(step3Status, "Ready", "ok");
  return transcription;
}

async function compareCurrentInputs({ enableControls = true } = {}) {
  setPill(step3Status, "Running", "busy");
  verificationSummary.textContent = "Repository Evidence Agent is comparing claims against repository and transcript evidence...";

  const comparison = await requestJson("/api/agents/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      projectId: state.projectId,
      repoUrl: state.repoUrl,
      description: state.description,
      transcriptChunks: state.transcription.chunks.map((chunk) => ({
        id: chunk.id,
        text: chunk.text,
        startTime: chunk.startTime,
        endTime: chunk.endTime,
      })),
    }),
  });

  state.comparison = comparison;
  renderComparison(comparison);
  if (enableControls) {
    step4Button.disabled = false;
  }
  setPill(step3Status, "Complete", "ok");
  setPill(step4Status, "Ready", "ok");
  return comparison;
}

async function generateCurrentReport() {
  setPill(step4Status, "Running", "busy");
  jsonViewer.textContent = "Assembling evidence-grounded JSON report...";

  const report = await requestJson("/api/agents/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      projectId: state.projectId,
      repoUrl: state.repoUrl,
      description: state.description,
      transcription: state.transcription,
      repositoryAnalysis: state.comparison.repositoryAnalysis,
      claimExtraction: state.comparison.claimExtraction,
      verification: state.comparison.verification,
    }),
  });

  renderReport(report);
  setPill(step4Status, "Complete", "ok");
  await loadReports();
  return report;
}

async function readRunDescription(projectId, repoUrl) {
  if (readmeInput.files.length) return readReadmeDescription();
  if (state.projectId === projectId && state.repoUrl === repoUrl && state.description) {
    descriptionPreview.value = state.description;
    return state.description;
  }
  throw new Error("Upload a README.md, Markdown, or text file.");
}

async function readReadmeDescription() {
  if (!readmeInput.files.length) {
    throw new Error("Upload a README.md, Markdown, or text file.");
  }
  const file = readmeInput.files[0];
  const lowerName = file.name.toLowerCase();
  const isAccepted = lowerName.endsWith(".md") || lowerName.endsWith(".markdown") || lowerName.endsWith(".txt");
  if (!isAccepted) throw new Error("README must be .md, .markdown, or .txt.");
  const text = await file.text();
  const description = text.trim();
  if (!description) throw new Error("The README file is empty.");
  descriptionPreview.value = description;
  return description;
}

function resetWorkflowOutput() {
  setPill(step2Status, "Idle", "idle");
  setPill(step3Status, "Idle", "idle");
  setPill(step4Status, "Idle", "idle");
  chunkCount.textContent = "-";
  durationValue.textContent = "-";
  embeddingValue.textContent = "-";
  transcriptViewer.textContent = "Transcript output appears here.";
  searchResults.textContent = "Vector search results appear here.";
  claimedTechs.innerHTML = "";
  detectedTechs.innerHTML = "";
  verificationSummary.textContent = "No comparison run.";
  metricsGrid.innerHTML = `
    <div class="metric-card"><span>Total Claims</span><strong>-</strong></div>
    <div class="metric-card"><span>Verified</span><strong>-</strong></div>
    <div class="metric-card"><span>Partially Verified</span><strong>-</strong></div>
    <div class="metric-card"><span>Unverified</span><strong>-</strong></div>
    <div class="metric-card"><span>Risk</span><strong>-</strong></div>
  `;
  jsonViewer.textContent = "{}";
  searchButton.disabled = true;
  step2Button.disabled = true;
  step3Button.disabled = true;
  step4Button.disabled = true;
}

function markActiveWorkflowStepFailed(message) {
  if (step2Status.textContent === "Running") {
    setPill(step2Status, "Error", "error");
    transcriptViewer.textContent = message;
    return;
  }
  if (step3Status.textContent === "Running") {
    setPill(step3Status, "Error", "error");
    verificationSummary.textContent = message;
    return;
  }
  if (step4Status.textContent === "Running") {
    setPill(step4Status, "Error", "error");
  }
}

async function uploadVideo(projectId, file) {
  const body = new FormData();
  body.append("projectId", projectId);
  body.append("file", file);
  const uploaded = await requestJson("/api/upload-video", {
    method: "POST",
    body,
  });
  return uploaded.videoPath;
}

async function loadReports() {
  try {
    const data = await requestJson("/api/reports");
    if (!data.reports.length) {
      reportList.innerHTML = `<p class="muted">No saved reports.</p>`;
      return;
    }
    reportList.innerHTML = data.reports
      .map((report) => `
        <button class="report-item" type="button" data-project-id="${escapeHtml(report.projectId)}">
          <strong>${escapeHtml(report.projectId)}</strong>
          <span>${escapeHtml(report.riskLevel)} risk · ${report.verifiedClaims}/${report.totalClaims} verified</span>
        </button>
      `)
      .join("");

    reportList.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => loadReport(button.dataset.projectId));
    });
  } catch (error) {
    reportList.innerHTML = `<p class="muted">${escapeHtml(error.message)}</p>`;
  }
}

async function loadReport(projectId) {
  const report = await requestJson(`/api/reports/${encodeURIComponent(projectId)}`);
  renderReport(report);
  projectIdInput.value = report.project_metadata.projectId;
}

function renderComparison(comparison) {
  claimedTechs.innerHTML = renderTags(comparison.claimExtraction.claimedTechs, "name");
  detectedTechs.innerHTML = renderTags(comparison.repositoryAnalysis.detectedTechs, "name");
  const summary = comparison.verification.summary;
  verificationSummary.innerHTML = `
    <strong>${escapeHtml(comparison.agent.agentName)}</strong>
    <p>${summary.verified} verified, ${summary.partial} partial, ${summary.unverified} unverified, ${summary.contradicted} contradicted.</p>
    ${comparison.verification.claimVerification.map((item) => `
      <article class="verification-item">
        <strong>${escapeHtml(item.claimed)}</strong>
        <span>${escapeHtml(item.status)} · ${Math.round(item.confidence * 100)}%</span>
      </article>
    `).join("")}
  `;
}

function renderReport(report) {
  state.report = report;
  jsonViewer.textContent = JSON.stringify(report, null, 2);
  const summary = report.summary || {};
  metricsGrid.innerHTML = `
    <div class="metric-card"><span>Total Claims</span><strong>${summary.totalClaims ?? "-"}</strong></div>
    <div class="metric-card"><span>Verified</span><strong>${summary.verifiedClaims ?? "-"}</strong></div>
    <div class="metric-card"><span>Partially Verified</span><strong>${summary.partialClaims ?? "-"}</strong></div>
    <div class="metric-card"><span>Unverified</span><strong>${summary.unverifiedClaims ?? "-"}</strong></div>
    <div class="metric-card"><span>Risk</span><strong>${escapeHtml(summary.riskLevel || "-")}</strong></div>
  `;
}

function renderTags(items, key) {
  if (!items?.length) return `<span class="muted">None found.</span>`;
  return items.map((item) => `<span class="tech-tag">${escapeHtml(item[key])}</span>`).join("");
}

function downloadReport() {
  const report = state.report || readReportFromViewer();
  if (!report) {
    inputSummary.innerHTML += `<p><strong>Download unavailable:</strong> final JSON is not ready yet.</p>`;
    return;
  }

  const projectId = report.project_metadata?.projectId || state.projectId || "report";
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${projectId}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function readReportFromViewer() {
  try {
    const parsed = JSON.parse(jsonViewer.textContent);
    if (!parsed || Object.keys(parsed).length === 0) return null;
    return parsed;
  } catch {
    return null;
  }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof data === "string" ? data : data.detail || "Request failed.";
    throw new Error(message);
  }
  return data;
}

function setBusy(isBusy) {
  [loadDefaultsButton, step1Button, step2Button, step3Button, step4Button, searchButton].forEach((button) => {
    if (!button.dataset.locked) button.disabled = isBusy || button.disabled;
  });
  if (!isBusy) {
    loadDefaultsButton.disabled = false;
    step1Button.disabled = false;
    step2Button.disabled = !(state.videoPath || state.transcriptFile || state.transcriptText);
    step3Button.disabled = !state.transcription;
    step4Button.disabled = !state.comparison;
    searchButton.disabled = !state.transcription;
  }
}

function setPill(element, text, className) {
  element.textContent = text;
  element.className = `status-pill ${className}`;
}

function requireStep(value, message) {
  if (!value) throw new Error(message);
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, index)).toFixed(index ? 1 : 0)} ${units[index]}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

init();
