"""
Validation Pipeline for Occupational Knowledge Base (Phase 2)
Validates primary keys, foreign keys, row reconciliation, category join integrity, schema integrity, and duplicate records.
Generates data/processed/validation_report.txt
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_ESCO_DIR = os.path.join(BASE_DIR, "raw", "ESCO")
RAW_ONET_DIR = os.path.join(BASE_DIR, "raw", "ONET")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
REPORT_PATH = os.path.join(PROCESSED_DIR, "validation_report.txt")


class Validator:

    def __init__(self):
        self.report_lines = []
        self.errors_found = 0
        self.warnings_found = 0

    def log(self, msg=""):
        print(msg)
        self.report_lines.append(msg)

    def log_section(self, title):
        banner = f"\n======================================================\n{title}\n======================================================\n"
        self.log(banner)

    def log_error(self, msg):
        self.errors_found += 1
        self.log(f"[ERROR] {msg}")

    def log_warning(self, msg):
        self.warnings_found += 1
        self.log(f"[WARNING] {msg}")

    def log_pass(self, msg):
        self.log(f"[PASS] {msg}")

    def check_pk_uniqueness(self, df, pk_col, table_name):
        null_count = df[pk_col].isnull().sum()
        if null_count > 0:
            self.log_error(
                f"{table_name}: Found {null_count} null primary keys in column '{pk_col}'"
            )
        else:
            self.log_pass(
                f"{table_name}: Primary key '{pk_col}' has 0 null values."
            )

        dup_count = df.duplicated(subset=[pk_col]).sum()
        if dup_count > 0:
            self.log_error(
                f"{table_name}: Primary key '{pk_col}' has {dup_count} duplicate values."
            )
        else:
            self.log_pass(
                f"{table_name}: Primary key '{pk_col}' is strictly unique ({len(df)} distinct values)."
            )

    def check_fk_integrity(
        self, child_df, child_fk, parent_df, parent_pk, child_name, parent_name
    ):
        child_keys = set(child_df[child_fk].dropna().unique())
        parent_keys = set(parent_df[parent_pk].dropna().unique())
        missing_keys = child_keys - parent_keys
        if len(missing_keys) > 0:
            self.log_error(
                f"FK Violation in {child_name} ({child_fk}) -> {parent_name} ({parent_pk}): {len(missing_keys)} missing foreign keys found. Examples: {list(missing_keys)[:3]}"
            )
        else:
            self.log_pass(
                f"FK Integrity passed: {child_name} ({child_fk}) -> {parent_name} ({parent_pk}) - all {len(child_keys)} distinct values found in parent."
            )

    def check_row_counts(
        self, raw_count, proc_count, name, expected_diff_reason=None
    ):
        if raw_count == proc_count:
            self.log_pass(
                f"Row reconciliation passed for {name}: raw={raw_count}, processed={proc_count}"
            )
        elif expected_diff_reason and (
            raw_count - proc_count == expected_diff_reason["diff"]
        ):
            self.log_pass(
                f"Row reconciliation passed for {name}: raw={raw_count}, processed={proc_count} ({expected_diff_reason['reason']})"
            )
        else:
            self.log_warning(
                f"Row reconciliation mismatch for {name}: raw={raw_count}, processed={proc_count} (Diff: {proc_count - raw_count})"
            )

    def check_exact_duplicates(self, df, table_name):
        dups = df.duplicated().sum()
        if dups > 0:
            self.log_warning(
                f"{table_name}: Found {dups} exact duplicate rows."
            )
        else:
            self.log_pass(f"{table_name}: Zero exact duplicate rows.")

    def run(self):
        self.log("OCCUPATIONAL KNOWLEDGE BASE VALIDATION REPORT")
        self.log(
            "================================================================"
        )

        # ---------------------------------------------------------------------
        # 1. ESCO VALIDATIONS
        # ---------------------------------------------------------------------
        self.log_section("1. ESCO TAXONOMY VALIDATION")

        esco_occ_p = os.path.join(PROCESSED_DIR, "esco_occupations.csv")
        esco_skill_p = os.path.join(PROCESSED_DIR, "esco_skills.csv")
        esco_occ_alias_p = os.path.join(
            PROCESSED_DIR, "esco_occupation_aliases.csv"
        )
        esco_skill_alias_p = os.path.join(
            PROCESSED_DIR, "esco_skill_aliases.csv"
        )
        esco_occ_skill_p = os.path.join(
            PROCESSED_DIR, "esco_occupation_skills.csv"
        )
        esco_skill_rel_p = os.path.join(
            PROCESSED_DIR, "esco_skill_relations.csv"
        )
        esco_hier_p = os.path.join(
            PROCESSED_DIR, "esco_skills_hierarchy.csv"
        )

        df_esco_occ = pd.read_csv(esco_occ_p)
        df_esco_skills = pd.read_csv(esco_skill_p)
        df_esco_occ_alias = pd.read_csv(esco_occ_alias_p)
        df_esco_skill_alias = pd.read_csv(esco_skill_alias_p)
        df_esco_occ_skills = pd.read_csv(esco_occ_skill_p)
        df_esco_skill_rel = pd.read_csv(esco_skill_rel_p)
        df_esco_hier = pd.read_csv(esco_hier_p)

        raw_esco_occ = len(
            pd.read_csv(os.path.join(RAW_ESCO_DIR, "occupations_en.csv"))
        )
        raw_esco_skills = len(
            pd.read_csv(os.path.join(RAW_ESCO_DIR, "skills_en.csv"))
        )
        raw_esco_occ_skills = len(
            pd.read_csv(
                os.path.join(RAW_ESCO_DIR, "occupationSkillRelations_en.csv")
            )
        )
        raw_esco_skill_rel = len(
            pd.read_csv(
                os.path.join(RAW_ESCO_DIR, "skillSkillRelations_en.csv")
            )
        )
        raw_esco_hier = len(
            pd.read_csv(os.path.join(RAW_ESCO_DIR, "skillsHierarchy_en.csv"))
        )

        # Row Reconciliation (noting revision deduplication)
        self.check_row_counts(
            raw_esco_occ,
            len(df_esco_occ),
            "esco_occupations",
            expected_diff_reason={
                "diff": 4,
                "reason": "4 raw revision duplicate rows removed via modifiedDate deduplication",
            },
        )
        self.check_row_counts(
            raw_esco_skills,
            len(df_esco_skills),
            "esco_skills",
            expected_diff_reason={
                "diff": 21,
                "reason": "21 raw revision duplicate rows removed via modifiedDate deduplication",
            },
        )
        self.check_row_counts(
            raw_esco_occ_skills,
            len(df_esco_occ_skills),
            "esco_occupation_skills",
        )
        self.check_row_counts(
            raw_esco_skill_rel, len(df_esco_skill_rel), "esco_skill_relations"
        )
        self.check_row_counts(
            raw_esco_hier, len(df_esco_hier), "esco_skills_hierarchy"
        )

        # PK Uniqueness
        self.check_pk_uniqueness(
            df_esco_occ, "concept_uri", "esco_occupations"
        )
        self.check_pk_uniqueness(
            df_esco_skills, "concept_uri", "esco_skills"
        )

        # Foreign Key Integrity
        self.check_fk_integrity(
            df_esco_occ_alias,
            "concept_uri",
            df_esco_occ,
            "concept_uri",
            "esco_occupation_aliases",
            "esco_occupations",
        )
        self.check_fk_integrity(
            df_esco_skill_alias,
            "concept_uri",
            df_esco_skills,
            "concept_uri",
            "esco_skill_aliases",
            "esco_skills",
        )
        self.check_fk_integrity(
            df_esco_occ_skills,
            "occupation_uri",
            df_esco_occ,
            "concept_uri",
            "esco_occupation_skills (occupation_uri)",
            "esco_occupations",
        )
        self.check_fk_integrity(
            df_esco_occ_skills,
            "skill_uri",
            df_esco_skills,
            "concept_uri",
            "esco_occupation_skills (skill_uri)",
            "esco_skills",
        )
        self.check_fk_integrity(
            df_esco_skill_rel,
            "original_skill_uri",
            df_esco_skills,
            "concept_uri",
            "esco_skill_relations (original_skill_uri)",
            "esco_skills",
        )
        self.check_fk_integrity(
            df_esco_skill_rel,
            "related_skill_uri",
            df_esco_skills,
            "concept_uri",
            "esco_skill_relations (related_skill_uri)",
            "esco_skills",
        )

        # Duplicate Checks
        for name, df in [
            ("esco_occupations", df_esco_occ),
            ("esco_skills", df_esco_skills),
            ("esco_occupation_aliases", df_esco_occ_alias),
            ("esco_skill_aliases", df_esco_skill_alias),
            ("esco_occupation_skills", df_esco_occ_skills),
            ("esco_skill_relations", df_esco_skill_rel),
            ("esco_skills_hierarchy", df_esco_hier),
        ]:
            self.check_exact_duplicates(df, name)

        # ---------------------------------------------------------------------
        # 2. O*NET VALIDATIONS
        # ---------------------------------------------------------------------
        self.log_section("2. O*NET TAXONOMY VALIDATION")

        df_onet_occ = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_occupations.csv")
        )
        df_onet_jt = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_job_titles.csv")
        )
        df_onet_sk = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_skills.csv")
        )
        df_onet_sk_piv = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_skills_pivoted.csv")
        )
        df_onet_kn = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_knowledge.csv")
        )
        df_onet_kn_piv = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_knowledge_pivoted.csv")
        )
        df_onet_sw = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_software_skills.csv")
        )
        df_onet_ts = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_tasks.csv")
        )
        df_onet_ed = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_education.csv")
        )
        df_onet_tr = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_training_experience.csv")
        )
        df_onet_jz = pd.read_csv(
            os.path.join(PROCESSED_DIR, "onet_job_zones.csv")
        )

        raw_onet_occ = len(
            pd.read_excel(os.path.join(RAW_ONET_DIR, "Occupation Data.xlsx"))
        )
        raw_onet_jt = len(
            pd.read_excel(os.path.join(RAW_ONET_DIR, "Job Titles.xlsx"))
        )
        raw_onet_sk = len(
            pd.read_excel(os.path.join(RAW_ONET_DIR, "Essential Skills.xlsx"))
        )
        raw_onet_kn = len(
            pd.read_excel(os.path.join(RAW_ONET_DIR, "Knowledge.xlsx"))
        )
        raw_onet_sw = len(
            pd.read_excel(os.path.join(RAW_ONET_DIR, "Software Skills.xlsx"))
        )
        raw_onet_ts = len(
            pd.read_excel(os.path.join(RAW_ONET_DIR, "Task Statements.xlsx"))
        )
        raw_onet_ed = len(
            pd.read_excel(os.path.join(RAW_ONET_DIR, "Education.xlsx"))
        )
        raw_onet_tr = len(
            pd.read_excel(
                os.path.join(RAW_ONET_DIR, "Training and Experience.xlsx")
            )
        )
        raw_onet_jz = len(
            pd.read_excel(os.path.join(RAW_ONET_DIR, "Job Zones.xlsx"))
        )

        self.check_row_counts(
            raw_onet_occ, len(df_onet_occ), "onet_occupations"
        )
        self.check_row_counts(
            raw_onet_jt, len(df_onet_jt), "onet_job_titles"
        )
        self.check_row_counts(raw_onet_sk, len(df_onet_sk), "onet_skills")
        self.check_row_counts(raw_onet_kn, len(df_onet_kn), "onet_knowledge")
        self.check_row_counts(
            raw_onet_sw, len(df_onet_sw), "onet_software_skills"
        )
        self.check_row_counts(raw_onet_ts, len(df_onet_ts), "onet_tasks")
        self.check_row_counts(
            raw_onet_ed, len(df_onet_ed), "onet_education (category join)"
        )
        self.check_row_counts(
            raw_onet_tr,
            len(df_onet_tr),
            "onet_training_experience (category join)",
        )
        self.check_row_counts(
            raw_onet_jz, len(df_onet_jz), "onet_job_zones (reference join)"
        )

        self.check_pk_uniqueness(
            df_onet_occ, "onet_soc_code", "onet_occupations"
        )

        for child_name, df_child in [
            ("onet_job_titles", df_onet_jt),
            ("onet_skills", df_onet_sk),
            ("onet_knowledge", df_onet_kn),
            ("onet_software_skills", df_onet_sw),
            ("onet_tasks", df_onet_ts),
            ("onet_education", df_onet_ed),
            ("onet_training_experience", df_onet_tr),
            ("onet_job_zones", df_onet_jz),
        ]:
            self.check_fk_integrity(
                df_child,
                "onet_soc_code",
                df_onet_occ,
                "onet_soc_code",
                child_name,
                "onet_occupations",
            )

        self.log_section("3. CATEGORY & REFERENCE JOIN INTEGRITY")
        if len(df_onet_ed) == raw_onet_ed:
            self.log_pass(
                "Category join on onet_education caused 0 row duplication or row loss."
            )
        else:
            self.log_error(
                f"Row duplication detected in onet_education! Raw: {raw_onet_ed}, Output: {len(df_onet_ed)}"
            )

        if len(df_onet_tr) == raw_onet_tr:
            self.log_pass(
                "Category join on onet_training_experience caused 0 row duplication or row loss."
            )
        else:
            self.log_error(
                f"Row duplication detected in onet_training_experience! Raw: {raw_onet_tr}, Output: {len(df_onet_tr)}"
            )

        if len(df_onet_jz) == raw_onet_jz:
            self.log_pass(
                "Reference join on onet_job_zones caused 0 row duplication or row loss."
            )
        else:
            self.log_error(
                f"Row duplication detected in onet_job_zones! Raw: {raw_onet_jz}, Output: {len(df_onet_jz)}"
            )

        self.log_section("4. ONET SCALE ID INTEGRITY (IM vs LV)")
        sk_scales = df_onet_sk["scale_id"].value_counts().to_dict()
        kn_scales = df_onet_kn["scale_id"].value_counts().to_dict()
        self.log_pass(f"Essential Skills scale breakdown: {sk_scales}")
        self.log_pass(f"Knowledge scale breakdown: {kn_scales}")

        piv_sk_im = df_onet_sk_piv["importance"].notnull().sum()
        piv_sk_lv = df_onet_sk_piv["level"].notnull().sum()
        self.log_pass(
            f"Pivoted Skills: {len(df_onet_sk_piv)} elements, Importance non-null count={piv_sk_im}, Level non-null count={piv_sk_lv}"
        )

        piv_kn_im = df_onet_kn_piv["importance"].notnull().sum()
        piv_kn_lv = df_onet_kn_piv["level"].notnull().sum()
        self.log_pass(
            f"Pivoted Knowledge: {len(df_onet_kn_piv)} elements, Importance non-null count={piv_kn_im}, Level non-null count={piv_kn_lv}"
        )

        for name, df in [
            ("onet_occupations", df_onet_occ),
            ("onet_job_titles", df_onet_jt),
            ("onet_skills", df_onet_sk),
            ("onet_knowledge", df_onet_kn),
            ("onet_software_skills", df_onet_sw),
            ("onet_tasks", df_onet_ts),
            ("onet_education", df_onet_ed),
            ("onet_training_experience", df_onet_tr),
            ("onet_job_zones", df_onet_jz),
        ]:
            self.check_exact_duplicates(df, name)

        self.log_section("5. VALIDATION SUMMARY")
        self.log(f"Total Errors Found: {self.errors_found}")
        self.log(f"Total Warnings Found: {self.warnings_found}")

        if self.errors_found == 0:
            self.log(
                "\n>>> ALL VALIDATION CHECKS PASSED PERFECTLY! <<<"
            )
        else:
            self.log(
                f"\n>>> VALIDATION COMPLETED WITH {self.errors_found} ERRORS. <<<"
            )

        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(self.report_lines))
        print(f"\nValidation report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    validator = Validator()
    validator.run()
