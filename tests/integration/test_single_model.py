from alfalfa_client.alfalfa_client import AlfalfaClient
from alfalfa_client.lib import AlfalfaException
from datetime import datetime, timedelta
import pytest

from tests.integration.conftest import external_clock_run_id

@pytest.mark.integration
def test_advance(client: AlfalfaClient, external_clock_run_id: str):
    current_datetime = datetime.strptime(client.get_sim_time(external_clock_run_id), '%Y-%m-%d %H:%M:%S')
    client.advance([external_clock_run_id])
    current_datetime += timedelta(minutes=1)
    assert datetime.strptime(client.get_sim_time(external_clock_run_id), '%Y-%m-%d %H:%M:%S') == current_datetime

@pytest.mark.integration
def test_status(client: AlfalfaClient, internal_clock_run_id: str):
    assert client.status(internal_clock_run_id) == "RUNNING"

@pytest.mark.integration
def test_input(client: AlfalfaClient, internal_clock_run_id: str):
    inputs = client.inputs(internal_clock_run_id)
    assert type(inputs) == dict
    assert len(inputs) > 0
    setInputs = {}
    for key in inputs.keys():
        setInputs[key] = 0.0
    client.setInputs(internal_clock_run_id, setInputs)

@pytest.mark.integration
def test_output(client: AlfalfaClient, internal_clock_run_id: str):
    outputs = client.outputs(internal_clock_run_id)
    assert type(outputs) == dict
    assert len(outputs) > 0

@pytest.mark.integration
def test_stop(client: AlfalfaClient, internal_clock_run_id: str):
    client.stop(internal_clock_run_id)
    assert client.status(internal_clock_run_id) == "COMPLETE"

@pytest.mark.integration
def test_error_handling(client: AlfalfaClient, run_id: str):
    with pytest.raises(AlfalfaException):
        client.start(run_id)
