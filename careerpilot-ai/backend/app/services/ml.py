import re
from typing import Iterable
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SKILL_ALIASES = {
    "python": ["python"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs"],
    "sql": ["sql", "postgresql", "mysql", "sqlite"],
    "postgresql": ["postgresql", "postgres"],
    "machine learning": ["machine learning", "ml"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "nlp": ["nlp", "natural language processing"],
    "fastapi": ["fastapi", "fast api"],
    "rest api": ["rest api", "restful api"],
    "git": ["git", "github"],
    "docker": ["docker", "containerization"],
    "aws": ["aws", "amazon web services"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "data analysis": ["data analysis", "data analytics"],
    "communication": ["communication", "presentation skills"],
    "html": ["html"],
    "css": ["css"],
    "node.js": ["node.js", "nodejs"],
    "java": ["java"],
    "c++": ["c++"],
    "cybersecurity": ["cybersecurity", "cyber security", "information security"],
}

ROLE_SKILLS = {
    "data scientist": [
        ("python", 1.0), ("sql", 0.9), ("pandas", 0.8), ("numpy", 0.7),
        ("machine learning", 1.0), ("scikit-learn", 0.8), ("data analysis", 0.9), ("nlp", 0.6),
    ],
    "machine learning engineer": [
        ("python", 1.0), ("machine learning", 1.0), ("scikit-learn", 0.9),
        ("numpy", 0.7), ("pandas", 0.7), ("rest api", 0.7), ("docker", 0.6), ("sql", 0.6),
    ],
    "frontend developer": [
        ("html", 0.8), ("css", 0.8), ("javascript", 1.0), ("typescript", 0.8),
        ("react", 1.0), ("next.js", 0.7), ("git", 0.6), ("rest api", 0.6),
    ],
    "backend developer": [
        ("python", 0.9), ("sql", 1.0), ("rest api", 1.0), ("fastapi", 0.8),
        ("git", 0.6), ("docker", 0.6), ("postgresql", 0.8),
    ],
    "cybersecurity analyst": [
        ("cybersecurity", 1.0), ("python", 0.6), ("sql", 0.4), ("git", 0.5),
        ("communication", 0.6),
    ],
}

def _contains_phrase(text: str, phrase: str) -> bool:
    pattern = r"(?<![a-zA-Z0-9_])" + re.escape(phrase.lower()) + r"(?![a-zA-Z0-9_])"
    return re.search(pattern, text.lower()) is not None

def extract_skills(text: str) -> list[str]:
    found = []
    for canonical, aliases in SKILL_ALIASES.items():
        if any(_contains_phrase(text, alias) for alias in aliases):
            found.append(canonical)
    return sorted(set(found))

def match_texts(resume_text: str, job_description: str) -> dict:
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        matrix = vectorizer.fit_transform([resume_text, job_description])
        similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0] * 100)
        resume_terms = set(extract_skills(resume_text))
        job_terms = set(extract_skills(job_description))
        matched = sorted(resume_terms & job_terms)
        missing = sorted(job_terms - resume_terms)
    except ValueError:
        similarity, matched, missing = 0.0, [], extract_skills(job_description)
    return {
        "similarity_score": round(similarity, 1),
        "matched_skills": matched,
        "missing_skills": missing,
        "resume_skills": sorted(extract_skills(resume_text)),
        "job_skills": sorted(extract_skills(job_description)),
        "interpretation": "Text similarity is a heuristic, not a hiring probability or an official ATS score.",
    }

def analyze_role_gap(target_role: str, current_skills: Iterable[str]) -> dict:
    role_key = target_role.strip().lower()
    required = ROLE_SKILLS.get(role_key)
    if required is None:
        # Allow role-name variations but don't pretend unknown roles have validated requirements.
        required = next((v for k, v in ROLE_SKILLS.items() if k in role_key or role_key in k), None)
    if required is None:
        return {
            "target_role": target_role,
            "known_role_template": False,
            "message": "No built-in skill template for this role yet. Add required skills manually or choose a supported demo role.",
            "current_skills": sorted({s.lower().strip() for s in current_skills if s.strip()}),
            "matched_skills": [],
            "missing_skills": [],
            "coverage_score": 0,
        }
    current = {s.lower().strip() for s in current_skills if s.strip()}
    matched = []
    missing = []
    total_weight = sum(weight for _, weight in required)
    covered_weight = 0.0
    for skill, weight in required:
        if skill in current:
            matched.append({"skill": skill, "importance": weight})
            covered_weight += weight
        else:
            missing.append({"skill": skill, "importance": weight})
    return {
        "target_role": target_role,
        "known_role_template": True,
        "current_skills": sorted(current),
        "matched_skills": matched,
        "missing_skills": sorted(missing, key=lambda x: x["importance"], reverse=True),
        "coverage_score": round(covered_weight / total_weight * 100) if total_weight else 0,
        "message": "Coverage measures listed skills present in your profile; it does not certify job readiness.",
    }

def build_roadmap(target_role: str, current_skills: Iterable[str], weeks: int = 8) -> dict:
    gap = analyze_role_gap(target_role, current_skills)
    if not gap["known_role_template"]:
        return {"target_role": target_role, "weeks": weeks, "tasks": [], "gap_analysis": gap}
    missing = gap["missing_skills"]
    tasks = []
    for idx, item in enumerate(missing):
        tasks.append({
            "week": min(weeks, 1 + (idx * weeks // max(len(missing), 1))),
            "skill": item["skill"],
            "priority": "High" if item["importance"] >= 0.9 else ("Medium" if item["importance"] >= 0.7 else "Normal"),
            "suggested_task": f"Study {item['skill']} fundamentals and complete one practical exercise.",
            "evidence": f"Save a short note or project demonstrating {item['skill']}.",
        })
    return {"target_role": target_role, "weeks": weeks, "tasks": tasks, "gap_analysis": gap}
