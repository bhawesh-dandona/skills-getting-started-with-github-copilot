from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


def get_auth_headers(email="student@mergington.edu", password="student-password"):
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_root_redirects_to_static_index():
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_login_verifies_credentials_and_returns_role():
    # Arrange
    credentials = {"email": "student@mergington.edu", "password": "student-password"}

    # Act
    response = client.post("/auth/login", json=credentials)

    # Assert
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"] == {
        "email": "student@mergington.edu",
        "role": "student",
    }
    assert response.json()["access_token"]


def test_login_rejects_invalid_credentials():
    response = client.post(
        "/auth/login",
        json={"email": "student@mergington.edu", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_logout_revokes_the_bearer_session():
    headers = get_auth_headers()

    logout_response = client.post("/auth/logout", headers=headers)
    activities_response = client.get("/activities", headers=headers)

    assert logout_response.status_code == 200
    assert activities_response.status_code == 401


def test_get_activities_requires_authentication():
    response = client.get("/activities")

    assert response.status_code == 401


def test_students_can_browse_activities_without_participant_emails():
    response = client.get("/activities", headers=get_auth_headers())

    activity = response.json()["Chess Club"]
    assert response.status_code == 200
    assert "description" in activity
    assert "schedule" in activity
    assert activity["participant_count"] == 2
    assert activity["participants"] == []


def test_students_only_see_their_own_registrations():
    headers = get_auth_headers()
    client.post("/activities/Chess Club/signup", headers=headers)

    response = client.get("/activities", headers=headers)

    assert response.json()["Chess Club"]["participants"] == [
        "student@mergington.edu"
    ]


def test_admins_can_view_participant_emails():
    headers = get_auth_headers("admin@mergington.edu", "admin-password")

    response = client.get("/activities", headers=headers)

    assert response.status_code == 200
    assert "michael@mergington.edu" in response.json()["Chess Club"]["participants"]


def test_signup_adds_participant_to_activity():
    # Arrange
    activity_name = "Soccer Team"
    headers = get_auth_headers()

    # Act
    response = client.post(f"/activities/{activity_name}/signup", headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up student@mergington.edu for {activity_name}"
    }
    assert "student@mergington.edu" in activities_for_admin()[activity_name]["participants"]


def activities_for_admin():
    headers = get_auth_headers("admin@mergington.edu", "admin-password")
    return client.get("/activities", headers=headers).json()


def test_signup_requires_authentication():
    response = client.post("/activities/Soccer Team/signup")

    assert response.status_code == 401


def test_admin_cannot_sign_up_as_a_student():
    headers = get_auth_headers("admin@mergington.edu", "admin-password")

    response = client.post("/activities/Soccer Team/signup", headers=headers)

    assert response.status_code == 403


def test_signup_returns_404_for_unknown_activity():
    # Arrange
    activity_name = "Unknown Activity"
    headers = get_auth_headers()

    # Act
    response = client.post(f"/activities/{activity_name}/signup", headers=headers)

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_returns_400_for_duplicate_participant():
    # Arrange
    activity_name = "Soccer Team"
    headers = get_auth_headers()

    # Act
    client.post(f"/activities/{activity_name}/signup", headers=headers)
    response = client.post(f"/activities/{activity_name}/signup", headers=headers)

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_unregister_participant_removes_email_from_activity():
    # Arrange
    activity_name = "Soccer Team"
    headers = get_auth_headers()
    signup_response = client.post(f"/activities/{activity_name}/signup", headers=headers)

    # Act
    delete_response = client.delete(
        f"/activities/{activity_name}/participants/student@mergington.edu",
        headers=headers,
    )

    # Assert
    assert signup_response.status_code == 200
    assert delete_response.status_code == 200
    assert "student@mergington.edu" not in activities_for_admin()[activity_name]["participants"]


def test_student_cannot_remove_another_students_registration():
    headers = get_auth_headers()

    response = client.delete(
        "/activities/Chess Club/participants/michael@mergington.edu",
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_remove_any_participant():
    headers = get_auth_headers("admin@mergington.edu", "admin-password")

    response = client.delete(
        "/activities/Chess Club/participants/michael@mergington.edu",
        headers=headers,
    )

    assert response.status_code == 200


def test_unregister_participant_returns_404_for_missing_email():
    # Arrange
    activity_name = "Chess Club"
    email = "student@mergington.edu"
    headers = get_auth_headers()

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants/{email}", headers=headers
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Participant not found"


def test_unregister_participant_returns_404_for_unknown_activity():
    # Arrange
    activity_name = "Unknown Activity"
    email = "admin@mergington.edu"
    headers = get_auth_headers("admin@mergington.edu", "admin-password")

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants/{email}", headers=headers
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"
