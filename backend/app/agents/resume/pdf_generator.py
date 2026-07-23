from __future__ import annotations

import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings
from app.schemas.profile import CandidateProfile

logger = logging.getLogger("app.pdf")

class ResumePDFGenerator:
    """Generate ATS-friendly PDF from HTML template."""

    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(settings.templates_path)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate(self, profile: CandidateProfile, output_path: Path) -> Path:
        logger.info("Generating PDF for %r → %s", profile.name, output_path.name)
        template = self.env.get_template("resume.html")
        html = template.render(profile=profile.model_dump())
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html_path = output_path.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        logger.debug("Wrote HTML template: %s", html_path)

        try:
            logger.info("Rendering PDF via Playwright")
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
                page.pdf(path=str(output_path), format="A4", print_background=True)
                browser.close()
            logger.info("PDF generated via Playwright: %s", output_path)
        except Exception as exc:
            logger.warning("Playwright failed (%s), falling back to WeasyPrint", exc)
            from weasyprint import HTML

            HTML(string=html, base_url=str(settings.templates_path)).write_pdf(str(output_path))
            logger.info("PDF generated via WeasyPrint: %s", output_path)

        return output_path