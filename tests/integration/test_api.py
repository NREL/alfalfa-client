from datetime import datetime, timedelta

import pytest

from alfalfa_client.alfalfa_client import AlfalfaClient, RunID
from alfalfa_client.lib import AlfalfaAPIException, AlfalfaClientException


@pytest.mark.integration
def test_api_workflow(client: AlfalfaClient, start_datetime: datetime, end_datetime: datetime, run_id: RunID):
    run_alias = "test_run"
    client.set_alias(run_alias, run_id)

    assert client.status(run_id) == "READY", "Status incorrect after submitting model"

    client.start(run_id, start_datetime, end_datetime, external_clock=True)

    assert client.status(run_id) == "RUNNING", "Status incorrect after starting run"

    current_datetime = client.get_sim_time(run_id)
    alias_current_datetime = client.get_sim_time(run_alias)

    assert isinstance(current_datetime, datetime), "Sim time is of incorrect type"

    client.advance(run_id)
    current_datetime += timedelta(minutes=1)
    alias_current_datetime += timedelta(minutes=1)

    assert client.get_sim_time(run_id) == current_datetime, "Run time did not increment after advance call"
    assert client.get_sim_time(run_alias) == alias_current_datetime, "Run referenced by alias did not increment"
    assert current_datetime == current_datetime, "run_id and run_alias out of sync"

    inputs = client.get_inputs(run_id)
    assert isinstance(inputs, list), "Inputs of incorrect type"
    assert len(inputs) > 0, "No inputs returned"

    inputs_dict = {}
    for key in inputs:
        inputs_dict[key] = 0.0

    client.set_inputs(run_id, inputs_dict)

    outputs = client.get_outputs(run_id)
    assert isinstance(outputs, dict), "Outputs of incorrect type"
    assert len(outputs) > 0, "No outputs returned"

    client.stop(run_id)
    assert client.status(run_id) == "COMPLETE", "Status incorrect after stopping run"


@pytest.mark.integration
def test_error_handling(client: AlfalfaClient, run_id: RunID):

    inputs = {'non_existant_point': 500}
    with pytest.raises(AlfalfaClientException):
        client.set_inputs(run_id, inputs)


@pytest.mark.integration
def test_run_not_found(client: AlfalfaClient):
    with pytest.raises(AlfalfaAPIException):
        client.get_sim_time("0000")

    with pytest.raises(AlfalfaAPIException):
        client.status("0000")

    with pytest.raises(AlfalfaAPIException):
        client.get_error_log("0000")

    with pytest.raises(AlfalfaAPIException):
        client.start("0000", datetime(2020, 1, 1, 1, 1), datetime(2020, 1, 1, 2, 1))

    with pytest.raises(AlfalfaAPIException):
        client.stop("0000")

    with pytest.raises(AlfalfaAPIException):
        client.advance("0000")

    with pytest.raises(AlfalfaAPIException):
        client.get_inputs("0000")

    with pytest.raises(AlfalfaAPIException):
        client.set_inputs("0000", {})

    with pytest.raises(AlfalfaAPIException):
        client.get_outputs("0000")

    with pytest.raises(AlfalfaAPIException):
        client.set_alias("test", "0000")


@pytest.mark.integration
def test_model_not_found(client: AlfalfaClient):
    try:
        client.create_run_from_model("0000")
    except AlfalfaAPIException as e:
        assert not hasattr(e, 'payload')
