from beanie import Document as BeanieDocument
from pydantic import Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BeanieDocument):
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    content_type: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    uploaded_by: str # user id
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    processed_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Settings:
    name = "documents"
    use_state_management = True