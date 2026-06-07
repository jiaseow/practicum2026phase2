from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DefaultInputsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: Optional[str] = Field(default=None, alias="projectId")
    repo_url: Optional[str] = Field(default=None, alias="repoUrl")
    video_path: Optional[str] = Field(default=None, alias="videoPath")
    video_filename: Optional[str] = Field(default=None, alias="videoFilename")
    transcript: Optional[str] = None
    transcript_filename: Optional[str] = Field(default=None, alias="transcriptFilename")
    readme: Optional[str] = None
    readme_filename: Optional[str] = Field(default=None, alias="readmeFilename")
    errors: list[str] = Field(default_factory=list)
