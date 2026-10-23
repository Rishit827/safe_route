@echo off
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
