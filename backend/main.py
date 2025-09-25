import os
import uuid
import asyncio
import logging
import time
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import aiofiles

from config.settings import settings
from database.mongodb import connect_to_mongo, close_mongo_connection
from models.user import User, UserRole
from models.document import Document, DocumentStatus
from models.analysis import Analysis
from auth.security import get_current_user, create_access_token, get_password_hash, verify_password
from crewai import Crew, Process
from agents import financial_analyst, document_verifier, investment_advisor, risk_assessor
from task import verification_task, financial_analysis_task, risk_analysis_task, investment_recommendation_task

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-grade AI-powered financial document analysis system",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
)

# Trusted hosts (dev-friendly)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*", "localhost", "127.0.0.1"])

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# simple in-memory rate limit (use Redis in prod)
request_counts = defaultdict(list)

async def rate_limit_check(user_id: str):
    now = time.time()
    reqs = request_counts[user_id]
    request_counts[user_id] = [t for t in reqs if now - t < settings.RATE_LIMIT_PERIOD]
    if len(request_counts[user_id]) >= settings.RATE_LIMIT_CALLS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    request_counts[user_id].append(now)

def validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}")
    allowed_content_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail="Invalid content type")

async def process_financial_document(query: str, file_path: str, user_id: str, document_id: str):
    start_time = time.time()
    try:
        doc = await Document.get(document_id)
        if doc:
            doc.status = DocumentStatus.PROCESSING
            await doc.save()

        crew = Crew(
            agents=[document_verifier, financial_analyst, risk_assessor, investment_advisor],
            tasks=[verification_task, financial_analysis_task, risk_analysis_task, investment_recommendation_task],
            process=Process.sequential,
            verbose=settings.DEBUG,
            memory=True,
        )
        result = crew.kickoff({"query": query, "file_path": file_path, "user_id": user_id})
        dt = time.time() - start_time

        analysis = Analysis(
            document_id=document_id,
            user_id=user_id,
            query=query,
            analysis_results={
                "full_analysis": str(result),
                "processing_time": dt,
                "crew_tasks_completed": len(crew.tasks),
            },
            processing_time=dt,
            confidence_score=0.95,
        )
        await analysis.save()

        if doc:
            doc.status = DocumentStatus.COMPLETED
            doc.processed_date = datetime.utcnow()
            await doc.save()

        logger.info(f"Analysis completed in {dt:.2f}s for {document_id}")
        return str(result)

    except Exception as e:
        logger.error(f"Analysis failed for {document_id}: {e}")
        doc = await Document.get(document_id)
        if doc:
            doc.status = DocumentStatus.FAILED
            await doc.save()
        raise

@app.on_event("startup")
async def startup():
    await connect_to_mongo()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    admin = await User.find_one({"role": UserRole.ADMIN})
    if not admin:
        admin_user = User(
            email="admin@example.com",
            username="admin",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
        )
        await admin_user.save()
        logger.info("Created default admin user")

@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()

@app.get("/")
async def root():
    return {"message": f"{settings.PROJECT_NAME} API is running", "version": settings.VERSION, "status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/auth/register")
async def register_user(email: str = Form(...), username: str = Form(...), full_name: str = Form(...), password: str = Form(...)):
    existing = await User.find_one({"$or": [{"email": email}, {"username": username}]})
    if existing:
        raise HTTPException(400, "User with this email or username already exists")
    user = User(email=email, username=username, full_name=full_name, hashed_password=get_password_hash(password), role=UserRole.USER)
    await user.save()
    return {"message": "User registered successfully", "user_id": str(user.id)}

@app.post("/auth/login")
async def login_user(username: str = Form(...), password: str = Form(...)):
    user = await User.find_one({"username": username})
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(401, "Incorrect username or password")
    if not user.is_active:
        raise HTTPException(401, "Account is inactive")
    user.last_login = datetime.utcnow()
    await user.save()
    token = create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer", "user": {"id": str(user.id), "username": user.username, "full_name": user.full_name, "role": user.role}}

@app.post(f"{settings.API_V1_STR}/analyze")
async def analyze_document_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    query: str = Form(default="Provide comprehensive financial analysis"),
    current_user: User = Depends(get_current_user),
):
    await rate_limit_check(str(current_user.id))
    validate_file(file)
    query = (query or "Provide comprehensive financial analysis").strip()[:2000]

    document_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    file_path = Path(settings.UPLOAD_DIR) / f"{file_id}{ext}"

    try:
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(413, "File too large")

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        doc = Document(
            id=document_id,
            filename=f"{file_id}{ext}",
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            content_type=file.content_type,
            uploaded_by=str(current_user.id),
            status=DocumentStatus.UPLOADED,
        )
        await doc.save()

        background_tasks.add_task(process_financial_document, query, str(file_path), str(current_user.id), document_id)

        return {
            "status": "success",
            "message": "Document uploaded. Analysis started.",
            "document_id": document_id,
            "query": query,
            "file_info": {"original_filename": file.filename, "file_size": len(content), "content_type": file.content_type},
            "estimated_processing_time": "2-5 minutes",
        }

    except HTTPException:
        if file_path.exists(): file_path.unlink()
        raise
    except Exception as e:
        if file_path.exists(): file_path.unlink()
        logger.error(f"Upload processing error: {e}")
        raise HTTPException(500, f"Error processing document: {e}")

@app.get(f"{settings.API_V1_STR}/analysis/{{analysis_id}}")
async def get_analysis_result(analysis_id: str, current_user: User = Depends(get_current_user)):
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(404, "Analysis not found")
    if analysis.user_id != str(current_user.id) and current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "Access denied")
    return {
        "analysis_id": str(analysis.id),
        "document_id": analysis.document_id,
        "query": analysis.query,
        "results": analysis.analysis_results,
        "confidence_score": analysis.confidence_score,
        "processing_time": analysis.processing_time,
        "created_at": analysis.created_at,
        "status": "completed",
    }

@app.get(f"{settings.API_V1_STR}/documents")
async def list_user_documents(skip: int = 0, limit: int = 50, current_user: User = Depends(get_current_user)):
    filt = {"uploaded_by": str(current_user.id)} if current_user.role != UserRole.ADMIN else {}
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
            }
            for d in documents
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@app.delete(f"{settings.API_V1_STR}/documents/{{document_id}}")
async def delete_document(document_id: str, current_user: User = Depends(get_current_user)):
    doc = await Document.get(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.uploaded_by != str(current_user.id) and current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "Access denied")
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        await Analysis.find({"document_id": document_id}).delete()
        await doc.delete()
        return {"message": "Document deleted successfully"}
    except Exception as e:
        logger.error(f"Delete error {document_id}: {e}")
        raise HTTPException(500, "Error deleting document")

@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    try:
        users_count = await User.count()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION,
            "database": "connected",
            "users_count": users_count,
            "upload_dir": str(Path(settings.UPLOAD_DIR).absolute()),
            "environment": settings.ENVIRONMENT,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)), reload=settings.DEBUG, log_level="info" if settings.DEBUG else "warning")
