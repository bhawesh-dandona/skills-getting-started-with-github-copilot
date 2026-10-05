"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Practice soccer skills and compete in school matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": []
    },
    "Basketball Team": {
        "description": "Develop basketball skills and play competitive games",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 15,
        "participants": []
    },
    "Art Club": {
        "description": "Explore drawing, painting, and other visual arts",
        "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 20,
        "participants": []
    },
    "Drama Club": {
        "description": "Act, direct, and produce entertaining stage performances",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 25,
        "participants": []
    },
    "Debate Club": {
        "description": "Build public speaking and critical thinking skills through debate",
        "schedule": "Mondays, 3:30 PM - 4:30 PM",
        "max_participants": 18,
        "participants": []
    },
    "Science Club": {
        "description": "Conduct experiments and explore scientific discoveries",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 20,
        "participants": []
    }
}

PASSWORD_HASH_ITERATIONS = 600_000
SESSION_LIFETIME_SECONDS = 12 * 60 * 60
sessions = {}
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, PASSWORD_HASH_ITERATIONS
    )
    return f"{salt.hex()}${password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, expected_hash = stored_hash.split("$", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hash)
    except (AttributeError, ValueError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, PASSWORD_HASH_ITERATIONS
    )
    return hmac.compare_digest(actual, expected)


def get_configured_users():
    try:
        configured_users = json.loads(os.environ.get("APP_USERS", "{}"))
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=500, detail="Invalid account configuration") from error

    if not isinstance(configured_users, dict):
        raise HTTPException(status_code=500, detail="Invalid account configuration")

    return configured_users


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = sessions.get(credentials.credentials)
    if session is None or session["expires_at"] <= time.time():
        sessions.pop(credentials.credentials, None)
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {**session, "token": credentials.credentials}


def get_current_user(session: dict = Depends(get_current_session)):
    return session["user"]


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(current_user: dict = Depends(get_current_user)):
    response = {}
    for name, activity in activities.items():
        response[name] = {
            key: value for key, value in activity.items() if key != "participants"
        }
        response[name]["participant_count"] = len(activity["participants"])
        if current_user["role"] == "admin":
            response[name]["participants"] = activity["participants"]
        else:
            response[name]["participants"] = [
                email
                for email in activity["participants"]
                if email == current_user["email"]
            ]
    return response


@app.post("/auth/login")
def login(login_request: LoginRequest):
    configured_user = get_configured_users().get(login_request.email)
    if (
        not isinstance(configured_user, dict)
        or configured_user.get("role") not in {"student", "admin"}
        or not verify_password(
            login_request.password, configured_user.get("password_hash", "")
        )
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = {"email": login_request.email, "role": configured_user["role"]}
    access_token = secrets.token_urlsafe(32)
    sessions[access_token] = {
        "user": user,
        "expires_at": time.time() + SESSION_LIFETIME_SECONDS,
    }
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@app.post("/auth/logout")
def logout(session: dict = Depends(get_current_session)):
    sessions.pop(session["token"], None)
    return {"message": "Signed out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, current_user: dict = Depends(get_current_user)
):
    """Sign up a student for an activity"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access required")

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    email = current_user["email"]
    if email in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student already signed up for this activity")

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/participants/{email}")
def unregister_participant(
    activity_name: str,
    email: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove a student from an activity"""
    if current_user["role"] != "admin" and current_user["email"] != email:
        raise HTTPException(status_code=403, detail="Cannot remove another student's registration")

    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]
    participants = activity["participants"]

    if email not in participants:
        raise HTTPException(status_code=404, detail="Participant not found")

    participants.remove(email)
    return {"message": f"Removed {email} from {activity_name}"}
