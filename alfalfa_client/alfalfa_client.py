# ****************************************************************************************************
# :copyright (c) 2008-2021 URBANopt, Alliance for Sustainable Energy, LLC, and other contributors.

# All rights reserved.

# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:

# Redistributions of source code must retain the above copyright notice, this list of conditions
# and the following disclaimer.

# Redistributions in binary form must reproduce the above copyright notice, this list of conditions
# and the following disclaimer in the documentation and/or other materials provided with the
# distribution.

# Neither the name of the copyright holder nor the names of its contributors may be used to endorse
# or promote products derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ****************************************************************************************************

import errno
import json
import os
from collections import OrderedDict
from datetime import datetime
from time import sleep, time
from typing import List, Union
from urllib.parse import urljoin

import requests
from requests_toolbelt import MultipartEncoder

from alfalfa_client.lib import (
    AlfalfaAPIException,
    AlfalfaClientException,
    AlfalfaException,
    parallelize,
    prepare_model
)

ModelID = str
RunID = str


class AlfalfaClient:
    """AlfalfaClient is a wrapper for the Alfalfa REST API"""

    def __init__(self, host: str = 'http://localhost', api_version: str = 'v2'):
        """Create a new alfalfa client instance

        :param host: url for host of alfalfa web server
        :param api_version: version of alfalfa api to use (probably don't change this)
        """
        self.host = host.rstrip('/')
        self.haystack_filter = self.host + '/haystack/read?filter='
        self.haystack_json_header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        self.host = host
        self.api_version = api_version
        self.point_translation_map = {}

    @property
    def url(self):
        return urljoin(self.host, f"api/{self.api_version}/")

    def _request(self, endpoint: str, method="POST", parameters=None) -> requests.Response:
        if parameters:
            response = requests.request(method=method, url=self.url + endpoint, json=parameters, headers={"Content-Type": "application/json"})
        else:
            response = requests.request(method=method, url=self.url + endpoint)

        if response.status_code >= 400:
            try:
                raise AlfalfaAPIException(response)
            except json.JSONDecodeError:
                pass
        response.raise_for_status()

        return response

    @parallelize
    def status(self, run_id: Union[RunID, List[RunID]]) -> str:
        """Get status of run

        :param run_id: id of run or list of ids
        :returns: status of run
        """
        response = self._request(f"runs/{run_id}", method="GET").json()
        return response["payload"]["status"]

    @parallelize
    def get_error_log(self, run_id: Union[RunID, List[RunID]]) -> str:
        """Get error log from run

        :param run_id: id of run or list of ids
        :returns: error log from run
        """
        response = self._request(f"runs/{run_id}", method="GET").json()
        return response["payload"]["errorLog"]

    @parallelize
    def wait(self, run_id: Union[RunID, List[RunID]], desired_status: str, timeout: float = 600) -> None:
        """Wait for a run to have a certain status or timeout with error

        :param run_id: id of run or list of ids
        :param desired_status: status to wait for
        :param timeout: timeout length in seconds
        """

        start_time = time()
        previous_status = None
        current_status = None
        while time() - timeout < start_time:
            try:
                current_status = self.status(run_id)
            except AlfalfaAPIException as e:
                if e.response.status_code != 404:
                    raise e

            if current_status == "ERROR":
                error_log = self.get_error_log(run_id)
                raise AlfalfaException(error_log)

            if current_status != previous_status:
                print("Desired status: {}\t\tCurrent status: {}".format(desired_status, current_status))
                previous_status = current_status
            if current_status == desired_status.upper():
                return
            sleep(2)
        raise AlfalfaClientException(f"'wait' timed out waiting for status: '{desired_status}', current status: '{current_status}'")

    def upload_model(self, model_path: os.PathLike) -> ModelID:
        """Upload a model to alfalfa

        :param model_path: path to model file or folder or list of paths

        :returns: id of model"""
        if not os.path.exists(model_path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), model_path)
        model_path = prepare_model(model_path)
        filename = os.path.basename(model_path)

        payload = {'modelName': filename}

        response = self._request('models/upload', parameters=payload)
        response_body = response.json()["payload"]
        post_url = response_body['url']

        model_id = response_body['modelId']
        form_data = OrderedDict(response_body['fields'])
        form_data['file'] = ('filename', open(model_path, 'rb'))

        encoder = MultipartEncoder(fields=form_data)
        response = requests.post(post_url, data=encoder, headers={'Content-Type': encoder.content_type})
        response.raise_for_status()
        assert response.status_code == 204, "Model upload failed"

        return model_id

    def create_run_from_model(self, model_id: Union[ModelID, List[ModelID]], wait_for_status: bool = True) -> RunID:
        """Create a run from a model

        :param model_id: id of model to create a run from or list of ids
        :param wait_for_status: wait for model to be "READY" before returning

        :returns: id of run created"""
        response = self._request(f"models/{model_id}/createRun")
        run_id = response.json()["payload"]["runId"]

        if wait_for_status:
            self.wait(run_id, "ready")

        return run_id

    @parallelize
    def submit(self, model_path: Union[str, List[str]], wait_for_status: bool = True) -> RunID:
        """Submit a model to alfalfa

        :param model_path: path to the model to upload or list of paths
        :param wait_for_status: wait for model to be "READY" before returning

        :returns: id of created run
        :rtype: str"""

        model_id = self.upload_model(model_path)

        # After the file has been uploaded, then tell BOPTEST to process the run
        # This is done not via the haystack api, but through a REST api
        run_id = self.create_run_from_model(model_id, wait_for_status=wait_for_status)

        return run_id

    @parallelize
    def start(self, run_id: Union[RunID, List[RunID]], start_datetime: datetime, end_datetime: datetime, timescale: int = 5, external_clock: bool = False, realtime: bool = False, wait_for_status: bool = True):
        """Start one run from a model.

        :param run_id: id of run or list of ids
        :param start_datetime: time to start the model from
        :param end_datetime: time to stop the model at (may not be honored for external_clock=True)
        :param timescale: multiple of real time to run model at (for external_clock=False)
        :param external_clock: run model with an external advancer
        :param realtime: run model with timescale=1
        :param wait_for_status: wait for model to be "RUNNING" before returning
        """
        parameters = {
            'startDatetime': str(start_datetime),
            'endDatetime': str(end_datetime),
            'timescale': timescale,
            'externalClock': external_clock,
            'realtime': realtime
        }

        response = self._request(f"runs/{run_id}/start", parameters=parameters)

        assert response.status_code == 204, "Got wrong status_code from alfalfa"

        if wait_for_status:
            self.wait(run_id, "running")

    @parallelize
    def stop(self, run_id: Union[RunID, List[RunID]], wait_for_status: bool = True):
        """Stop a run

        :param run_id: id of the run or list of ids
        :param wait_for_status: wait for the run to be "complete" before returning
        """

        response = self._request(f"runs/{run_id}/stop")

        assert response.status_code == 204, "Got wrong status_code from alfalfa"

        if wait_for_status:
            self.wait(run_id, "complete")

    @parallelize
    def advance(self, run_id: Union[RunID, List[RunID]]) -> None:
        """Advance a run 1 timestep

        :param run_id: id of run or list of ids"""
        self._request(f"runs/{run_id}/advance")

    def get_inputs(self, run_id: str) -> List[str]:
        """Get inputs of run

        :param run_id: id of run
        :returns: list of input names"""

        response = self._request(f"runs/{run_id}/points", method="POST",
                                 parameters={"pointTypes": ["INPUT", "BIDIRECTIONAL"]})
        response_body = response.json()["payload"]
        inputs = []
        for point in response_body:
            if point["name"] != "":
                inputs.append(point["name"])
        return inputs

    def set_inputs(self, run_id: str, inputs: dict) -> None:
        """Set inputs of run

        :param run_id: id of run
        :param inputs: dictionary of point names and input values"""
        point_writes = {}
        for name, value in inputs.items():
            id = self._get_point_translation(run_id, name)
            if id:
                point_writes[id] = value
            else:
                raise AlfalfaClientException(f"No Point exists with name {name}")
        self._request(f"runs/{run_id}/points/values", method="PUT", parameters={'points': point_writes})

    def get_outputs(self, run_id: str) -> dict:
        """Get outputs of run

        :param run_id: id of run
        :returns: dictionary of output names and values"""
        response = self._request(f"runs/{run_id}/points/values", method="POST",
                                 parameters={"pointTypes": ["OUTPUT", "BIDIRECTIONAL"]})
        response_body = response.json()["payload"]
        outputs = {}
        for point, value in response_body.items():
            name = self._get_point_translation(run_id, point)
            outputs[name] = value

        return outputs

    @parallelize
    def get_sim_time(self, run_id: Union[RunID, List[RunID]]) -> datetime:
        """Get sim_time of run

        :param run_id: id of site or list of ids
        :returns: datetime of site
        """
        response = self._request(f"runs/{run_id}/time", method="GET")
        response_body = response.json()["payload"]
        return datetime.strptime(response_body["time"], '%Y-%m-%d %H:%M:%S')

    def set_alias(self, alias: str, run_id: RunID) -> None:
        """Set alias to point to a run_id

        :param run_id: id of run to point alias to
        :param alias: alias to use"""

        self._request(f"aliases/{alias}", method="PUT", parameters={"runId": run_id})

    def get_alias(self, alias: str) -> RunID:
        """Get run_id from alias

        :param alias: alias
        :returns: Id of run associated with alias"""

        response = self._request(f"aliases/{alias}", method="GET")
        response_body = response.json()["payload"]
        return response_body

    def _get_point_translation(self, *args):
        if args in self.point_translation_map:
            return self.point_translation_map[args]
        if args not in self.point_translation_map:
            self._fetch_points(args[0])
        if args in self.point_translation_map:
            return self.point_translation_map[args]
        return None

    def _fetch_points(self, run_id):
        response = self._request(f"runs/{run_id}/points", method="GET")
        for point in response.json()["payload"]:
            self.point_translation_map[(run_id, point["name"])] = point["id"]
            self.point_translation_map[(run_id, point["id"])] = point["name"]
