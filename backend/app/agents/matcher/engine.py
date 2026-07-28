from __future__ import annotations

import logging

from app.schemas.profile import CandidateProfile

logger = logging.getLogger("app.matcher")

class MatchingEngine:
    """Score resume vs job description on multiple dimensions."""

    def __init__(self, threshold: float = 75.0) -> None:
        self.threshold = threshold
        self._embedder = None

    @property
    def embedder(self):
        if self._embedder is None:
            from app.services.embeddings import EmbeddingService

            self._embedder = EmbeddingService()
        return self._embedder

    def score(self, profile: CandidateProfile | dict, job: dict, *, profile_vec=None) -> dict:
        if isinstance(profile, CandidateProfile):
            profile_data = profile.model_dump()
        else:
            profile_data = profile

        job_skills = [s.lower() for s in job.get("skills", [])]
        profile_skills = [s.lower() for s in profile_data.get("skills", [])]
        profile_text = str(profile_data).lower()
        description = job.get("description", "").lower()

        skills_score = self._skills_score(profile_skills, job_skills, profile_text, description)
        experience_score = self._experience_score(profile_data, description)
        location_score = self._location_score(profile_data.get("location", ""), job.get("location", ""))
        embedding_score = self._embedding_score(profile_data, job, profile_vec=profile_vec)

        final = round(
            skills_score * 0.35
            + experience_score * 0.20
            + embedding_score * 0.30
            + location_score * 0.15,
            1,
        )

        logger.debug(
            "Score %s @ %s → total=%.1f skills=%.1f exp=%.1f embed=%.1f loc=%.1f pass=%s",
            job.get("title", "?"),
            job.get("company", "?"),
            final,
            skills_score,
            experience_score,
            embedding_score,
            location_score,
            final >= self.threshold,
        )

        return {
            "score": final,
            "skills_score": round(skills_score, 1),
            "experience_score": round(experience_score, 1),
            "embedding_score": round(embedding_score, 1),
            "location_score": round(location_score, 1),
            "passed_threshold": final >= self.threshold,
        }

    def profile_vector(self, profile: CandidateProfile | dict):
        from app.services.embeddings import build_profile_document

        profile_data = profile.model_dump() if isinstance(profile, CandidateProfile) else profile
        return self.embedder.embed_text(build_profile_document(profile_data))

    def score_many(self, profile: CandidateProfile | dict, jobs: list[dict]) -> list[dict]:
        profile_vec = self.profile_vector(profile)
        return [self.score(profile, job, profile_vec=profile_vec) for job in jobs]

    def _skills_score(
        self,
        profile_skills: list[str],
        job_skills: list[str],
        profile_text: str,
        description: str,
    ) -> float:
        if not job_skills:
            overlap = sum(1 for token in description.split() if token in profile_text)
            return min(100.0, overlap / max(len(set(description.split())), 1) * 200)

        matched = 0
        for skill in job_skills:
            if skill in profile_skills or skill in profile_text:
                matched += 1
        return (matched / len(job_skills)) * 100

    def _experience_score(self, profile: dict, description: str) -> float:
        bullets = []
        for exp in profile.get("experience", []):
            bullets.extend(exp.get("bullets", []))
        if not bullets:
            return 50.0 if profile.get("skills") else 30.0

        hits = sum(1 for bullet in bullets if any(token in bullet.lower() for token in description.split()[:50]))
        return min(100.0, (hits / len(bullets)) * 100 + 20)

    def _location_score(self, candidate_location: str, job_location: str) -> float:
        if not job_location:
            return 80.0
        if not candidate_location:
            return 50.0
        c = candidate_location.lower()
        j = job_location.lower()
        if "remote" in j:
            return 95.0
        if c in j or j in c:
            return 100.0
        return 40.0

    def _embedding_score(self, profile: dict, job: dict, *, profile_vec=None) -> float:
        job_doc = " ".join(
            [
                job.get("title", ""),
                job.get("company", ""),
                str(job.get("description", ""))[:1500],
                ", ".join(job.get("skills", [])),
            ]
        )
        if profile_vec is None:
            from app.services.embeddings import build_profile_document

            profile_doc = build_profile_document(profile)
            profile_vec = self.embedder.embed_text(profile_doc)
        job_vec = self.embedder.embed_text(job_doc)
        similarity = float((profile_vec @ job_vec.T)[0][0])
        return max(0.0, min(100.0, similarity * 100))
