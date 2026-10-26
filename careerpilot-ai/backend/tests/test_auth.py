"""
Tests for Authentication and User-Specific Data Ownership.
Verifies registration, password hashing, JWT generation/validation,
unauthorized access denial, and cross-user data isolation.
"""
import pytest
from fastapi.testclient import TestClient
import bcrypt
from app.main import app
import app.models as models
from .conftest import client, TestingSessionLocal, test_engine



def test_user_registration_success_and_password_hashed():
    payload = {
        "email": "alice@example.com",
        "password": "StrongPassword123!",
        "full_name": "Alice Developer",
    }
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["full_name"] == "Alice Developer"
    assert "password" not in data["user"]

    # Verify password was hashed in database (not plaintext)
    db = TestingSessionLocal()
    db_user = db.query(models.User).filter(models.User.email == "alice@example.com").first()
    assert db_user is not None
    assert db_user.hashed_password != "StrongPassword123!"
    assert bcrypt.checkpw("StrongPassword123!".encode("utf-8"), db_user.hashed_password.encode("utf-8"))
    db.close()


def test_duplicate_registration_rejected():
    payload = {
        "email": "alice@example.com",
        "password": "AnotherPassword456!",
        "full_name": "Alice Duplicate",
    }
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 400
    assert "already exists" in r.json()["detail"]


def test_registration_validation_rules():
    # Password too short (<8 chars)
    r = client.post("/api/auth/register", json={"email": "short@example.com", "password": "short"})
    assert r.status_code == 422

    # Invalid email
    r = client.post("/api/auth/register", json={"email": "notanemail", "password": "ValidPassword123!"})
    assert r.status_code == 422


def test_login_success_and_failure():
    # Success
    r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "StrongPassword123!"})
    assert r.status_code == 200
    assert "access_token" in r.json()

    # Wrong password
    r_bad = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "WrongPassword!"})
    assert r_bad.status_code == 401

    # Non-existent user
    r_no_user = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "SomePassword123!"})
    assert r_no_user.status_code == 401


def test_auth_me_endpoint():
    # Unauthorized request (no token, no cookies)
    client.cookies.clear()
    r_unauth = client.get("/api/auth/me")
    assert r_unauth.status_code == 401

    # Login as Alice
    login_res = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "StrongPassword123!"})
    token = login_res.json()["access_token"]

    # Authorized request with Bearer header
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"

    # Invalid token (clear cookie so it relies on the header)
    client.cookies.clear()
    r_invalid = client.get("/api/auth/me", headers={"Authorization": "Bearer fake.tampered.token"})
    assert r_invalid.status_code == 401


def test_protected_applications_and_cross_user_data_isolation():
    # Register Bob
    client.post("/api/auth/register", json={
        "email": "bob@example.com",
        "password": "BobsStrongPassword123!",
        "full_name": "Bob Builder",
    })

    # Clear cookies so tests rely on headers or start unauthenticated
    client.cookies.clear()

    # 1. Unauthenticated request to /api/applications must fail with 401
    r_unauth = client.get("/api/applications")
    assert r_unauth.status_code == 401

    # Login Alice and Bob
    alice_token = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "StrongPassword123!"}).json()["access_token"]
    bob_token = client.post("/api/auth/login", json={"email": "bob@example.com", "password": "BobsStrongPassword123!"}).json()["access_token"]

    # Clear cookie jar on client so that requests strictly use the specified user headers
    client.cookies.clear()

    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # 2. Alice creates an application
    create_res = client.post(

        "/api/applications",
        json={"company": "Acme AI", "role": "ML Engineer", "status": "Applied"},
        headers=alice_headers,
    )
    assert create_res.status_code == 201
    alice_app = create_res.json()
    alice_app_id = alice_app["id"]

    # 3. Alice lists applications -> sees her application
    alice_list = client.get("/api/applications", headers=alice_headers).json()["items"]
    assert any(a["id"] == alice_app_id for a in alice_list)

    # 4. Bob lists applications -> Bob CANNOT see Alice's application!
    bob_list = client.get("/api/applications", headers=bob_headers).json()["items"]
    assert not any(a["id"] == alice_app_id for a in bob_list)

    # 5. Bob tries to update Alice's application -> 404 (Not found / unauthorized)
    bob_patch = client.patch(
        f"/api/applications/{alice_app_id}",
        json={"status": "Rejected"},
        headers=bob_headers,
    )
    assert bob_patch.status_code == 404

    # 6. Bob tries to delete Alice's application -> 404
    bob_delete = client.delete(
        f"/api/applications/{alice_app_id}",
        headers=bob_headers,
    )
    assert bob_delete.status_code == 404

    # 7. Alice's application is untouched
    alice_check = client.get("/api/applications", headers=alice_headers).json()["items"]
    alice_app_check = next(a for a in alice_check if a["id"] == alice_app_id)
    assert alice_app_check["status"] == "Applied"

    # 8. Alice can delete her own application
    alice_delete = client.delete(f"/api/applications/{alice_app_id}", headers=alice_headers)
    assert alice_delete.status_code == 204


def test_httponly_cookie_auth_and_logout():
    cookie_client = TestClient(app)
    # Login sets access_token cookie
    r = cookie_client.post("/api/auth/login", json={"email": "alice@example.com", "password": "StrongPassword123!"})
    assert r.status_code == 200
    assert "access_token" in r.cookies

    # Calling /api/auth/me without Authorization header succeeds via cookie
    r_me = cookie_client.get("/api/auth/me")
    assert r_me.status_code == 200
    assert r_me.json()["email"] == "alice@example.com"

    # Logout clears cookie
    r_logout = cookie_client.post("/api/auth/logout")
    assert r_logout.status_code == 200

    # Subsequent call without cookie fails with 401
    r_after = cookie_client.get("/api/auth/me")
    assert r_after.status_code == 401

