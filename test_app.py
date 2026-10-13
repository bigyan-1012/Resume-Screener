import os
import unittest
import tempfile
from unittest.mock import patch
import pypdf
from app import (
    app, clean_text, extract_skills_from_text,
    analyze_resume_against_jd, check_ats_formatting,
    db_query, contact_rate_limit_store
)


class TestResumeScreener(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()

    def test_clean_text(self):
        raw = "Hello World! Visit https://example.com/ resume\n\n\ttest."
        cleaned = clean_text(raw)
        self.assertNotIn("https", cleaned)
        self.assertIn("hello world", cleaned)
        self.assertIn("resume test", cleaned)

    def test_extract_skills_from_text(self):
        sample_text = "Proficient in Python, Flask, SQL, React.js, Docker, and AWS."
        skills = extract_skills_from_text(sample_text)
        self.assertIn("Python", skills)
        self.assertIn("Flask", skills)
        self.assertIn("SQL", skills)
        self.assertIn("Docker", skills)
        self.assertIn("AWS", skills)

    def test_check_ats_formatting(self):
        sample_text = """
        John Doe
        Email: john.doe@example.com
        Phone: +1 555-123-4567

        Professional Experience
        Senior Developer at Tech Corp. Worked on Python, Flask, and SQL backend APIs.

        Education
        Bachelor of Science in Computer Science, State University.

        Technical Skills
        Python, Flask, SQL, Git, AWS
        """
        ats_result = check_ats_formatting(sample_text)
        self.assertGreaterEqual(ats_result['ats_score'], 80)
        check_names = [c['name'] for c in ats_result['checks'] if c['passed']]
        self.assertIn("Contact Email", check_names)
        self.assertIn("Phone Number", check_names)
        self.assertIn("Work Experience Section", check_names)
        self.assertIn("Education Section", check_names)

    def test_analyze_resume_against_jd_strong_match(self):
        resume_text = "Senior Python Developer with 5 years experience in Flask, MySQL, REST API, Git, Docker, and AWS cloud."
        jd_text = "Looking for a Senior Python Developer with Flask, REST API, MySQL, Git, Docker, and AWS."
        result = analyze_resume_against_jd(resume_text, jd_text)
        
        self.assertGreaterEqual(result['match_percentage'], 40.0)
        self.assertIn(result['grade'], ["Strong Match", "Moderate Match", "Low Match"])
        self.assertIn("Python", result['matched_skills'])
        self.assertIn("Flask", result['matched_skills'])
        self.assertIn('ats_score', result)

    def test_analyze_resume_against_jd_missing_skills(self):
        resume_text = "Frontend Developer skilled in HTML, CSS, JavaScript, React.js."
        jd_text = "Seeking Python Engineer with Flask, Docker, Kubernetes, AWS, and Machine Learning background."
        result = analyze_resume_against_jd(resume_text, jd_text)
        
        self.assertIn("Python", result['missing_skills'])
        self.assertIn("Docker", result['missing_skills'])

    def test_routes_unauthenticated(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

        upload_resp = self.client.post('/api/upload')
        self.assertEqual(upload_resp.status_code, 401)

        analyze_resp = self.client.post('/api/analyze', json={})
        self.assertEqual(analyze_resp.status_code, 401)

        history_resp = self.client.get('/api/history')
        self.assertEqual(history_resp.status_code, 401)

    def test_signup_and_login_flow(self):
        # Signup user
        signup_resp = self.client.post('/signup', data={'username': 'unittest_user', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(signup_resp.status_code, 200)

        # Logout user
        self.client.get('/logout')

        # Login user
        login_resp = self.client.post('/login', data={'username': 'unittest_user', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)

    @patch('app.extract_text_from_pdf')
    def test_upload_analyze_and_history_flow(self, mock_extract):
        mock_extract.return_value = "John Doe\nEmail: john@example.com\nPhone: 555-123-4567\nWork Experience\nSenior Python Developer with Flask, SQL, Docker, and AWS experience.\nEducation\nB.S. Computer Science\nSkills\nPython, Flask, SQL, Docker"

        # Create dummy PDF file
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            writer.write(tmp)
            tmp_path = tmp.name

        try:
            with self.client.session_transaction() as sess:
                sess['username'] = 'flow_testuser'

            with open(tmp_path, 'rb') as f:
                upload_resp = self.client.post(
                    '/api/upload',
                    data={'resume': (f, 'test_resume.pdf')},
                    content_type='multipart/form-data'
                )
            
            self.assertEqual(upload_resp.status_code, 200)
            json_data = upload_resp.get_json()
            self.assertTrue(json_data['success'])
            filename = json_data['filename']

            # Run analysis API
            analyze_resp = self.client.post(
                '/api/analyze',
                json={
                    'filename': filename,
                    'job_title': 'Python Developer',
                    'job_description': 'We need a Python software engineer with Flask, SQL, and Docker.'
                }
            )
            self.assertEqual(analyze_resp.status_code, 200)
            res_json = analyze_resp.get_json()
            self.assertTrue(res_json['success'])
            self.assertIn('match_percentage', res_json)
            self.assertIn('Python', res_json['matched_skills'])
            self.assertIn('ats_score', res_json)

            # Test History API
            hist_resp = self.client.get('/api/history')
            self.assertEqual(hist_resp.status_code, 200)
            hist_json = hist_resp.get_json()
            self.assertTrue(hist_json['success'])
            self.assertGreaterEqual(len(hist_json['history']), 1)
            item_id = hist_json['history'][0]['id']

            # Delete single item
            del_resp = self.client.delete(f'/api/history/{item_id}')
            self.assertEqual(del_resp.status_code, 200)
            self.assertTrue(del_resp.get_json()['success'])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


    def test_contact_page_route(self):
        resp = self.client.get('/contact')
        self.assertEqual(resp.status_code, 200)

    def test_contact_submission_success(self):
        contact_rate_limit_store.clear()
        payload = {
            'name': 'Alex Morgan',
            'email': 'alex.morgan@example.com',
            'subject': 'Resume Analysis Support',
            'message': 'Hello, I have a question about how ATS keyword weighting is calculated.'
        }
        resp = self.client.post('/api/contact', json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('ticket_id', data)
        self.assertTrue(data['ticket_id'].startswith('HH-TK-'))
        ticket_id = data['ticket_id']

        # Verify database record
        with app.app_context():
            ticket = db_query("SELECT * FROM support_tickets WHERE ticket_id = %s", (ticket_id,), fetchone=True)
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket['name'], 'Alex Morgan')
            self.assertEqual(ticket['email'], 'alex.morgan@example.com')
            self.assertEqual(ticket['status'], 'open')

    def test_contact_validation_missing_name(self):
        payload = {
            'name': '',
            'email': 'valid@example.com',
            'subject': 'General Inquiry',
            'message': 'This is a test inquiry message with sufficient length.'
        }
        resp = self.client.post('/api/contact', json=payload)
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['success'])
        self.assertIn('name', data['error'].lower())

    def test_contact_validation_invalid_email(self):
        payload = {
            'name': 'Valid User',
            'email': 'invalid-email-address',
            'subject': 'General Inquiry',
            'message': 'This is a test inquiry message with sufficient length.'
        }
        resp = self.client.post('/api/contact', json=payload)
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['success'])
        self.assertIn('email', data['error'].lower())

    def test_contact_validation_short_message(self):
        payload = {
            'name': 'Valid User',
            'email': 'valid@example.com',
            'subject': 'General Inquiry',
            'message': 'Too short'
        }
        resp = self.client.post('/api/contact', json=payload)
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['success'])
        self.assertIn('message', data['error'].lower())

    def test_contact_honeypot_spam_trap(self):
        payload = {
            'name': 'Spam Bot',
            'email': 'spambot@example.com',
            'subject': 'Spam subject',
            'message': 'Spam message that should be ignored by the system.',
            'hp_website': 'http://buy-viagra-now.com'
        }
        resp = self.client.post('/api/contact', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

        # Verify spambot was NOT saved to support_tickets
        with app.app_context():
            ticket = db_query("SELECT * FROM support_tickets WHERE email = %s", ('spambot@example.com',), fetchone=True)
            self.assertIsNone(ticket)

    def test_contact_ticket_status_lookup(self):
        contact_rate_limit_store.clear()
        payload = {
            'name': 'Status Check User',
            'email': 'status.check@example.com',
            'subject': 'Status Inquiry',
            'message': 'Checking that status lookup endpoint functions properly.'
        }
        resp = self.client.post('/api/contact', json=payload)
        self.assertEqual(resp.status_code, 201)
        ticket_id = resp.get_json()['ticket_id']

        status_resp = self.client.get(f'/api/contact/status/{ticket_id}')
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.get_json()
        self.assertTrue(status_data['success'])
        self.assertEqual(status_data['ticket']['ticket_id'], ticket_id)
        self.assertEqual(status_data['ticket']['status'], 'open')

    def test_contact_rate_limiting(self):
        contact_rate_limit_store.clear()
        payload = {
            'name': 'Rate Limit Tester',
            'email': 'ratelimit@example.com',
            'subject': 'Rate Limit Test',
            'message': 'Testing sliding window rate limit on contact form endpoint.'
        }
        # First 5 should succeed (201)
        for _ in range(5):
            resp = self.client.post('/api/contact', json=payload)
            self.assertEqual(resp.status_code, 201)

        # 6th should be rate-limited (429)
        rate_resp = self.client.post('/api/contact', json=payload)
        self.assertEqual(rate_resp.status_code, 429)
        self.assertIn('too many requests', rate_resp.get_json()['error'].lower())
        contact_rate_limit_store.clear()


if __name__ == '__main__':
    unittest.main()
