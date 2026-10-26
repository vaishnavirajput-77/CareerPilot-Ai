# conftest.py — ensures pytest can import the `app` package when run from backend/
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
