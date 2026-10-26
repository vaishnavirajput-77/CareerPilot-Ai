from app.services.ml import extract_skills, match_texts, analyze_role_gap, build_roadmap
from app.services.interviews import evaluate_answer

def test_extract_skills_aliases():
    skills = extract_skills("I build React.js apps with Python, PostgreSQL and machine learning.")
    assert "react" in skills
    assert "python" in skills
    assert "postgresql" in skills
    assert "machine learning" in skills

def test_match_texts_returns_explanation():
    result = match_texts("Python SQL pandas data analysis", "Python SQL machine learning")
    assert 0 <= result["similarity_score"] <= 100
    assert "python" in result["matched_skills"]
    assert "machine learning" in result["missing_skills"]
    assert "not a hiring probability" in result["interpretation"]

def test_gap_and_roadmap():
    gap = analyze_role_gap("Data Scientist", ["python", "sql"])
    assert gap["known_role_template"] is True
    assert gap["coverage_score"] > 0
    assert any(x["skill"] == "machine learning" for x in gap["missing_skills"])
    roadmap = build_roadmap("Data Scientist", ["python", "sql"], 8)
    assert len(roadmap["tasks"]) > 0

def test_unknown_role_is_honest():
    gap = analyze_role_gap("Astrophysics Product Manager", [])
    assert gap["known_role_template"] is False

def test_interview_feedback_is_bounded():
    result = evaluate_answer("Explain ML", "First I define the problem. For example, I compare models because validation helps. Then I measure the result and explain what I learned.", "ML Engineer")
    assert 0 <= result["practice_score"] <= 100
    assert "disclaimer" in result
