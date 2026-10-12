"""
Matching Scorer Module (Phase 3B)
Computes multi-dimensional feature vector and calculates overall JobFitScore and Grade.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .retriever import normalize_token


class MatchingScorer:

    def __init__(
        self,
        w_req=0.40,
        w_opt=0.15,
        w_know=0.15,
        w_task=0.15,
        w_title=0.15,
    ):
        self.w_req = w_req
        self.w_opt = w_opt
        self.w_know = w_know
        self.w_task = w_task
        self.w_title = w_title

    def compute_score(
        self,
        resume_text,
        jd_text,
        candidate_skills,
        essential_skills,
        optional_skills,
        job_title="",
        retrieved_requirements=None,
    ):
        """Compute individual feature scores and calculate total JobFitScore (0 - 100)."""

        # 1. Required Skill Coverage Ratio (F_req_skill)
        cand_skill_set = set([s.lower() for s in candidate_skills])
        ess_skill_set = set([s.lower() for s in essential_skills])
        opt_skill_set = set([s.lower() for s in optional_skills])

        if ess_skill_set:
            matched_ess = cand_skill_set.intersection(ess_skill_set)
            f_req = len(matched_ess) / len(ess_skill_set)
        else:
            f_req = 1.0 if cand_skill_set else 0.5

        # 2. Optional Skill Coverage Ratio (F_opt_skill)
        if opt_skill_set:
            matched_opt = cand_skill_set.intersection(opt_skill_set)
            f_opt = len(matched_opt) / len(opt_skill_set)
        else:
            f_opt = 1.0 if cand_skill_set else 0.5

        # 3. TF-IDF Textual & Task Similarity (F_task)
        clean_resume = normalize_token(resume_text)
        clean_jd = normalize_token(jd_text)

        if clean_resume and clean_jd:
            try:
                vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
                mat = vec.fit_transform([clean_jd, clean_resume])
                sim = cosine_similarity(mat[0:1], mat[1:2])[0][0]
                f_task = float(max(0.0, min(1.0, sim)))
                feature_names = vec.get_feature_names_out()
                jd_vec = mat[0].toarray()[0]
                top_idx = jd_vec.argsort()[::-1][:10]
                top_keywords = []
                for idx in top_idx:
                    word = feature_names[idx]
                    score = round(float(jd_vec[idx]), 3)
                    if score > 0:
                        top_keywords.append(
                            {
                                "word": word.title(),
                                "score": score,
                                "in_resume": word in clean_resume,
                            }
                        )
            except Exception:
                f_task = 0.0
                top_keywords = []
        else:
            f_task = 0.0
            top_keywords = []

        # 4. Job Title Alignment (F_title)
        clean_title = normalize_token(job_title)
        if clean_title and clean_title in clean_resume:
            f_title = 1.0
        elif clean_title:
            title_words = set(clean_title.split())
            resume_words = set(clean_resume.split())
            if title_words:
                f_title = len(title_words.intersection(resume_words)) / len(title_words)
            else:
                f_title = 0.5
        else:
            f_title = 0.5

        # 5. Knowledge Area Alignment (F_know)
        # Ratio of matched domain skills to total JD domain skills
        f_know = (f_req + f_opt) / 2.0

        # Calculate Calibrated Overall Score (0.0 to 100.0)
        weighted_sum = (
            self.w_req * f_req
            + self.w_opt * f_opt
            + self.w_know * f_know
            + self.w_task * f_task
            + self.w_title * f_title
        )
        total_score = round(float(weighted_sum) * 100.0, 1)

        # Categorize Match Grade
        if total_score >= 75.0:
            grade = "Strong Match"
            recommendation = (
                "Excellent candidate alignment! Resume strongly reflects key requirements "
                "and technical keywords of the job description."
            )
        elif total_score >= 50.0:
            grade = "Moderate Match"
            recommendation = (
                "Good baseline alignment. Candidate possesses several core skills, "
                "but could benefit from highlighting missing job requirements."
            )
        elif total_score >= 25.0:
            grade = "Low Match"
            recommendation = (
                "Fair match. Several key skills and qualifications from the job description "
                "appear missing or unemphasized."
            )
        else:
            grade = "Weak Match"
            recommendation = (
                "Low keyword alignment. Significant skill gaps detected relative to "
                "the target job description."
            )

        return {
            "match_percentage": total_score,
            "grade": grade,
            "recommendation": recommendation,
            "top_keywords": top_keywords,
            "feature_vector": {
                "f_req_skill": round(f_req, 3),
                "f_opt_skill": round(f_opt, 3),
                "f_know": round(f_know, 3),
                "f_task": round(f_task, 3),
                "f_title": round(f_title, 3),
            },
        }
