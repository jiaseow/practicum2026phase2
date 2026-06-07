from pydantic import BaseModel, ConfigDict, Field


class UploadVideoResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    filename: str
    original_filename: str = Field(alias="originalFilename")
    video_path: str = Field(alias="videoPath")
    content_type: str = Field(alias="contentType")
    size_bytes: int = Field(alias="sizeBytes")
