from __future__ import annotations

import logging

from app.schemas.profile import CandidateProfile, ProjectItem

logger = logging.getLogger("app.optimizer")

class ResumeOptimizer:
    """
    Reorder and rewrite resume content to match a job description.
    Never invents experience — only reorders and rewrites existing facts.
    """

    def optimize(self, profile: CandidateProfile, job_description: str, job_skills: list[str]) -> CandidateProfile:
        optimized = profile.model_copy(deep=True)
        jd_lower = job_description.lower()

        optimized.skills = self._reorder_skills(profile.skills, job_skills, jd_lower)
        optimized.projects = self._reorder_projects(profile.projects, jd_lower)
        optimized.keywords = self._merge_keywords(profile.keywords, job_skills, jd_lower)
        optimized.experience = self._reorder_bullets(profile.experience, jd_lower)
        logger.info(
            "Optimized resume: skills %d→%d order, projects reordered, keywords=%d",
            len(profile.skills),
            len(optimized.skills),
            len(optimized.keywords),
        )
        return optimized
    def _reorder_skills(self, skills: list[str], job_skills: list[str], jd_lower: str) -> list[str]:
        priority: list[str] = []
        remaining = list(skills)

        for target in job_skills:
            for skill in list(remaining):
                if skill.lower() == target.lower() or target.lower() in skill.lower():
                    priority.append(skill)
                    remaining.remove(skill)

        for skill in list(remaining):
            if skill.lower() in jd_lower:
                priority.append(skill)
                remaining.remove(skill)

        return priority + remaining

    def _reorder_projects(self, projects: list[ProjectItem], jd_lower: str) -> list[ProjectItem]:
        def score(project: ProjectItem) -> int:
            text = f"{project.name} {project.description} {' '.join(project.technologies)}".lower()
            return sum(1 for token in jd_lower.split() if len(token) > 3 and token in text)

        return sorted(projects, key=score, reverse=True)

    def _merge_keywords(self, keywords: list[str], job_skills: list[str], jd_lower: str) -> list[str]:
        merged = list(dict.fromkeys([*keywords, *job_skills]))
        return [kw for kw in merged if kw.lower() in jd_lower or kw in keywords][:30]

    def _reorder_bullets(self, experience: list, jd_lower: str):
        from app.schemas.profile import ExperienceItem

        reordered: list[ExperienceItem] = []
        for item in experience:
            exp = item if isinstance(item, ExperienceItem) else ExperienceItem.model_validate(item)
            scored = sorted(
                exp.bullets,
                key=lambda bullet: sum(
                    1 for token in jd_lower.split() if len(token) > 3 and token in bullet.lower()
                ),
                reverse=True,
            )
            reordered.append(exp.model_copy(update={"bullets": scored}))
        return reordered

    def estimate_ats_score(self, profile: CandidateProfile, job_description: str, job_skills: list[str]) -> dict:
        jd_tokens = set(job_description.lower().split())
        profile_text = profile.model_dump_json().lower()
        profile_tokens = set(profile_text.split())

        if job_skills:
            covered = sum(1 for skill in job_skills if skill.lower() in profile_text)
            keyword_coverage = (covered / len(job_skills)) * 100
        else:
            overlap = len(jd_tokens & profile_tokens)
            keyword_coverage = min(100.0, overlap / max(len(jd_tokens), 1) * 100)

        missing_skills = [s for s in job_skills if s.lower() not in profile_text]
        formatting_score = 90.0 if profile.name and profile.skills else 70.0
        overall = round(keyword_coverage * 0.7 + formatting_score * 0.3, 1)

        logger.info(
            "ATS estimate: overall=%.1f keyword_coverage=%.1f missing_skills=%d",
            overall,
            keyword_coverage,
            len(missing_skills),
        )

        return {            "overall_score": overall,
            "keyword_coverage": round(keyword_coverage, 1),
            "formatting_score": formatting_score,
            "missing_skills": missing_skills,
            "recommendations": self._recommendations(missing_skills, overall),
        }

    def _recommendations(self, missing_skills: list[str], score: float) -> list[str]:
        recs: list[str] = []
        if missing_skills:
            recs.append(f"Surface existing experience related to: {', '.join(missing_skills[:5])}")
        if score < 75:
            recs.append("Reorder skills and projects to prioritize JD keywords.")
        recs.append("Use single-column layout and standard section headings.")
        return recs
