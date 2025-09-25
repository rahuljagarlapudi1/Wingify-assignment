from datetime import datetime
from typing import Optional
from enum import Enum
from beanie import Document
from pydantic import Field

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Document(Document):
    filename: str = Field(...)
    original_filename: str = Field(...)
    file_path: str = Field(...)
    file_size: int = Field(...)
    content_type: str = Field(...)
    uploaded_by: str = Field(...)  # User ID
    status: DocumentStatus = Field(default=DocumentStatus.UPLOADED)
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    processed_date: Optional[datetime] = Field(default=None)
    
    class Settings:
        name = "documents"
        indexes = [
            [("uploaded_by", 1)],
            [("status", 1)],
            [("upload_date", -1)],
        ]