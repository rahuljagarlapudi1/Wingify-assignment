# api/routes/documents.py
import os
from pathlib import Path
import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from models.document import Document, DocumentStatus
from models.user import User, UserRole
from api.deps import rate_limit
from config.settings import settings
from beanie import PydanticObjectId
from fastapi import HTTPException, Depends
from models.user import User, UserRole
from api.deps import rate_limit
from models.document import Document

router = APIRouter()

_ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

def _validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(400, "No file provided")
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(400, "Invalid content type")
    if Path(file.filename).suffix.lower() not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}")

@router.get("")
async def list_user_documents(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(rate_limit),
):
    filt = {"uploaded_by": str(user.id)} if user.role != UserRole.ADMIN else {}
    documents = await Document.find(filt).skip(skip).limit(limit).to_list()
    total = await Document.find(filt).count()
    return {
        "documents": [
            {
                "id": str(d.id),
                "original_filename": d.original_filename,
                "status": d.status,
                "upload_date": d.upload_date,
                "processed_date": d.processed_date,
                "file_size": d.file_size,
            } for d in documents
        ],
        "total": total, "skip": skip, "limit": limit,
    }

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(rate_limit),
):
    _validate_file(file)
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")

    uploads = Path(settings.UPLOAD_DIR); uploads.mkdir(exist_ok=True)
    # store with a generated name
    dst = uploads / file.filename  # or include a UUID prefix
    async with aiofiles.open(dst, "wb") as f:
        await f.write(content)

    doc = Document(
        original_filename=file.filename,
        filename=dst.name,
        file_path=str(dst),
        file_size=len(content),
        content_type=file.content_type or "application/octet-stream",
        uploaded_by=str(user.id),
        status=DocumentStatus.UPLOADED,
    )
    await doc.save()
    return {"message": "Uploaded", "id": str(doc.id)}



@router.get("/{doc_id}")
async def get_document_detail(doc_id: str, user: User = Depends(rate_limit)):
    try:
        oid = PydanticObjectId(doc_id)
    except Exception:
        raise HTTPException(400, "Invalid document id")

    doc = await Document.get(oid)
    if not doc:
        raise HTTPException(404, "Document not found")

    # allow owner or admin
    if doc.uploaded_by != str(user.id) and user.role != UserRole.ADMIN:
        raise HTTPException(403, "Access denied")

    return {
        "id": str(doc.id),
        "original_filename": doc.original_filename,
        "status": doc.status,
        "upload_date": doc.upload_date,
        "processed_date": doc.processed_date,
        "file_size": doc.file_size,
        "analysis": doc.analysis,
        "error": doc.error,
    }