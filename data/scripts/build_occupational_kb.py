"""
ETL Pipeline for Occupational Knowledge Base (Phase 2)
Builds normalized CSV datasets from raw ESCO and O*NET source files in data/raw/
Outputs processed datasets into data/processed/
"""

import os
import re
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_ESCO_DIR = os.path.join(BASE_DIR, "raw", "ESCO")
RAW_ONET_DIR = os.path.join(BASE_DIR, "raw", "ONET")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")


def normalize_text(val):
    """Normalize string whitespace and return cleaned string or empty string if null."""
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    val_str = re.sub(r"\s+", " ", val_str)
    return val_str


def parse_aliases(alt_labels_str):
    """Parse newline-separated altLabels into list of (original_alias, normalized_alias)."""
    if pd.isna(alt_labels_str) or not alt_labels_str:
        return []
    lines = str(alt_labels_str).split("\n")
    aliases = []
    seen = set()
    for line in lines:
        orig = line.strip()
        if orig:
            norm = re.sub(r"\s+", " ", orig).lower()
            if norm not in seen:
                seen.add(norm)
                aliases.append((orig, norm))
    return aliases


def ensure_processed_dir():
    os.makedirs(PROCESSED_DIR, exist_ok=True)


def build_esco():
    print("--- Processing ESCO Data ---")

    # 1. Occupations & Occupation Aliases
    occ_path = os.path.join(RAW_ESCO_DIR, "occupations_en.csv")
    df_occ_raw = pd.read_csv(occ_path)
    raw_occ_cnt = len(df_occ_raw)

    # Sort by modifiedDate descending and drop duplicate conceptUri to preserve primary key integrity
    df_occ = df_occ_raw.sort_values("modifiedDate", ascending=False).drop_duplicates(
        subset=["conceptUri"], keep="first"
    )
    print(
        f"Loaded raw occupations: {raw_occ_cnt} rows. Deduplicated by modifiedDate to {len(df_occ)} unique URIs."
    )

    occ_rename = {
        "conceptType": "concept_type",
        "conceptUri": "concept_uri",
        "iscoGroup": "isco_group",
        "preferredLabel": "preferred_label",
        "altLabels": "alt_labels",
        "hiddenLabels": "hidden_labels",
        "status": "status",
        "modifiedDate": "modified_date",
        "regulatedProfessionNote": "regulated_profession_note",
        "scopeNote": "scope_note",
        "definition": "definition",
        "inScheme": "in_scheme",
        "description": "description",
        "code": "code",
        "naceCode": "nace_code",
    }
    df_occ_proc = df_occ.rename(columns=occ_rename).copy()

    # Create occupation aliases table
    occ_alias_rows = []
    for _, row in df_occ_proc.iterrows():
        uri = row["concept_uri"]
        aliases = parse_aliases(row["alt_labels"])
        for orig, norm in aliases:
            occ_alias_rows.append(
                {
                    "concept_uri": uri,
                    "original_alias": orig,
                    "normalized_alias": norm,
                }
            )
    df_occ_alias = pd.DataFrame(occ_alias_rows)

    df_occ_proc.to_csv(
        os.path.join(PROCESSED_DIR, "esco_occupations.csv"), index=False
    )
    df_occ_alias.to_csv(
        os.path.join(PROCESSED_DIR, "esco_occupation_aliases.csv"), index=False
    )
    print(
        f"Saved esco_occupations.csv ({len(df_occ_proc)} rows) & esco_occupation_aliases.csv ({len(df_occ_alias)} rows)"
    )

    # 2. Skills & Skill Aliases
    skills_path = os.path.join(RAW_ESCO_DIR, "skills_en.csv")
    df_skills_raw = pd.read_csv(skills_path)
    raw_skills_cnt = len(df_skills_raw)

    # Sort by modifiedDate descending and drop duplicate conceptUri to preserve primary key integrity
    df_skills = df_skills_raw.sort_values(
        "modifiedDate", ascending=False
    ).drop_duplicates(subset=["conceptUri"], keep="first")
    print(
        f"Loaded raw skills: {raw_skills_cnt} rows. Deduplicated by modifiedDate to {len(df_skills)} unique URIs."
    )

    skills_rename = {
        "conceptType": "concept_type",
        "conceptUri": "concept_uri",
        "skillType": "skill_type",
        "reuseLevel": "reuse_level",
        "preferredLabel": "preferred_label",
        "altLabels": "alt_labels",
        "hiddenLabels": "hidden_labels",
        "status": "status",
        "modifiedDate": "modified_date",
        "scopeNote": "scope_note",
        "definition": "definition",
        "inScheme": "in_scheme",
        "description": "description",
    }
    df_skills_proc = df_skills.rename(columns=skills_rename).copy()

    skill_alias_rows = []
    for _, row in df_skills_proc.iterrows():
        uri = row["concept_uri"]
        aliases = parse_aliases(row["alt_labels"])
        for orig, norm in aliases:
            skill_alias_rows.append(
                {
                    "concept_uri": uri,
                    "original_alias": orig,
                    "normalized_alias": norm,
                }
            )
    df_skill_alias = pd.DataFrame(skill_alias_rows)

    df_skills_proc.to_csv(
        os.path.join(PROCESSED_DIR, "esco_skills.csv"), index=False
    )
    df_skill_alias.to_csv(
        os.path.join(PROCESSED_DIR, "esco_skill_aliases.csv"), index=False
    )
    print(
        f"Saved esco_skills.csv ({len(df_skills_proc)} rows) & esco_skill_aliases.csv ({len(df_skill_alias)} rows)"
    )

    # 3. Occupation-Skill Relations
    occ_skill_path = os.path.join(
        RAW_ESCO_DIR, "occupationSkillRelations_en.csv"
    )
    df_occ_skill = pd.read_csv(occ_skill_path)
    print(f"Loaded raw occupationSkillRelations: {len(df_occ_skill)} rows")

    occ_skill_rename = {
        "occupationUri": "occupation_uri",
        "occupationLabel": "occupation_label",
        "relationType": "relation_type",
        "skillType": "skill_type",
        "skillUri": "skill_uri",
        "skillLabel": "skill_label",
    }
    df_occ_skill_proc = df_occ_skill.rename(columns=occ_skill_rename)
    df_occ_skill_proc.to_csv(
        os.path.join(PROCESSED_DIR, "esco_occupation_skills.csv"), index=False
    )
    print(
        f"Saved esco_occupation_skills.csv ({len(df_occ_skill_proc)} rows)"
    )

    # 4. Skill-Skill Relations
    skill_rel_path = os.path.join(RAW_ESCO_DIR, "skillSkillRelations_en.csv")
    df_skill_rel = pd.read_csv(skill_rel_path)
    print(f"Loaded raw skillSkillRelations: {len(df_skill_rel)} rows")

    skill_rel_rename = {
        "originalSkillUri": "original_skill_uri",
        "originalSkillType": "original_skill_type",
        "relationType": "relation_type",
        "relatedSkillType": "related_skill_type",
        "relatedSkillUri": "related_skill_uri",
    }
    df_skill_rel_proc = df_skill_rel.rename(columns=skill_rel_rename)
    df_skill_rel_proc.to_csv(
        os.path.join(PROCESSED_DIR, "esco_skill_relations.csv"), index=False
    )
    print(f"Saved esco_skill_relations.csv ({len(df_skill_rel_proc)} rows)")

    # 5. Skills Hierarchy
    hierarchy_path = os.path.join(RAW_ESCO_DIR, "skillsHierarchy_en.csv")
    df_hierarchy = pd.read_csv(hierarchy_path)
    print(f"Loaded raw skillsHierarchy: {len(df_hierarchy)} rows")

    hierarchy_rename = {
        "Level 0 URI": "level_0_uri",
        "Level 0 preferred term": "level_0_preferred_term",
        "Level 1 URI": "level_1_uri",
        "Level 1 preferred term": "level_1_preferred_term",
        "Level 2 URI": "level_2_uri",
        "Level 2 preferred term": "level_2_preferred_term",
        "Level 3 URI": "level_3_uri",
        "Level 3 preferred term": "level_3_preferred_term",
        "Description": "description",
        "Scope note": "scope_note",
        "Level 0 code": "level_0_code",
        "Level 1 code": "level_1_code",
        "Level 2 code": "level_2_code",
        "Level 3 code": "level_3_code",
    }
    df_hierarchy_proc = df_hierarchy.rename(columns=hierarchy_rename)
    df_hierarchy_proc.to_csv(
        os.path.join(PROCESSED_DIR, "esco_skills_hierarchy.csv"), index=False
    )
    print(f"Saved esco_skills_hierarchy.csv ({len(df_hierarchy_proc)} rows)")


