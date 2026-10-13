import sys
import os

# Add root directory to sys.path so app and its packages load seamlessly on Vercel
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app


class VercelPathMiddleware:
    """
    Normalizes PATH_INFO for Vercel serverless rewrites.
    On Vercel, HTTP_X_MATCHED_PATH contains the actual client requested route (e.g. /contact, /login).
    If present, we restore PATH_INFO to match the client's intended route.
    Otherwise, we strip any internal /api/index rewrite prefix.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = environ.get('HTTP_X_MATCHED_PATH')
        if matched_path and not matched_path.startswith('/api/index'):
            environ['PATH_INFO'] = matched_path
        else:
            path_info = environ.get('PATH_INFO', '')
            if path_info in ('/api/index', '/api/index/'):
                environ['PATH_INFO'] = '/'
            elif path_info.startswith('/api/index/'):
                environ['PATH_INFO'] = path_info[len('/api/index'):] or '/'

        return self.wsgi_app(environ, start_response)


# Wrap Flask with Vercel path normalization middleware
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

if __name__ == "__main__":
    app.run()
