"""
Knowledge Base Retriever Module (Phase 3B)
Loads and indexes processed ESCO and O*NET datasets from data/processed/ for fast matching lookup.
"""

import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")


def normalize_token(text):
    """Clean and normalize token string for lookup indexing."""
    if pd.isna(text) or not text:
        return ""
    val = str(text).strip().lower()
    val = re.sub(r"[^\w\s\+#\.]", " ", val)
    return re.sub(r"\s+", " ", val).strip()


COMMON_TITLE_MAPPINGS = {
    "python developer": "software developer",
    "senior python developer": "software developer",
    "java developer": "software developer",
    "backend developer": "software developer",
    "frontend developer": "web developer",
    "full stack developer": "software developer",
    "software engineer": "software developer",
    "python engineer": "software developer",
}


class KnowledgeBaseRetriever:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to cache loaded datasets across requests."""
        if cls._instance is None:
            cls._instance = super(KnowledgeBaseRetriever, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir=None):
        if self._initialized:
            return

        self.data_dir = data_dir or PROCESSED_DIR
        self.esco_occupations = {}
        self.esco_skills = {}
        self.esco_occ_alias_map = {}
        self.esco_skill_alias_map = {}
        self.esco_occ_skills_map = {}

        self.onet_occupations = {}
        self.onet_job_titles_map = {}
        self.onet_skills_map = {}
        self.onet_knowledge_map = {}
        self.onet_tasks_map = {}
        self.onet_education_map = {}
        self.onet_job_zones_map = {}

        self._load_datasets()
        self._initialized = True

    def _load_datasets(self):
        # 1. Load ESCO Occupations
        occ_p = os.path.join(self.data_dir, "esco_occupations.csv")
        if os.path.exists(occ_p):
            df_occ = pd.read_csv(occ_p)
            for r in df_occ.to_dict("records"):
                uri = r["concept_uri"]
                label = str(r["preferred_label"]) if pd.notnull(r.get("preferred_label")) else ""
                self.esco_occupations[uri] = {
                    "concept_uri": uri,
                    "preferred_label": label,
                    "code": str(r.get("code", "")) if pd.notnull(r.get("code")) else "",
                    "description": str(r.get("description", "")) if pd.notnull(r.get("description")) else "",
                }
                norm_lab = normalize_token(label)
                if norm_lab:
                    self.esco_occ_alias_map[norm_lab] = uri

        # 2. Load ESCO Occupation Aliases
        occ_alias_p = os.path.join(self.data_dir, "esco_occupation_aliases.csv")
        if os.path.exists(occ_alias_p):
            df_occ_alias = pd.read_csv(occ_alias_p)
            for r in df_occ_alias.to_dict("records"):
                alias_norm = str(r.get("normalized_alias", "")).strip().lower()
                uri = r["concept_uri"]
                if alias_norm:
                    self.esco_occ_alias_map[alias_norm] = uri

        # 3. Load ESCO Skills
        skills_p = os.path.join(self.data_dir, "esco_skills.csv")
        if os.path.exists(skills_p):
            df_sk = pd.read_csv(skills_p)
            for r in df_sk.to_dict("records"):
                uri = r["concept_uri"]
                label = str(r.get("preferred_label", "")) if pd.notnull(r.get("preferred_label")) else ""
                self.esco_skills[uri] = {
                    "concept_uri": uri,
                    "preferred_label": label,
                    "skill_type": str(r.get("skill_type", "")) if pd.notnull(r.get("skill_type")) else "",
                    "reuse_level": str(r.get("reuse_level", "")) if pd.notnull(r.get("reuse_level")) else "",
                    "description": str(r.get("description", "")) if pd.notnull(r.get("description")) else "",
                }
                norm_lab = normalize_token(label)
                if norm_lab:
                    self.esco_skill_alias_map[norm_lab] = uri

        # 4. Load ESCO Skill Aliases
        skill_alias_p = os.path.join(self.data_dir, "esco_skill_aliases.csv")
        if os.path.exists(skill_alias_p):
            df_sk_alias = pd.read_csv(skill_alias_p)
            for r in df_sk_alias.to_dict("records"):
                alias_norm = str(r.get("normalized_alias", "")).strip().lower()
                uri = r["concept_uri"]
                if alias_norm:
                    self.esco_skill_alias_map[alias_norm] = uri

        # 5. Load ESCO Occupation-Skill Relations
        occ_sk_p = os.path.join(self.data_dir, "esco_occupation_skills.csv")
        if os.path.exists(occ_sk_p):
            df_occ_sk = pd.read_csv(occ_sk_p)
            for r in df_occ_sk.to_dict("records"):
                occ_uri = r["occupation_uri"]
                if occ_uri not in self.esco_occ_skills_map:
                    self.esco_occ_skills_map[occ_uri] = []
                self.esco_occ_skills_map[occ_uri].append(
                    {
                        "skill_uri": r["skill_uri"],
                        "relation_type": str(r.get("relation_type", "")),
                        "skill_type": str(r.get("skill_type", "")) if pd.notnull(r.get("skill_type")) else "",
                    }
                )

        # 6. Load O*NET Occupations
        onet_occ_p = os.path.join(self.data_dir, "onet_occupations.csv")
        if os.path.exists(onet_occ_p):
            df_onet_occ = pd.read_csv(onet_occ_p)
            for r in df_onet_occ.to_dict("records"):
                code = r["onet_soc_code"]
                title = str(r.get("title", "")) if pd.notnull(r.get("title")) else ""
                self.onet_occupations[code] = {
                    "onet_soc_code": code,
                    "title": title,
                    "description": str(r.get("description", "")) if pd.notnull(r.get("description")) else "",
                }
                norm_t = normalize_token(title)
                if norm_t:
                    self.onet_job_titles_map[norm_t] = code

        # 7. Load O*NET Alternate Job Titles
        onet_jt_p = os.path.join(self.data_dir, "onet_job_titles.csv")
        if os.path.exists(onet_jt_p):
            df_onet_jt = pd.read_csv(onet_jt_p)
            for r in df_onet_jt.to_dict("records"):
                code = r["onet_soc_code"]
                jt = str(r.get("job_title", "")) if pd.notnull(r.get("job_title")) else ""
                norm_jt = normalize_token(jt)
                if norm_jt:
                    self.onet_job_titles_map[norm_jt] = code

        # 8. Load O*NET Pivoted Skills
        onet_sk_p = os.path.join(self.data_dir, "onet_skills_pivoted.csv")
        if os.path.exists(onet_sk_p):
            df_onet_sk = pd.read_csv(onet_sk_p)
            for r in df_onet_sk.to_dict("records"):
                code = r["onet_soc_code"]
                if code not in self.onet_skills_map:
                    self.onet_skills_map[code] = []
                self.onet_skills_map[code].append(
                    {
                        "element_id": r["element_id"],
                        "element_name": r["element_name"],
                        "importance": float(r["importance"]) if pd.notnull(r.get("importance")) else 0.0,
                        "level": float(r["level"]) if pd.notnull(r.get("level")) else 0.0,
                    }
                )

        # 9. Load O*NET Pivoted Knowledge
        onet_kn_p = os.path.join(self.data_dir, "onet_knowledge_pivoted.csv")
        if os.path.exists(onet_kn_p):
            df_onet_kn = pd.read_csv(onet_kn_p)
            for r in df_onet_kn.to_dict("records"):
                code = r["onet_soc_code"]
                if code not in self.onet_knowledge_map:
                    self.onet_knowledge_map[code] = []
                self.onet_knowledge_map[code].append(
                    {
                        "element_id": r["element_id"],
                        "element_name": r["element_name"],
                        "importance": float(r["importance"]) if pd.notnull(r.get("importance")) else 0.0,
                        "level": float(r["level"]) if pd.notnull(r.get("level")) else 0.0,
                    }
                )

        # 10. Load O*NET Tasks
        onet_ts_p = os.path.join(self.data_dir, "onet_tasks.csv")
        if os.path.exists(onet_ts_p):
            df_onet_ts = pd.read_csv(onet_ts_p)
            for r in df_onet_ts.to_dict("records"):
                code = r["onet_soc_code"]
                if code not in self.onet_tasks_map:
                    self.onet_tasks_map[code] = []
                task_text = str(r.get("task", r.get("task_statement", "")))
                self.onet_tasks_map[code].append(
                    {
                        "task_id": r["task_id"],
                        "task_statement": task_text,
                        "task_type": str(r.get("task_type", "Core")),
                    }
                )

        # 11. Load O*NET Job Zones
        onet_jz_p = os.path.join(self.data_dir, "onet_job_zones.csv")
        if os.path.exists(onet_jz_p):
            df_onet_jz = pd.read_csv(onet_jz_p)
            for r in df_onet_jz.to_dict("records"):
                code = r["onet_soc_code"]
                self.onet_job_zones_map[code] = {
                    "job_zone": int(r["job_zone"]) if pd.notnull(r.get("job_zone")) else 3,
                    "name": str(r.get("name", "")),
                    "svp_range": str(r.get("svp_range", "")),
                }

    def find_esco_occupation(self, title_text):
        """Match title string to closest ESCO occupation concept URI."""
        norm_t = normalize_token(title_text)
        if not norm_t or norm_t in ["general match", "general"]:
            return None
        mapped = COMMON_TITLE_MAPPINGS.get(norm_t, norm_t)
        if mapped in self.esco_occ_alias_map:
            uri = self.esco_occ_alias_map[mapped]
            return self.esco_occupations.get(uri)

        for alias, uri in self.esco_occ_alias_map.items():
            if len(alias) >= 5 and alias == norm_t:
                return self.esco_occupations.get(uri)
        return None

    def find_onet_occupation(self, title_text):
        """Match title string to closest O*NET occupation SOC code."""
        norm_t = normalize_token(title_text)
        if not norm_t or norm_t in ["general match", "general"]:
            return None
        mapped = COMMON_TITLE_MAPPINGS.get(norm_t, norm_t)
        if mapped in self.onet_job_titles_map:
            code = self.onet_job_titles_map[mapped]
            return self.onet_occupations.get(code)

        for alias, code in self.onet_job_titles_map.items():
            if len(alias) >= 5 and alias == norm_t:
                return self.onet_occupations.get(code)
        return None