def build_onet():
    print("\n--- Processing O*NET Data ---")

    def to_snake(name):
        s = str(name).strip().replace("*", "").replace("(", "").replace(")", "")
        s = re.sub(r"[\s\-\/]+", "_", s)
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        return s.lower()

    # 1. Occupation Data
    occ_path = os.path.join(RAW_ONET_DIR, "Occupation Data.xlsx")
    df_occ = pd.read_excel(occ_path)
    print(f"Loaded raw Occupation Data: {len(df_occ)} rows")
    df_occ.columns = [to_snake(c) for c in df_occ.columns]
    df_occ = df_occ.rename(columns={"onet_soc_code": "onet_soc_code"})
    df_occ.to_csv(
        os.path.join(PROCESSED_DIR, "onet_occupations.csv"), index=False
    )
    print(f"Saved onet_occupations.csv ({len(df_occ)} rows)")

    # 2. Job Titles
    jt_path = os.path.join(RAW_ONET_DIR, "Job Titles.xlsx")
    df_jt = pd.read_excel(jt_path)
    print(f"Loaded raw Job Titles: {len(df_jt)} rows")
    df_jt.columns = [to_snake(c) for c in df_jt.columns]
    if "sources" in df_jt.columns:
        df_jt = df_jt.rename(columns={"sources": "source"})
    df_jt.to_csv(os.path.join(PROCESSED_DIR, "onet_job_titles.csv"), index=False)
    print(f"Saved onet_job_titles.csv ({len(df_jt)} rows)")

    # 3. Essential Skills (Raw scale records + Pivoted convenience table)
    sk_path = os.path.join(RAW_ONET_DIR, "Essential Skills.xlsx")
    df_sk = pd.read_excel(sk_path)
    print(f"Loaded raw Essential Skills: {len(df_sk)} rows")
    df_sk_proc = df_sk.copy()
    df_sk_proc.columns = [to_snake(c) for c in df_sk_proc.columns]
    df_sk_proc.to_csv(
        os.path.join(PROCESSED_DIR, "onet_skills.csv"), index=False
    )

    # Pivoted convenience view
    piv_sk = df_sk_proc.pivot_table(
        index=["onet_soc_code", "title", "element_id", "element_name"],
        columns="scale_id",
        values="data_value",
        aggfunc="first",
    ).reset_index()
    piv_sk.columns.name = None
    if "IM" in piv_sk.columns:
        piv_sk = piv_sk.rename(columns={"IM": "importance"})
    if "LV" in piv_sk.columns:
        piv_sk = piv_sk.rename(columns={"LV": "level"})
    piv_sk.to_csv(
        os.path.join(PROCESSED_DIR, "onet_skills_pivoted.csv"), index=False
    )
    print(
        f"Saved onet_skills.csv ({len(df_sk_proc)} raw scale rows) & onet_skills_pivoted.csv ({len(piv_sk)} rows)"
    )

    # 4. Knowledge (Raw scale records + Pivoted convenience table)
    kn_path = os.path.join(RAW_ONET_DIR, "Knowledge.xlsx")
    df_kn = pd.read_excel(kn_path)
    print(f"Loaded raw Knowledge: {len(df_kn)} rows")
    df_kn_proc = df_kn.copy()
    df_kn_proc.columns = [to_snake(c) for c in df_kn_proc.columns]
    df_kn_proc.to_csv(
        os.path.join(PROCESSED_DIR, "onet_knowledge.csv"), index=False
    )

    # Pivoted convenience view
    piv_kn = df_kn_proc.pivot_table(
        index=["onet_soc_code", "title", "element_id", "element_name"],
        columns="scale_id",
        values="data_value",
        aggfunc="first",
    ).reset_index()
    piv_kn.columns.name = None
    if "IM" in piv_kn.columns:
        piv_kn = piv_kn.rename(columns={"IM": "importance"})
    if "LV" in piv_kn.columns:
        piv_kn = piv_kn.rename(columns={"LV": "level"})
    piv_kn.to_csv(
        os.path.join(PROCESSED_DIR, "onet_knowledge_pivoted.csv"), index=False
    )
    print(
        f"Saved onet_knowledge.csv ({len(df_kn_proc)} raw scale rows) & onet_knowledge_pivoted.csv ({len(piv_kn)} rows)"
    )

    # 5. Software Skills
    sw_path = os.path.join(RAW_ONET_DIR, "Software Skills.xlsx")
    df_sw = pd.read_excel(sw_path)
    print(f"Loaded raw Software Skills: {len(df_sw)} rows")
    df_sw.columns = [to_snake(c) for c in df_sw.columns]
    df_sw = df_sw.rename(columns={"workplace_example": "software_title"})
    df_sw.to_csv(
        os.path.join(PROCESSED_DIR, "onet_software_skills.csv"), index=False
    )
    print(f"Saved onet_software_skills.csv ({len(df_sw)} rows)")

    # 6. Task Statements
    ts_path = os.path.join(RAW_ONET_DIR, "Task Statements.xlsx")
    df_ts = pd.read_excel(ts_path)
    print(f"Loaded raw Task Statements: {len(df_ts)} rows")
    df_ts.columns = [to_snake(c) for c in df_ts.columns]
    df_ts.to_csv(os.path.join(PROCESSED_DIR, "onet_tasks.csv"), index=False)
    print(f"Saved onet_tasks.csv ({len(df_ts)} rows)")

    # 7. Education + Category Reference Join
    ed_path = os.path.join(RAW_ONET_DIR, "Education.xlsx")
    ed_cat_path = os.path.join(RAW_ONET_DIR, "Education Categories.xlsx")
    df_ed = pd.read_excel(ed_path)
    df_ed_cat = pd.read_excel(ed_cat_path)
    print(
        f"Loaded raw Education ({len(df_ed)} rows) & Education Categories ({len(df_ed_cat)} rows)"
    )

    merged_ed = df_ed.merge(
        df_ed_cat[["Element ID", "Scale ID", "Category", "Category Description"]],
        on=["Element ID", "Scale ID", "Category"],
        how="left",
    )
    merged_ed.columns = [to_snake(c) for c in merged_ed.columns]
    merged_ed.to_csv(
        os.path.join(PROCESSED_DIR, "onet_education.csv"), index=False
    )
    print(f"Saved onet_education.csv ({len(merged_ed)} merged rows)")

    # 8. Training & Experience + Category Reference Join
    tr_path = os.path.join(RAW_ONET_DIR, "Training and Experience.xlsx")
    tr_cat_path = os.path.join(
        RAW_ONET_DIR, "Training and Experience Categories.xlsx"
    )
    df_tr = pd.read_excel(tr_path)
    df_tr_cat = pd.read_excel(tr_cat_path)
    print(
        f"Loaded raw Training ({len(df_tr)} rows) & Training Categories ({len(df_tr_cat)} rows)"
    )

    merged_tr = df_tr.merge(
        df_tr_cat[["Element ID", "Scale ID", "Category", "Category Description"]],
        on=["Element ID", "Scale ID", "Category"],
        how="left",
    )
    merged_tr.columns = [to_snake(c) for c in merged_tr.columns]
    merged_tr.to_csv(
        os.path.join(PROCESSED_DIR, "onet_training_experience.csv"), index=False
    )
    print(
        f"Saved onet_training_experience.csv ({len(merged_tr)} merged rows)"
    )

    # 9. Job Zones + Reference Join
    jz_path = os.path.join(RAW_ONET_DIR, "Job Zones.xlsx")
    jz_ref_path = os.path.join(RAW_ONET_DIR, "Job Zone Reference.xlsx")
    df_jz = pd.read_excel(jz_path)
    df_jz_ref = pd.read_excel(jz_ref_path)
    print(
        f"Loaded raw Job Zones ({len(df_jz)} rows) & Job Zone Reference ({len(df_jz_ref)} rows)"
    )

    merged_jz = df_jz.merge(
        df_jz_ref[
            [
                "Job Zone",
                "Name",
                "Experience",
                "Education",
                "Job Training",
                "Examples",
                "SVP Range",
            ]
        ],
        on="Job Zone",
        how="left",
    )
    merged_jz.columns = [to_snake(c) for c in merged_jz.columns]
    merged_jz.to_csv(
        os.path.join(PROCESSED_DIR, "onet_job_zones.csv"), index=False
    )
    print(f"Saved onet_job_zones.csv ({len(merged_jz)} merged rows)")


def main():
    ensure_processed_dir()
    build_esco()
    build_onet()
    print("\nETL build complete!")


if __name__ == "__main__":
    main()
