from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import hashlib
import json
from datetime import datetime

from backend.db import get_db
from backend.models.analysis import Analysis, AnalysisStatus
from backend.models.user import User
from backend.security.auth import get_current_user
from backend.schemas.analysis import AnalysisCreate, AnalysisResponse, AnalysisListResponse
from backend.services.file_service import FileService
from backend.services.ml_service import MLService
from backend.services.audit_service import AuditService

analysis_router = APIRouter(prefix="/analysis", tags=["analysis"])

@analysis_router.post("/", response_model=AnalysisResponse)
async def create_analysis(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    clinical_data: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new analysis with uploaded files and clinical data"""
    try:
        # Parse clinical data
        clinical_data_dict = json.loads(clinical_data)
        
        # Create analysis record
        analysis_id = str(uuid.uuid4())
        input_hash = hashlib.sha256(
            f"{clinical_data}_{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        analysis = Analysis(
            id=analysis_id,
            user_id=current_user.id,
            clinical_data=clinical_data_dict,
            status=AnalysisStatus.PENDING,
            input_hash=input_hash,
            created_at=datetime.utcnow()
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Process files in background
        background_tasks.add_task(
            process_analysis_task,
            analysis_id=analysis_id,
            files=files,
            clinical_data=clinical_data_dict,
            user_id=current_user.id
        )
        
        # Log audit trail
        await AuditService.log_analysis_created(
            analysis_id=analysis_id,
            user_id=current_user.id,
            input_hash=input_hash
        )
        
        return AnalysisResponse.from_orm(analysis)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create analysis: {str(e)}")

@analysis_router.get("/", response_model=AnalysisListResponse)
async def get_analyses(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's analysis history"""
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)
    
    if status:
        query = query.filter(Analysis.status == status)
    
    analyses = query.order_by(Analysis.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()
    
    return AnalysisListResponse(
        analyses=[AnalysisResponse.from_orm(analysis) for analysis in analyses],
        total=total,
        skip=skip,
        limit=limit
    )

@analysis_router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific analysis details"""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return AnalysisResponse.from_orm(analysis)

@analysis_router.post("/{analysis_id}/review")
async def request_clinician_review(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request clinician review for an analysis"""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Analysis must be completed before review")
    
    analysis.status = AnalysisStatus.REQUIRES_REVIEW
    analysis.review_requested_at = datetime.utcnow()
    db.commit()
    
    await AuditService.log_review_requested(
        analysis_id=analysis_id,
        user_id=current_user.id
    )
    
    return {"message": "Clinical review requested successfully"}

async def process_analysis_task(
    analysis_id: str,
    files: List[UploadFile],
    clinical_data: dict,
    user_id: str
):
    """Background task to process analysis"""
    from backend.db import SessionLocal
    
    db = SessionLocal()
    try:
        # Update status to processing
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = AnalysisStatus.PROCESSING
            db.commit()
        
        # Process files
        file_service = FileService()
        uploaded_files = []
        
        for file in files:
            file_url = await file_service.upload_file(file, analysis_id)
            uploaded_files.append({
                "name": file.filename,
                "type": file.content_type,
                "url": file_url,
                "size": file.size
            })
        
        # Run ML analysis
        ml_service = MLService()
        result = await ml_service.analyze(
            files=uploaded_files,
            clinical_data=clinical_data
        )
        
        # Update analysis with results
        if analysis:
            analysis.result = result
            analysis.files = uploaded_files
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.utcnow()
            
            # Check if clinician review is required
            if result.get("audit_trail", {}).get("clinician_review_required", False):
                analysis.status = AnalysisStatus.REQUIRES_REVIEW
            
            db.commit()
        
        await AuditService.log_analysis_completed(
            analysis_id=analysis_id,
            user_id=user_id,
            result=result
        )
        
    except Exception as e:
        if analysis:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            db.commit()
        
        await AuditService.log_analysis_failed(
            analysis_id=analysis_id,
            user_id=user_id,
            error=str(e)
        )
    finally:
        db.close()
