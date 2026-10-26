"""
Live E2E Verification Script for Phase 5 Database Persistence.
Runs against the running backend server (http://127.0.0.1:8000) and directly checks SQLite on-disk persistence.
"""
import urllib.request
import urllib.error
import json
import uuid
import sys
import io

BASE_URL = "http://127.0.0.1:8000"

def request(path, method="GET", data=None, token=None, content_type="application/json"):
    url = f"{BASE_URL}{path}"
    headers = {}
    body = None
    if content_type:
        headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        if isinstance(data, dict):
            body = json.dumps(data).encode("utf-8")
        elif isinstance(data, bytes):
            body = data
        else:
            body = str(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            status = response.status
            return status, json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = {"raw": err_body}
        return e.code, parsed

def upload_multipart_resume(token, filename, content_bytes):
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.write(b"Content-Type: text/plain\r\n\r\n")
    body.write(content_bytes)
    body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode("utf-8"))
    
    return request(
        "/api/analyze/resume",
        method="POST",
        data=body.getvalue(),
        token=token,
        content_type=f"multipart/form-data; boundary={boundary}"
    )

def main():
    print("=== Step 1: Check Live Server Health ===")
    status, health = request("/health")
    assert status == 200, f"Health check failed with {status}"
    print(f"Server is healthy: {health}")

    uid = uuid.uuid4().hex[:8]
    email_a = f"alice_{uid}@example.com"
    email_b = f"bob_{uid}@example.com"
    password = "StrongPassword123!"

    print(f"\n=== Step 2: Register User A ({email_a}) and User B ({email_b}) ===")
    status_a, res_a = request("/api/auth/register", "POST", {"email": email_a, "password": password, "full_name": "Alice"})
    assert status_a == 201, f"Alice registration failed: {res_a}"
    token_a = res_a["access_token"]
    user_a_id = res_a["user"]["id"]
    print(f"Alice registered successfully (User ID: {user_a_id})")

    status_b, res_b = request("/api/auth/register", "POST", {"email": email_b, "password": password, "full_name": "Bob"})
    assert status_b == 201, f"Bob registration failed: {res_b}"
    token_b = res_b["access_token"]
    user_b_id = res_b["user"]["id"]
    print(f"Bob registered successfully (User ID: {user_b_id})")

    print("\n=== Step 3: Application CRUD & Fresh GET Verification ===")
    # 3.1 Create
    status, app = request("/api/applications", "POST", {
        "company": "Live Tech Corp",
        "role": "Lead Architect",
        "status": "Applied",
        "notes": "Submitted application online"
    }, token=token_a)
    assert status == 201, f"Create app failed: {app}"
    app_id = app["id"]
    print(f"Application created (ID: {app_id})")

    # 3.2 Fresh GET request for User A
    status, apps_a = request("/api/applications", "GET", token=token_a)
    assert status == 200 and len(apps_a["items"]) >= 1
    matched = [x for x in apps_a["items"] if x["id"] == app_id]
    assert len(matched) == 1, "Created application missing in fresh GET request"
    assert matched[0]["status"] == "Applied"
    print(f"Application verified in fresh GET: {matched[0]['company']} - {matched[0]['status']}")

    # 3.3 Update status to Interview
    status, updated_app = request(f"/api/applications/{app_id}", "PATCH", {
        "status": "Interview",
        "notes": "Technical screening scheduled"
    }, token=token_a)
    assert status == 200, f"Update app failed: {updated_app}"
    assert updated_app["status"] == "Interview"

    # 3.4 Fresh GET request to verify updated status persisted
    status, apps_a2 = request("/api/applications", "GET", token=token_a)
    matched_updated = [x for x in apps_a2["items"] if x["id"] == app_id][0]
    assert matched_updated["status"] == "Interview"
    assert matched_updated["notes"] == "Technical screening scheduled"
    print(f"Application update verified in fresh GET: status is now '{matched_updated['status']}'")

    print("\n=== Step 4: Cross-User Application Isolation ===")
    # Bob requests applications -> must not see Alice's
    status, apps_b = request("/api/applications", "GET", token=token_b)
    assert status == 200
    assert all(x["id"] != app_id for x in apps_b["items"]), "CRITICAL: Bob can see Alice's application!"
    print("Bob cannot see Alice's application in GET /api/applications")

    # Bob tries to update Alice's application -> 404
    status, err = request(f"/api/applications/{app_id}", "PATCH", {"status": "Rejected"}, token=token_b)
    assert status == 404, f"CRITICAL: Bob modified Alice's application: {status}"
    print("Bob blocked with 404 when attempting to PATCH Alice's application")

    # Bob tries to delete Alice's application -> 404
    status, err = request(f"/api/applications/{app_id}", "DELETE", token=token_b)
    assert status == 404, f"CRITICAL: Bob deleted Alice's application: {status}"
    print("Bob blocked with 404 when attempting to DELETE Alice's application")

    print("\n=== Step 5: Resume Analysis Persistence & Isolation ===")
    resume_text = b"Alice Smith\nExpert Full Stack Engineer with Python, React, Docker, and PostgreSQL."
    status, res_upload = upload_multipart_resume(token_a, "alice_resume.txt", resume_text)
    assert status == 200, f"Resume upload failed: {res_upload}"
    assert "python" in [s.lower() for s in res_upload["skills"]]
    print(f"Alice uploaded resume: extracted skills = {res_upload['skills']}")

    # Fresh GET /api/analyze/resume/latest for Alice
    status, latest_resume_a = request("/api/analyze/resume/latest", "GET", token=token_a)
    assert status == 200 and latest_resume_a["item"] is not None
    assert latest_resume_a["item"]["filename"] == "alice_resume.txt"
    assert "python" in [s.lower() for s in latest_resume_a["item"]["skills"]]
    print(f"Alice fresh GET latest resume verified: {latest_resume_a['item']['filename']} persists")

    # Bob requests latest resume -> must be None
    status, latest_resume_b = request("/api/analyze/resume/latest", "GET", token=token_b)
    assert status == 200 and latest_resume_b["item"] is None, "CRITICAL: Alice's resume leaked to Bob!"
    print("Bob fresh GET latest resume returns None (User isolation confirmed)")

    print("\n=== Step 6: Roadmap Persistence & Isolation ===")
    status, roadmap_res = request("/api/roadmap", "POST", {
        "target_role": "Backend Developer",
        "current_skills": ["python"],
        "weeks": 4
    }, token=token_a)
    assert status == 200, f"Roadmap generation failed: {roadmap_res}"
    print(f"Alice generated roadmap for '{roadmap_res['target_role']}' with {len(roadmap_res['tasks'])} tasks")

    # Fresh GET /api/roadmap/latest for Alice
    status, latest_roadmap_a = request("/api/roadmap/latest", "GET", token=token_a)
    assert status == 200 and latest_roadmap_a["item"] is not None
    assert latest_roadmap_a["item"]["target_role"] == "Backend Developer"
    assert len(latest_roadmap_a["item"]["result_json"]["tasks"]) == len(roadmap_res["tasks"])
    print("Alice fresh GET latest roadmap verified: roadmap data persists")

    # Bob requests latest roadmap -> must be None
    status, latest_roadmap_b = request("/api/roadmap/latest", "GET", token=token_b)
    assert status == 200 and latest_roadmap_b["item"] is None, "CRITICAL: Alice's roadmap leaked to Bob!"
    print("Bob fresh GET latest roadmap returns None (User isolation confirmed)")

    print("\n=== Step 7: Mock Interview Persistence & Isolation ===")
    status, eval_res = request("/api/interviews/evaluate", "POST", {
        "question": "What is ACID compliance in relational databases?",
        "answer": "ACID stands for Atomicity, Consistency, Isolation, and Durability, ensuring transactions are processed reliably.",
        "role": "Backend Developer"
    }, token=token_a)
    assert status == 200, f"Interview evaluation failed: {eval_res}"
    print(f"Alice submitted interview answer: score = {eval_res['practice_score']}")

    # Fresh GET /api/interviews/latest for Alice
    status, latest_interview_a = request("/api/interviews/latest", "GET", token=token_a)
    assert status == 200 and latest_interview_a["item"] is not None
    assert latest_interview_a["item"]["question"] == "What is ACID compliance in relational databases?"
    assert latest_interview_a["item"]["practice_score"] == eval_res["practice_score"]
    print("Alice fresh GET latest interview verified: score and question persist")

    # Bob requests latest interview -> must be None
    status, latest_interview_b = request("/api/interviews/latest", "GET", token=token_b)
    assert status == 200 and latest_interview_b["item"] is None, "CRITICAL: Alice's interview leaked to Bob!"
    print("Bob fresh GET latest interview returns None (User isolation confirmed)")

    print("\n=== Step 8: Direct On-Disk SQLite Verification (Server Restart Survival) ===")
    from app.database import SessionLocal
    import app.models as models

    db = SessionLocal()
    try:
        # Check that Alice's user, application, resume, roadmap, and interview records exist in the persistent SQLite file
        user_record = db.query(models.User).filter(models.User.email == email_a).first()
        assert user_record is not None, "Alice user record not found in SQLite file"

        app_record = db.query(models.Application).filter(models.Application.id == app_id).first()
        assert app_record is not None, "Alice application record not found in SQLite file"
        assert app_record.status == "Interview"

        resume_record = db.query(models.ResumeAnalysis).filter(models.ResumeAnalysis.user_id == user_a_id).first()
        assert resume_record is not None, "Alice resume record not found in SQLite file"
        assert resume_record.filename == "alice_resume.txt"

        roadmap_record = db.query(models.RoadmapSnapshot).filter(models.RoadmapSnapshot.user_id == user_a_id).first()
        assert roadmap_record is not None, "Alice roadmap snapshot not found in SQLite file"

        interview_record = db.query(models.InterviewSession).filter(models.InterviewSession.user_id == user_a_id).first()
        assert interview_record is not None, "Alice interview session not found in SQLite file"

        print("SUCCESS: All 5 entities (User, Application, ResumeAnalysis, RoadmapSnapshot, InterviewSession)")
        print("are verified directly in the persistent SQLite on-disk database file!")

        # Clean up only the records created by this test run to preserve database integrity
        db.delete(interview_record)
        db.delete(roadmap_record)
        db.delete(resume_record)
        db.delete(app_record)
        db.delete(user_record)
        bob_record = db.query(models.User).filter(models.User.email == email_b).first()
        if bob_record:
            db.delete(bob_record)
        db.commit()
        print("Cleaned up verification test records. Existing database records remain untouched.")
    finally:
        db.close()

    print("\n=======================================================")
    print("ALL LIVE PERSISTENCE & DATA-ISOLATION CHECKS PASSED 100%")
    print("=======================================================")

if __name__ == "__main__":
    main()
