from copy import deepcopy

import pytest

from src.app import activities


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(activities)

    yield

    activities.clear()
    activities.update(original_activities)
