from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import timedelta
from database import get_db

from entities.user import User, Role
from security.auth import verify_password, create_access_token, require_role, ACCESS_TOKEN_EXPIRE_MINUTES

from entities.company import Company
from entities.verification_service import VerificationService
from entities.verification_profile import VerificationProfile, ProfileVersion, VerificationStep, VerificationEdge, ProfileStatus

from dto.superadmin_dto import (
    CompanyCreate, CompanyResponse,
    VerificationServiceResponse,
    ProfileCreate, ProfileResponse, ProfileVersionResponse,
    FlowGraphUpdate, FlowGraphResponse, StepDTO, EdgeDTO
)

router = APIRouter(prefix="/api/v1/admin", tags=["Super Admin"])

# --- Auth ---
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Verification Services ---
@router.get("/verification-services", response_model=List[VerificationServiceResponse], dependencies=[Depends(require_role([Role.SUPER_ADMIN, Role.ADMIN]))])
def get_verification_services(db: Session = Depends(get_db)):
    return db.query(VerificationService).all()

# --- Companies ---
@router.get("/companies", response_model=List[CompanyResponse])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()

@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(name=payload.name, industry=payload.industry)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

@router.get("/companies/{company_id}", response_model=CompanyResponse)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

# --- Verification Profiles ---
@router.get("/companies/{company_id}/profiles", response_model=List[ProfileResponse])
def list_profiles(company_id: int, db: Session = Depends(get_db)):
    profiles = db.query(VerificationProfile).filter(VerificationProfile.company_id == company_id).all()
    return profiles

@router.post("/companies/{company_id}/profiles", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(company_id: int, payload: ProfileCreate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    profile = VerificationProfile(company_id=company_id, name=payload.name, description=payload.description)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    # Auto-create v1 DRAFT
    version = ProfileVersion(
        company_id=company_id,
        profile_id=profile.id,
        version_number=1,
        status=ProfileStatus.DRAFT
    )
    db.add(version)
    db.commit()
    
    # Reload profile to include versions
    db.refresh(profile)
    return profile

@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(VerificationProfile).filter(VerificationProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

# --- Flow Graph (Visual Builder) ---
@router.get("/profiles/{profile_id}/versions/{version_number}/steps", response_model=FlowGraphResponse)
def get_flow_graph(profile_id: int, version_number: int, db: Session = Depends(get_db)):
    version = db.query(ProfileVersion).filter(
        ProfileVersion.profile_id == profile_id,
        ProfileVersion.version_number == version_number
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    return {
        "nodes": version.steps,
        "edges": version.edges
    }

@router.put("/profiles/{profile_id}/versions/{version_number}/steps")
def update_flow_graph(profile_id: int, version_number: int, payload: FlowGraphUpdate, db: Session = Depends(get_db)):
    version = db.query(ProfileVersion).filter(
        ProfileVersion.profile_id == profile_id,
        ProfileVersion.version_number == version_number
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    if version.status in [ProfileStatus.PUBLISHED, ProfileStatus.ARCHIVED]:
        raise HTTPException(status_code=400, detail="Cannot edit a PUBLISHED or ARCHIVED profile version. Duplicate it first.")

    # Clear existing steps and edges for this version
    db.query(VerificationStep).filter(VerificationStep.profile_version_id == version.id).delete()
    db.query(VerificationEdge).filter(VerificationEdge.profile_version_id == version.id).delete()
    
    # Add new steps
    for node in payload.nodes:
        step = VerificationStep(
            company_id=version.company_id,
            profile_version_id=version.id,
            service_id=node.service_id,
            node_key=node.node_key,
            order_index=node.order_index,
            is_required=node.is_required,
            is_enabled=node.is_enabled,
            configuration=node.configuration
        )
        db.add(step)
        
    # Add new edges
    for edge in payload.edges:
        db.add(VerificationEdge(
            company_id=version.company_id,
            profile_version_id=version.id,
            source_step_key=edge.source_step_key,
            target_step_key=edge.target_step_key,
            condition=edge.condition
        ))

    db.commit()
    return {"message": "Flow graph updated successfully"}

# --- Version Lifecycle ---
@router.post("/profiles/{profile_id}/versions/{version_number}/publish")
def publish_version(profile_id: int, version_number: int, db: Session = Depends(get_db)):
    version = db.query(ProfileVersion).filter(
        ProfileVersion.profile_id == profile_id,
        ProfileVersion.version_number == version_number
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    version.status = ProfileStatus.PUBLISHED
    db.commit()
    return {"message": "Version published", "status": version.status}

@router.post("/profiles/{profile_id}/versions/{version_number}/duplicate", response_model=ProfileVersionResponse)
def duplicate_version(profile_id: int, version_number: int, db: Session = Depends(get_db)):
    old_version = db.query(ProfileVersion).filter(
        ProfileVersion.profile_id == profile_id,
        ProfileVersion.version_number == version_number
    ).first()
    if not old_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Find next version number
    highest_v = db.query(func.max(ProfileVersion.version_number)).filter(ProfileVersion.profile_id == profile_id).scalar() or 0
    next_v = highest_v + 1
    
    new_version = ProfileVersion(
        company_id=old_version.company_id,
        profile_id=profile_id,
        version_number=next_v,
        status=ProfileStatus.DRAFT
    )
    db.add(new_version)
    db.flush() # get new_version.id
    
    # Duplicate steps
    for step in old_version.steps:
        db.add(VerificationStep(
            company_id=new_version.company_id,
            profile_version_id=new_version.id,
            service_id=step.service_id,
            node_key=step.node_key,
            order_index=step.order_index,
            is_required=step.is_required,
            is_enabled=step.is_enabled,
            configuration=step.configuration
        ))
        
    # Duplicate edges
    for edge in old_version.edges:
        db.add(VerificationEdge(
            company_id=new_version.company_id,
            profile_version_id=new_version.id,
            source_step_key=edge.source_step_key,
            target_step_key=edge.target_step_key,
            condition=edge.condition
        ))
        
    db.commit()
    db.refresh(new_version)
    return new_version
