"""
Evidence Recommender Module (Phase 3B)
Generates evidence-based gap feedback and actionable recommendations.
"""

import re


class EvidenceRecommender:

    def _clean_skill_label(self, skill_name):
        """Remove parenthetical qualifiers e.g. 'Python (Computer Programming)' -> 'python'."""
        if not skill_name:
            return ""
        return re.sub(r"\s*\(.*?\)", "", str(skill_name)).strip().lower()

    def generate_recommendations(
        self,
        candidate_skills,
        essential_skills,
        optional_skills,
        experience_bullets,
        negated_terms=None,
    ):
        """Categorize matched skills, missing skills, and generate evidence feedback."""
        cand_skill_map = {self._clean_skill_label(s): s for s in candidate_skills}
        ess_skill_map = {self._clean_skill_label(s): s for s in essential_skills}
        opt_skill_map = {self._clean_skill_label(s): s for s in optional_skills}

        target_skill_map = {}
        target_skill_map.update(ess_skill_map)
        target_skill_map.update(opt_skill_map)

        if not target_skill_map:
            target_skill_map = cand_skill_map

        matched_keys = set(cand_skill_map.keys()).intersection(set(target_skill_map.keys()))
        missing_keys = set(target_skill_map.keys()).difference(set(cand_skill_map.keys()))

        matched_skills = sorted([cand_skill_map[k] for k in matched_keys])
        missing_skills = sorted([target_skill_map[k] for k in missing_keys])

        # Identify context gaps (skills listed in skills list but not mentioned in experience bullets)
        exp_text_lower = " ".join(experience_bullets).lower()
        context_gaps = []
        for sk in matched_skills:
            clean_term = self._clean_skill_label(sk)
            pattern = r"(?:\b|_)" + re.escape(clean_term) + r"(?:\b|_)"
            if not (re.search(pattern, exp_text_lower) or clean_term in exp_text_lower):
                context_gaps.append(sk)

        recommendations = []
        if missing_skills:
            critical_missing = [s for s in missing_skills if self._clean_skill_label(s) in ess_skill_map]
            if critical_missing:
                recommendations.append(
                    f"Critical Skill Gaps: Consider highlighting experience in {', '.join(critical_missing[:5])}."
                )

        if context_gaps:
            recommendations.append(
                f"Context Gap: Provide work experience evidence for listed skills: {', '.join(context_gaps[:5])}."
            )

        if not recommendations:
            recommendations.append(
                "Excellent alignment! Candidate resume covers core job requirements and presents clear work history context."
            )

        return {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "context_gaps": context_gaps,
            "detailed_recommendations": recommendations,
        }

