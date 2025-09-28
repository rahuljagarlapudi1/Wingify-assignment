# api/routes/analysis.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Form
from beanie import PydanticObjectId
from models.document import Document, DocumentStatus
from models.user import User
from services.analysis_service import process_financial_document
from api.deps import rate_limit

router = APIRouter()

@router.post("/analyze/{doc_id}")
async def analyze_document_endpoint(
    doc_id: str,
    background_tasks: BackgroundTasks,
    query: str = Form(default="Provide comprehensive financial analysis"),
    user: User = Depends(rate_limit),
):
    try:
        oid = PydanticObjectId(doc_id)
    except Exception:
        raise HTTPException(400, "Invalid document id")

    doc = await Document.get(oid)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.uploaded_by != str(user.id):
        raise HTTPException(403, "Access denied")

    doc.status = DocumentStatus.PROCESSING
    await doc.save()

    background_tasks.add_task(
        process_financial_document,
        query=query.strip()[:2000],
        file_path=doc.file_path,
        user_id=str(user.id),
        document_id=str(doc.id),
    )

    return {"status": "queued", "document_id": str(doc.id)}
