# CareerPilot AI — Advanced Career Intelligence Platform

CareerPilot AI is a full-stack AI/ML career-readiness project for students and early-career professionals. It combines resume parsing, explainable job matching, skill-gap recommendations, mock interview practice, and application tracking.

## What is implemented in this starter
- **Next.js + TypeScript frontend** with a premium light dashboard and working API-connected tools.
- **FastAPI backend** with resume text extraction, skills detection, TF-IDF/cosine-similarity job matching, skill-gap analysis, roadmap generation, mock-interview question bank, and application CRUD.
- **PostgreSQL-ready data layer** via SQLAlchemy; SQLite is the default for quick local development.
- **Demo job dataset** clearly marked as sample data.
- **Pytest tests** for the core ML functions.
- Docker Compose for a local PostgreSQL option.

> This is a substantial runnable foundation, not a claim that every production feature is finished. Authentication, production-grade user isolation, live job integrations, and hosted deployment still need configuration and additional implementation before real users' data is stored.

## Architecture
- `frontend/`: Next.js App Router, TypeScript, Tailwind CSS.
- `backend/app/api/`: FastAPI routes.
- `backend/app/services/`: NLP, matching, skill-gap, and interview logic.
- `backend/app/models.py`: SQLAlchemy tables.
- `backend/tests/`: core tests.

## Quick start

### 1. Backend
Python 3.11+ recommended.

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

The default database is a local SQLite file at `backend/careerpilot.db`. To use PostgreSQL, set `DATABASE_URL` (see `.env.example`) and start PostgreSQL first.

### 2. Frontend
Install Node.js 20+.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000. On Windows, copy `.env.example` to `.env.local` manually if `cp` is unavailable.

### 3. PostgreSQL with Docker (optional)
From the project root:

```bash
docker compose up -d db
```

Then set `DATABASE_URL=postgresql+psycopg://careerpilot:careerpilot_dev_password@localhost:5432/careerpilot` in `backend/.env`.

## API endpoints
- `GET /health`
- `POST /api/auth/register` (user registration with bcrypt hashing)
- `POST /api/auth/login` (JWT token & HttpOnly cookie)
- `POST /api/auth/logout` (session invalidation & cookie clearing)
- `GET /api/auth/me` (authenticated user profile)
- `GET /api/jobs`
- `POST /api/analyze/resume` (multipart PDF/TXT upload)
- `POST /api/match` (resume text + job description)
- `POST /api/roadmap` (target role + current skills)
- `GET /api/roadmap/history` (user-scoped roadmap history)
- `GET /api/interviews/questions?role=...&category=technical`
- `POST /api/interviews/evaluate` (transparent rubric-based practice feedback)
- `GET /api/interviews/history` (user-scoped interview practice history)
- `GET /api/applications` (strictly scoped to authenticated user)
- `POST /api/applications` (creates application owned by authenticated user)
- `PATCH /api/applications/{id}` (user-isolated modification)
- `DELETE /api/applications/{id}` (user-isolated deletion)


## ML approach
1. Resume text is extracted from PDF or plain text.
2. Skills are identified using a transparent taxonomy and aliases.
3. TF-IDF + cosine similarity estimates textual alignment between resume and job description.
4. Missing role skills are calculated from a small editable role/skill taxonomy.
5. Recommendations explain matched/missing terms; similarity is not a hiring probability and is not an employer ATS score.

## Tests
```bash
cd backend
pytest
```

## GitHub checklist
- Do not commit `.env`, API keys, uploaded resumes, or database files.
- Update screenshots in `docs/screenshots/`.
- Add your own name and project details to the README.
- Include data-source attribution if you replace the included sample jobs.
- Before production, implement authentication, per-user authorization, rate limiting, secure private file storage, migrations, and deployment health checks.

## Current limitations
- Included job listings are synthetic demo records, not live vacancies.
- Resume extraction supports text PDFs and `.txt`; scanned PDF OCR is not included.
- Interview feedback is rubric-based and intended for practice, not a validated assessment.
- External LLM provider integration is intentionally optional and not required for the core ML pipeline.

