"""
Taxonomy Matcher Module (Phase 3B)
Extracts ESCO/O*NET skills, job titles, and domain knowledge from clean text using alias graphs.
"""

import re
from .retriever import KnowledgeBaseRetriever, normalize_token

# Baseline fallback technical skills list for backwards compatibility
LEGACY_SKILLS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "ruby", "go", "golang", "rust",
    "php", "swift", "kotlin", "r", "matlab", "scala", "perl", "sql", "html", "css", "bash", "shell",
    "react", "react.js", "angular", "vue", "vue.js", "next.js", "node.js", "express", "django",
    "flask", "fastapi", "spring", "spring boot", "asp.net", "laravel", "rails", "graphql", "rest api",
    "mysql", "postgresql", "postgres", "mongodb", "redis", "sqlite", "oracle", "elasticsearch",
    "dynamodb", "cassandra", "firebase",
    "aws", "amazon web services", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "jenkins", "terraform", "ansible", "ci/cd", "git", "github", "gitlab", "bitbucket", "linux",
    "machine learning", "deep learning", "ai", "artificial intelligence", "pandas", "numpy",
    "scikit-learn", "sklearn", "tensorflow", "pytorch", "opencv", "nlp", "natural language processing",
    "data analysis", "data science", "tableau", "power bi", "keras",
    "agile", "scrum", "kanban", "microservices", "system design", "object oriented programming",
    "oop", "test driven development", "tdd", "unit testing", "cybersecurity", "ui/ux", "figma"
]


class TaxonomyMatcher:

    def __init__(self, retriever=None):
        self.retriever = retriever or KnowledgeBaseRetriever()

    def extract_skills(self, text, negated_terms=None):
        """Extract matched skills from text mapped to display names and canonical concept URIs."""
        if not text:
            return []

        negated = set([normalize_token(t) for t in (negated_terms or [])])
        norm_text = normalize_token(text)
        found_skills = set()

        # 1. Match against ESCO skill alias graph
        for alias, uri in self.retriever.esco_skill_alias_map.items():
            if len(alias) < 3 and alias not in ["r", "ai", "c", "go", "ui"]:
                continue
            if alias in negated:
                continue

            pattern = r"(?:\b|_)" + re.escape(alias) + r"(?:\b|_)"
            if re.search(pattern, norm_text):
                skill_obj = self.retriever.esco_skills.get(uri)
                if skill_obj:
                    raw_label = skill_obj["preferred_label"]
                    clean_label = re.sub(r"\s*\(.*?\)", "", raw_label).strip()
                    if clean_label.lower() in ["sql", "aws", "gcp", "ai", "nlp", "ui/ux", "oop", "tdd", "ci/cd", "k8s", "r", "api", "rest api"]:
                        display_name = clean_label.upper()
                    elif clean_label.lower() in ["c++", "c#"]:
                        display_name = clean_label.upper()
                    elif "." in clean_label:
                        parts = clean_label.split(".")
                        display_name = parts[0].title() + "." + parts[1]
                    else:
                        display_name = clean_label.title()
                    found_skills.add(display_name)

        # 2. Match against Legacy/Fallback Skills list to guarantee backward compatibility
        for skill in LEGACY_SKILLS:
            if skill in negated:
                continue
            pattern = r"(?:\b|_)" + re.escape(skill) + r"(?:\b|_)"
            if re.search(pattern, norm_text):
                if skill in ["sql", "aws", "gcp", "ai", "nlp", "ui/ux", "oop", "tdd", "ci/cd", "k8s", "r"]:
                    display_name = skill.upper()
                elif skill in ["c++", "c#"]:
                    display_name = skill.upper()
                elif "." in skill:
                    parts = skill.split(".")
                    display_name = parts[0].title() + "." + parts[1]
                else:
                    display_name = skill.title()
                found_skills.add(display_name)

        return sorted(list(found_skills))

    def extract_target_requirements(self, job_title, jd_text):
        """Identify target ESCO/O*NET occupation and extract job-relevant essential vs optional requirements."""
        esco_occ = self.retriever.find_esco_occupation(job_title)
        onet_occ = self.retriever.find_onet_occupation(job_title)

        # 1. Extract skills directly requested in the Job Description text
        jd_skills = set(self.extract_skills(jd_text))

        # 2. Build taxonomy lookup sets for the matched occupation
        tax_essential_lower = set()
        tax_optional_lower = set()

        if esco_occ:
            uri = esco_occ["concept_uri"]
            rel_list = self.retriever.esco_occ_skills_map.get(uri, [])
            for r in rel_list:
                sk_obj = self.retriever.esco_skills.get(r["skill_uri"])
                if sk_obj:
                    clean_l = re.sub(r"\s*\(.*?\)", "", sk_obj["preferred_label"]).strip().lower()
                    if r["relation_type"] == "essential":
                        tax_essential_lower.add(clean_l)
                    else:
                        tax_optional_lower.add(clean_l)

        if onet_occ:
            code = onet_occ["onet_soc_code"]
            sk_list = self.retriever.onet_skills_map.get(code, [])
            for sk in sk_list:
                clean_l = sk["element_name"].strip().lower()
                if sk["importance"] >= 3.0:
                    tax_essential_lower.add(clean_l)
                else:
                    tax_optional_lower.add(clean_l)

        essential_skills = set()
        optional_skills = set()

        if jd_skills:
            # Contextualize JD-extracted skills using occupation taxonomy
            for sk in jd_skills:
                sk_lower = sk.lower()
                if sk_lower in tax_optional_lower:
                    optional_skills.add(sk)
                else:
                    # Default to essential for explicitly requested JD skills
                    essential_skills.add(sk)
        else:
            # Fallback if JD text contains no explicit recognized skills:
            # Use top core essential skills from matched ESCO/O*NET occupation (up to 8)
            if esco_occ:
                uri = esco_occ["concept_uri"]
                rel_list = self.retriever.esco_occ_skills_map.get(uri, [])
                for r in rel_list:
                    if r["relation_type"] == "essential" and len(essential_skills) < 8:
                        sk_obj = self.retriever.esco_skills.get(r["skill_uri"])
                        if sk_obj:
                            raw_l = sk_obj["preferred_label"]
                            clean_l = re.sub(r"\s*\(.*?\)", "", raw_l).strip().title()
                            essential_skills.add(clean_l)

        return {
            "esco_occupation": esco_occ,
            "onet_occupation": onet_occ,
            "essential_skills": sorted(list(essential_skills)),
            "optional_skills": sorted(list(optional_skills)),
        }
