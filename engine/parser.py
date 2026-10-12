"""
Resume Parser Module (Phase 3B)
Extracts structured document sections, work experience bullet points, contact details, and handles negation scope analysis.
"""

import re


def clean_line(text):
    """Strip whitespace and normalize line formatting."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


class ResumeParser:

    NEGATION_PATTERNS = [
        r"\bno\s+experience\s+(?:in|with)\b",
        r"\bnot\s+proficient\s+(?:in|with)\b",
        r"\bnever\s+worked\s+with\b",
        r"\bno\s+knowledge\s+of\b",
        r"\blacking\s+experience\s+in\b",
        r"\bwithout\s+any\s+prior\b",
    ]

    SECTION_HEADINGS = {
        "experience": [
            "work experience",
            "professional experience",
            "employment history",
            "career history",
            "work history",
            "experience",
        ],
        "education": [
            "education",
            "academic background",
            "qualifications",
            "degrees",
        ],
        "skills": [
            "technical skills",
            "skills",
            "core competencies",
            "technologies",
            "tools",
        ],
    }

    def parse(self, text):
        """Parse raw resume text into structured sections, bullets, and contact info."""
        if not text:
            return {
                "raw_text": "",
                "clean_text": "",
                "sections": {},
                "experience_bullets": [],
                "email": "",
                "phone": "",
                "negated_terms": [],
            }

        lines = [clean_line(l) for l in text.split("\n") if clean_line(l)]
        clean_full_text = " ".join(lines)

        sections = self._extract_sections(lines)
        exp_bullets = self._extract_experience_bullets(sections.get("experience", []))
        email = self._extract_email(clean_full_text)
        phone = self._extract_phone(clean_full_text)
        negated_terms = self._extract_negated_terms(clean_full_text)

        return {
            "raw_text": text,
            "clean_text": clean_full_text,
            "sections": sections,
            "experience_bullets": exp_bullets,
            "email": email,
            "phone": phone,
            "negated_terms": negated_terms,
        }

    def _extract_sections(self, lines):
        sections = {"summary": [], "experience": [], "education": [], "skills": []}
        current_section = "summary"

        for line in lines:
            line_lower = line.lower().strip(":-# ")
            matched_heading = False
            for sec_name, keywords in self.SECTION_HEADINGS.items():
                if any(line_lower == kw or line_lower.startswith(kw + ":") for kw in keywords):
                    current_section = sec_name
                    matched_heading = True
                    break
            if not matched_heading:
                sections[current_section].append(line)

        return sections

    def _extract_experience_bullets(self, exp_lines):
        bullets = []
        for line in exp_lines:
            # Lines starting with bullet characters or verbs
            if re.match(r"^[\bullet\-\*\•\d\.\)]\s*", line):
                cleaned_b = re.sub(r"^[\bullet\-\*\•\d\.\)]\s*", "", line)
                if len(cleaned_b) > 10:
                    bullets.append(cleaned_b)
            elif len(line) > 20 and not line.endswith(":"):
                bullets.append(line)
        return bullets

    def _extract_email(self, text):
        m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        return m.group(0) if m else ""

    def _extract_phone(self, text):
        m = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+\d{1,3}[-.\s]?\d{6,14}", text)
        return m.group(0) if m else ""

    def _extract_negated_terms(self, text):
        negated = []
        for pat in self.NEGATION_PATTERNS:
            matches = re.finditer(pat + r"\s+([a-zA-Z0-9\+\#\.\s]{2,30})", text, re.IGNORECASE)
            for m in matches:
                negated.append(m.group(1).strip())
        return negated
