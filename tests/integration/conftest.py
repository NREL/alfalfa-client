import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from alfalfa_client.alfalfa_client import AlfalfaClient


def pytest_generate_tests(metafunc):
    model_dir = Path(os.path.dirname(__file__)) / 'models'
    if "model_path" in metafunc.fixturenames:
        model_paths = [
            model_dir / 'refrig_case_osw'
        ]

        metafunc.parametrize("model_path", model_paths)


def create_zip(model_dir):
    zip_file_fd, zip_file_path = tempfile.mkstemp(suffix='.zip')
    zip_file_path = Path(zip_file_path)
    shutil.make_archive(zip_file_path.parent / zip_file_path.stem, "zip", model_dir)

    return zip_file_path


@pytest.fixture
def client():
    yield AlfalfaClient('http://localhost')


@pytest.fixture
def run_id(client: AlfalfaClient, model_path: Path):
    run_id = client.submit(model_path)

    yield run_id

    status = client.status(run_id)
    if status == "running":
        client.stop(run_id)


@pytest.fixture
def start_datetime():
    yield datetime(2020, 1, 1, 0, 0)


@pytest.fixture
def end_datetime():
    yield datetime(2020, 1, 1, 0, 5)


@pytest.fixture
def internal_clock_run_id(client: AlfalfaClient, run_id: str, start_datetime: datetime, end_datetime: datetime):
    params = {
        "external_clock": False,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "timescale": 5
    }
    client.start(run_id, **params)
    yield run_id


@pytest.fixture
def external_clock_run_id(client: AlfalfaClient, run_id: str, start_datetime: datetime, end_datetime: datetime):
    params = {
        "external_clock": True,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime
    }
    client.start(run_id, **params)
    yield run_id
