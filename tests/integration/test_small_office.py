from datetime import datetime, timedelta

from tests.integration.conftest import create_zip
from alfalfa_client.alfalfa_client import AlfalfaClient
import pytest

@pytest.mark.integration
def test_basic_io():
        zip_file_path = create_zip('small_office')
        alfalfa = AlfalfaClient(host='http://localhost')
        model_id = alfalfa.submit(zip_file_path)

        alfalfa.wait(model_id, "READY")
        alfalfa.start(
            model_id,
            external_clock=True,
            start_datetime=datetime(2019, 1, 2, 0, 2, 0),
            end_datetime=datetime(2019, 1, 3, 0, 0, 0)
        )

        alfalfa.wait(model_id, "RUNNING")

        inputs = alfalfa.inputs(model_id)
        assert "Test_Point_1" in inputs.keys(), "Test_Point_1 is in input points"
        inputs["Test_Point_1"] = 12

        alfalfa.setInputs(model_id, inputs)

        outputs = alfalfa.outputs(model_id)
        assert "Test_Point_1_Value" in outputs.keys(), "Echo point for Test_Point_1 is not in outputs"
        assert "Test_Point_1_Enable_Value" in outputs.keys(), "Echo point for Test_Point_1_Enable is not in outputs"

        # -- Advance a single time step
        alfalfa.advance([model_id])
        alfalfa.advance([model_id])

        outputs = alfalfa.outputs(model_id)
        assert int(outputs["Test_Point_1_Value"] == 12), "Test_Point_1 value has not been processed by the model"
        assert int(outputs["Test_Point_1_Enable_Value"] == 1), "Enable flag for Test_Point_1 is not set correctly"

        # Shut down
        alfalfa.stop(model_id)
        alfalfa.wait(model_id, "COMPLETE")

@pytest.mark.integration
def test_many_model_operations():
        zip_file_path = create_zip('small_office')
        alfalfa = AlfalfaClient(host='http://localhost')
        num_models = 3
        zip_file_paths = [zip_file_path]*num_models

        # Upload Models
        run_ids = alfalfa.submit_many(zip_file_paths)

        for run_id in run_ids:
            assert alfalfa.status(run_id) == "READY", "Run has incorrect status"

        # Start Runs
        start_datetime = datetime(2022, 1, 1, 0, 0)
        alfalfa.start_many(run_ids,
                        start_datetime = start_datetime,
                        end_datetime = datetime(2022, 1, 1, 0, 20),
                        external_clock=True)

        for run_id in run_ids:
            assert alfalfa.status(run_id) == "RUNNING", "Run has incorrect status"
        
        # Advance Runs
        sim_datetime = start_datetime
        for _ in range(5):
            alfalfa.advance(run_ids)
            sim_datetime += timedelta(minutes=1)

        for run_id in run_ids:
            assert sim_datetime.strftime("%Y-%m-%d %H:%M") in alfalfa.get_sim_time(run_id), "Run has wrong time"

        
        # Stop Runs
        alfalfa.stop_many(run_ids)

        for run_id in run_ids:
            assert alfalfa.status(run_id) == "COMPLETE", "Run has incorrect status"
        
