"""Vercel 서버리스 함수 진입점: /api/* 요청을 backend 의 Flask 앱으로 넘긴다."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app import app  # noqa: E402  (Vercel 이 WSGI 앱 `app` 을 찾아 실행)
