"""
Phase 3B Matching Engine Unit & Integration Test Suite
Tests retriever, parser, taxonomy matcher, scoring model, negation, and recommendation logic.
"""

import unittest
from engine import (
    KnowledgeBaseRetriever,
    ResumeParser,
    TaxonomyMatcher,
    MatchingScorer,
    EvidenceRecommender,
)


class TestMatchingEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.retriever = KnowledgeBaseRetriever()
        cls.parser = ResumeParser()
        cls.matcher = TaxonomyMatcher(retriever=cls.retriever)
        cls.scorer = MatchingScorer()
        cls.recommender = EvidenceRecommender()

    def test_retriever_initialization(self):
        self.assertGreater(len(self.retriever.esco_occupations), 1000)
        self.assertGreater(len(self.retriever.esco_skills), 10000)
        self.assertGreater(len(self.retriever.onet_occupations), 900)

    def test_title_lookup(self):
        esco_occ = self.retriever.find_esco_occupation("Software Developer")
        self.assertIsNotNone(esco_occ)
        self.assertIn("software developer", esco_occ["preferred_label"].lower())

        onet_occ = self.retriever.find_onet_occupation("Web Developer")
        self.assertIsNotNone(onet_occ)
        self.assertIn("15-1254.00", onet_occ["onet_soc_code"])

    def test_parser_and_negation(self):
        sample_resume = """
        John Doe
        Email: john.doe@example.com | Phone: 555-019-2831
        
        Work Experience
        - Developed REST APIs in Python and Flask for cloud services.
        - Managed Docker containers and deployed to AWS.
        - Has no experience in Rust and not proficient in C++.
        
        Education
        Bachelor of Science in Computer Science.
        
        Technical Skills
        Python, Flask, Docker, AWS, SQL
        """
        parsed = self.parser.parse(sample_resume)
        self.assertEqual(parsed["email"], "john.doe@example.com")
        self.assertEqual(parsed["phone"], "555-019-2831")
        self.assertGreaterEqual(len(parsed["experience_bullets"]), 2)
        
        # Verify negation detection
        negated_lower = [t.lower() for t in parsed["negated_terms"]]
        self.assertTrue(any("rust" in t for t in negated_lower))
        self.assertTrue(any("c++" in t for t in negated_lower))

    def test_matcher_skill_extraction(self):
        text = "Skilled in Python, Flask, SQL, Docker, AWS, and React."
        skills = self.matcher.extract_skills(text)
        self.assertIn("Python", skills)
        self.assertIn("Flask", skills)
        self.assertIn("Docker", skills)
        self.assertIn("Aws", [s.title() for s in skills])

    def test_scorer_feature_vector_bounds(self):
        resume_text = "Senior Python Developer with 5 years experience in Flask, MySQL, REST API, Git, Docker, and AWS cloud."
        jd_text = "Looking for a Senior Python Developer with Flask, REST API, MySQL, Git, Docker, and AWS."
        
        target_reqs = self.matcher.extract_target_requirements("Software Developer", jd_text)
        cand_skills = self.matcher.extract_skills(resume_text)
        
        score_res = self.scorer.compute_score(
            resume_text=resume_text,
            jd_text=jd_text,
            candidate_skills=cand_skills,
            essential_skills=target_reqs["essential_skills"],
            optional_skills=target_reqs["optional_skills"],
            job_title="Software Developer",
            retrieved_requirements=target_reqs,
        )
        
        self.assertGreaterEqual(score_res["match_percentage"], 0.0)
        self.assertLessEqual(score_res["match_percentage"], 100.0)
        self.assertIn(score_res["grade"], ["Strong Match", "Moderate Match", "Low Match", "Weak Match"])
        self.assertIn("f_req_skill", score_res["feature_vector"])

    def test_evidence_recommender(self):
        cand_skills = ["Python", "Flask", "SQL"]
        ess_skills = ["Python", "Flask", "Docker", "AWS"]
        opt_skills = ["Kubernetes"]
        bullets = ["Built Python REST APIs using Flask and SQL database."]
        
        rec_res = self.recommender.generate_recommendations(
            candidate_skills=cand_skills,
            essential_skills=ess_skills,
            optional_skills=opt_skills,
            experience_bullets=bullets,
        )
        
        self.assertIn("Docker", rec_res["missing_skills"])
        self.assertTrue(any(s.upper() == "AWS" for s in rec_res["missing_skills"]))
        self.assertIn("Python", rec_res["matched_skills"])

    def test_bug1_ranking_sort_order(self):
        cand_high_match = {"filename": "aarav.pdf", "match_percentage": 85.0, "ats_score": 65}
        cand_high_ats = {"filename": "priya.pdf", "match_percentage": 15.0, "ats_score": 90}
        candidates = [cand_high_ats, cand_high_match]
        ranked = sorted(candidates, key=lambda x: (x.get("match_percentage", 0), x.get("ats_score", 0)), reverse=True)
        self.assertEqual(ranked[0]["filename"], "aarav.pdf")
        self.assertEqual(ranked[1]["filename"], "priya.pdf")

    def test_bug2_jd_skill_coverage_not_penalized_by_unrelated_occupation_skills(self):
        jd_text = "Looking for Senior Python Developer with Python, REST API, PostgreSQL, Docker, AWS, and Git."
        resume_text = "Senior Python Developer skilled in Python, REST API, PostgreSQL, Docker, AWS, and Git."
        target_reqs = self.matcher.extract_target_requirements("Software Developer", jd_text)
        cand_skills = self.matcher.extract_skills(resume_text)
        
        # Verify requirement denominator is bounded by JD skills, not 100+ ESCO skills
        self.assertLessEqual(len(target_reqs["essential_skills"]) + len(target_reqs["optional_skills"]), 10)
        
        score_res = self.scorer.compute_score(
            resume_text=resume_text,
            jd_text=jd_text,
            candidate_skills=cand_skills,
            essential_skills=target_reqs["essential_skills"],
            optional_skills=target_reqs["optional_skills"],
            job_title="Software Developer",
            retrieved_requirements=target_reqs,
        )
        self.assertGreaterEqual(score_res["match_percentage"], 75.0)
        self.assertIn(score_res["grade"], ["Strong Match", "Moderate Match"])

    def test_bug3_canonical_label_equivalence_and_context_gaps(self):
        cand_skills = ["Python (Computer Programming)", "Kubernetes"]
        ess_skills = ["Python", "Kubernetes"]
        opt_skills = []
        bullets = ["Developed backend services in Python."]
        
        rec_res = self.recommender.generate_recommendations(
            candidate_skills=cand_skills,
            essential_skills=ess_skills,
            optional_skills=opt_skills,
            experience_bullets=bullets,
        )
        self.assertNotIn("Python", rec_res["context_gaps"])
        self.assertNotIn("Python (Computer Programming)", rec_res["context_gaps"])
        self.assertIn("Kubernetes", rec_res["context_gaps"])


if __name__ == "__main__":
    unittest.main()

