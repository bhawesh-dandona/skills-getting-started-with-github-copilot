from copy import deepcopy
import json

import pytest

from src.app import activities, hash_password

TEST_USERS = {
    "student@mergington.edu": {
        "password_hash": hash_password("student-password"),
        "role": "student",
    },
    "admin@mergington.edu": {
        "password_hash": hash_password("admin-password"),
        "role": "admin",
    },
}


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(activities)

    yield

    activities.clear()
    activities.update(original_activities)


@pytest.fixture(autouse=True)
def configure_test_users(monkeypatch):
    monkeypatch.setenv("APP_USERS", json.dumps(TEST_USERS))
