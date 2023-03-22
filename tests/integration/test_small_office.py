from datetime import datetime, timedelta

import pytest

from alfalfa_client.alfalfa_client import AlfalfaClient


@pytest.mark.integration
def test_basic_io():
    alfalfa = AlfalfaClient(host='http://localhost')
    model_id = alfalfa.submit('tests/integration/models/small_office')

    alfalfa.wait(model_id, "ready")
    alfalfa.start(
        model_id,
        external_clock=True,
        start_datetime=datetime(2019, 1, 2, 0, 2, 0),
        end_datetime=datetime(2019, 1, 3, 0, 0, 0)
    )

    alfalfa.wait(model_id, "running")

    inputs = alfalfa.get_inputs(model_id)
    assert "Test_Point_1" in inputs, "Test_Point_1 is in input points"
    inputs = {}
    inputs["Test_Point_1"] = 12

    alfalfa.set_inputs(model_id, inputs)

    outputs = alfalfa.get_outputs(model_id)
    assert "Test_Point_1" in outputs.keys(), "Echo point for Test_Point_1 is not in outputs"

    # -- Advance a single time step
    alfalfa.advance(model_id)

    outputs = alfalfa.get_outputs(model_id)

    assert pytest.approx(12) == outputs["Test_Point_1"], "Test_Point_1 value has not been processed by the model"

    # Shut down
    alfalfa.stop(model_id)
    alfalfa.wait(model_id, "complete")


@pytest.mark.integration
def test_many_model_operations():
    alfalfa = AlfalfaClient(host='http://localhost')
    num_models = 2
    model_paths = ['tests/integration/models/small_office'] * num_models

    # Upload Models
    run_ids = alfalfa.submit(model_path=model_paths)

    for run_id in run_ids:
        assert alfalfa.status(run_id) == "ready", "Run has incorrect status"

    # Start Runs
    start_datetime = datetime(2022, 1, 1, 0, 0)
    alfalfa.start(run_ids,
                  start_datetime=start_datetime,
                  end_datetime=datetime(2022, 1, 1, 0, 20),
                  external_clock=True)

    for run_id in run_ids:
        assert alfalfa.status(run_id) == "running", "Run has incorrect status"

    # Advance Runs
    sim_datetime = start_datetime
    for _ in range(5):
        alfalfa.advance(run_ids)
        sim_datetime += timedelta(minutes=1)

        for run_id in run_ids:
            assert sim_datetime == alfalfa.get_sim_time(run_id), "Run has wrong time"

    # Stop Runs
    alfalfa.stop(run_ids)

    for run_id in run_ids:
        assert alfalfa.status(run_id) == "complete", "Run has incorrect status"
