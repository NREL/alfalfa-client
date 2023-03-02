from datetime import timedelta

import pytest

from alfalfa_client.alfalfa_client import AlfalfaClient


@pytest.mark.integration
def test_advance(client: AlfalfaClient, external_clock_run_id: str):
    current_datetime = client.get_sim_time(external_clock_run_id)
    client.advance([external_clock_run_id])
    current_datetime += timedelta(minutes=1)
    assert client.get_sim_time(external_clock_run_id) == current_datetime


@pytest.mark.integration
def test_status(client: AlfalfaClient, internal_clock_run_id: str):
    assert client.status(internal_clock_run_id) == "running"


@pytest.mark.integration
def test_input(client: AlfalfaClient, internal_clock_run_id: str):
    inputs = client.get_inputs(internal_clock_run_id)
    assert isinstance(inputs, list)
    assert len(inputs) > 0
    inputs = {}
    for key in inputs:
        inputs[key] = 0.0
    client.set_inputs(internal_clock_run_id, inputs)


@pytest.mark.integration
def test_output(client: AlfalfaClient, internal_clock_run_id: str):
    outputs = client.get_outputs(internal_clock_run_id)
    assert isinstance(outputs, dict)
    assert len(outputs) > 0


@pytest.mark.integration
def test_stop(client: AlfalfaClient, internal_clock_run_id: str):
    client.stop(internal_clock_run_id)
    assert client.status(internal_clock_run_id) == "complete"


@pytest.mark.integration
def test_alias(client: AlfalfaClient, internal_clock_run_id: str):
    client.set_alias("test", internal_clock_run_id)
    assert client.get_alias("test") == internal_clock_run_id


# @pytest.mark.integration
# def test_error_handling(client: AlfalfaClient, run_id: str):
#     with pytest.raises(AlfalfaException):
#         client.start(run_id)
