from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.agents.resume.parser import ResumeParser
from app.database.models import Candidate, Resume
from app.database.session import get_db
from app.schemas.profile import CandidateProfile
from app.services.embeddings import EmbeddingService, build_profile_document

import logging

logger = logging.getLogger("app.resumes")

router = APIRouter(prefix="/resumes", tags=["resumes"])

@router.post("/upload", response_model=dict)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")

    logger.info("Upload received: %s (%d bytes)", file.filename, file.size or 0)
    from uuid import uuid4

    from app.config import settings

    file_id = uuid4().hex
    dest = settings.storage_path / "resumes" / f"{file_id}.pdf"
    content = await file.read()
    dest.write_bytes(content)

    parser = ResumeParser()
    logger.info("Parsing resume: %s", dest.name)
    from app.services.pipeline_log import step, step_done

    step("PARSE_RESUME", file=file.filename)
    profile = parser.parse(dest)
    step_done("PARSE_RESUME", name=profile.name, skills=len(profile.skills))
    logger.info(
        "Parsed profile: name=%r skills=%d experience=%d projects=%d",
        profile.name,
        len(profile.skills),
        len(profile.experience),
        len(profile.projects),
    )
    candidate = Candidate(
        name=profile.name,
        email=profile.email,
        profile_json=profile.model_dump(),
        raw_text=profile.raw_text,
    )
    db.add(candidate)
    db.flush()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename=file.filename,
        file_path=str(dest),
        profile_json=profile.model_dump(),
        version_label="original",
    )
    db.add(resume)

    embedder = EmbeddingService()
    from app.services.pipeline_log import step_done

    logger.info("Creating embedding for candidate_id=%s", candidate.id)
    embedding_id = embedder.upsert_candidate(candidate.id, build_profile_document(profile.model_dump()))
    candidate.embedding_id = embedding_id

    db.commit()
    db.refresh(candidate)
    db.refresh(resume)

    logger.info(
        "Resume stored: candidate_id=%s resume_id=%s embedding_id=%s",
        candidate.id,
        resume.id,
        embedding_id,
    )
    step_done("STORE_CANDIDATE", candidate_id=candidate.id, resume_id=resume.id)
    return {
        "candidate_id": candidate.id,
        "resume_id": resume.id,
        "profile": profile.model_dump(),
    }


@router.get("/{candidate_id}", response_model=CandidateProfile)
def get_candidate_profile(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return CandidateProfile.model_validate(candidate.profile_json)
