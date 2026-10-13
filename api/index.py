import sys
import os

# Add root directory to sys.path so relative imports and app module load seamlessly on Vercel
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

# Expose WSGI handler for Vercel Serverless Function
if __name__ == "__main__":
    app.run()
