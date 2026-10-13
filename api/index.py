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
    When Vercel rewrites /(.*) to /api/index, PATH_INFO can be passed as
    /api/index or /api/index/<subpath>. This middleware normalizes it so
    Flask routes match transparently.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
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
