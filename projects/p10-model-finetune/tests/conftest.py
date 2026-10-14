"""Shared fixtures for P10 model-finetune tests."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import main as app_main  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app_main.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _restore_state():
    """Endpoints mutate module-level stores (create dataset, start training,
    deploy model edits a ModelVersion in place). Snapshot and restore all four
    stores plus the id counters so tests stay independent.
    """
    datasets = copy.deepcopy(app_main._sample_datasets)
    uploads = copy.deepcopy(app_main._dataset_uploads)
    trainings = copy.deepcopy(app_main._sample_trainings)
    evaluations = copy.deepcopy(app_main._sample_evaluations)
    models = copy.deepcopy(app_main._sample_models)
    counters = (
        app_main._user_dataset_counter,
        app_main._user_training_counter,
        app_main._user_eval_counter,
        app_main._user_model_counter,
    )
    yield
    app_main._sample_datasets.clear()
    app_main._sample_datasets.update(datasets)
    app_main._dataset_uploads.clear()
    app_main._dataset_uploads.update(uploads)
    app_main._sample_trainings.clear()
    app_main._sample_trainings.update(trainings)
    app_main._sample_evaluations.clear()
    app_main._sample_evaluations.update(evaluations)
    app_main._sample_models.clear()
    app_main._sample_models.update(models)
    (
        app_main._user_dataset_counter,
        app_main._user_training_counter,
        app_main._user_eval_counter,
        app_main._user_model_counter,
    ) = counters
