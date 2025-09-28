# models/document.py
from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Optional
import uuid

from beanie import Document as BeanieDocument, PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# -------- API Schemas (never use Beanie Document as request body) --------
class DocumentCreate(BaseModel):
    filename: str
    content_type: Optional[str] = None


class DocumentOut(BaseModel):
    id: str                  # Mongo ObjectId as hex string
    external_id: str         # Stable UUID for clients (optional to expose)
    filename: str
    content_type: str
    created_at: datetime


# ----------------------------- DB Model -----------------------------------
class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BeanieDocument):
    # Let Mongo/Beanie create ObjectId; do NOT set this from the client
    id: PydanticObjectId = Field(default_factory=PydanticObjectId)

    # Client-facing stable UUID (optional to expose in APIs)
    external_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # File metadata
    original_filename: str
    filename: str
    file_path: str
    file_size: int
    content_type: str

    # Ownership & lifecycle
    uploaded_by: str  # store user id as string; change to PydanticObjectId if you prefer
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    processed_date: Optional[datetime] = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    analysis: Optional[Dict[str, Any]] = None  # <- store final analysis payload here
    error: Optional[str] = None 

    class Settings:
        name = "documents"  # collection name


__all__ = [
    "Document",
    "DocumentStatus",
    "DocumentCreate",
    "DocumentOut",
]
