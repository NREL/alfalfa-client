"""
****************************************************************************************************
:copyright (c) 2008-2021 URBANopt, Alliance for Sustainable Energy, LLC, and other contributors.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions
and the following disclaimer in the documentation and/or other materials provided with the
distribution.

Neither the name of the copyright holder nor the names of its contributors may be used to endorse
or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
****************************************************************************************************
"""

import json
import os
from collections import OrderedDict
from datetime import datetime
from numbers import Number
from time import sleep, time
from typing import List, Union
from urllib.parse import urljoin

import requests
from requests.exceptions import HTTPError
from requests_toolbelt import MultipartEncoder

from alfalfa_client.lib import (
    AlfalfaAPIException,
    AlfalfaClientException,
    AlfalfaException,
    parallelize,
    prepare_model
)

ModelID = str
SiteID = str


class AlfalfaClient:

    def __init__(self, host: str = 'http://localhost', api_version: str = 'v2'):
        """Create a new alfalfa client instance

        :param host: url for host of alfalfa web server
        :param api_version: version of alfalfa api to use (probably don't change this)
        """
        self.host = host.lstrip('/')
        self.haystack_filter = self.host + '/haystack/read?filter='
        self.haystack_json_header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        self.host = host
        self.api_version = api_version

    @property
    def url(self):
        return urljoin(self.host, f"api/{self.api_version}/")

    def _request(self, endpoint: str, method="POST", parameters=None) -> requests.Response:
        if parameters:
            response = requests.request(method=method, url=self.url + endpoint, json=parameters, headers={"Content-Type": "application/json"})
        else:
            response = requests.request(method=method, url=self.url + endpoint)

        if response.status_code == 400:
            try:
                body = response.json()
                raise AlfalfaAPIException(body["error"])
            except json.JSONDecodeError:
                pass
        response.raise_for_status()

        return response

    @parallelize
    def status(self, site_id: Union[SiteID, List[SiteID]]) -> str:
        """Get status of site

        :param site_id: id of site or list of ids
        :returns: status of site
        """
        response = self._request(f"sites/{site_id}", method="GET").json()
        return response["data"]["status"]

    @parallelize
    def get_error_log(self, site_id: Union[SiteID, List[SiteID]]) -> str:
        """Get error log from site

        :param site_id: id of site or list of ids
        :returns: error log from site
        """
        response = self._request(f"sites/{site_id}", method="GET").json()
        return response["data"]["errorLog"]

    @parallelize
    def wait(self, site_id: Union[SiteID, List[SiteID]], desired_status: str, timeout: float = 600) -> None:
        """Wait for a site to have a certain status or timeout with error

        :param site_id: id of site or list of ids
        :param desired_status: status to wait for
        :param timeout: timeout length in seconds
        """

        start_time = time()
        previous_status = None
        current_status = None
        while time() - timeout < start_time:
            try:
                current_status = self.status(site_id)
            except HTTPError as e:
                if e.response.status_code != 404:
                    raise e

            if current_status == "error":
                error_log = self.get_error_log(site_id)
                raise AlfalfaException(error_log)

            if current_status != previous_status:
                print("Desired status: {}\t\tCurrent status: {}".format(desired_status, current_status))
                previous_status = current_status
            if current_status == desired_status:
                return
            sleep(2)
        raise AlfalfaClientException(f"'wait' timed out waiting for status: '{desired_status}', current status: '{current_status}'")

    def upload_model(self, model_path: os.PathLike) -> ModelID:
        """Upload a model to alfalfa

        :param model_path: path to model file or folder or list of paths

        :returns: id of model"""
        model_path = prepare_model(model_path)
        filename = os.path.basename(model_path)

        payload = {'modelName': filename}

        response = self._request('models/upload', parameters=payload)
        response_body = response.json()
        post_url = response_body['url']

        model_id = response_body['modelID']
        form_data = OrderedDict(response_body['fields'])
        form_data['file'] = ('filename', open(model_path, 'rb'))

        encoder = MultipartEncoder(fields=form_data)
        response = requests.post(post_url, data=encoder, headers={'Content-Type': encoder.content_type})
        response.raise_for_status()
        assert response.status_code == 204, "Model upload failed"

        return model_id

    def create_run_from_model(self, model_id: Union[ModelID, List[ModelID]], wait_for_status: bool = True) -> SiteID:
        """Create a run from a model

        :param model_id: id of model to create a run from or list of ids
        :param wait_for_status: wait for model to be "READY" before returning

        :returns: id of run created"""
        response = self._request(f"models/{model_id}/createRun")
        run_id = response.json()["runID"]

        if wait_for_status:
            self.wait(run_id, "ready")

        return run_id

    @parallelize
    def submit(self, model_path: Union[str, List[str]], wait_for_status: bool = True) -> SiteID:
        """Submit a model to alfalfa

        :param model_path: path to the model to upload or list of paths
        :param wait_for_status: wait for model to be "READY" before returning

        :returns: id of created run
        :rtype: str"""

        model_id = self.upload_model(model_path)

        # After the file has been uploaded, then tell BOPTEST to process the site
        # This is done not via the haystack api, but through a REST api
        run_id = self.create_run_from_model(model_id, wait_for_status=wait_for_status)

        return run_id

    @parallelize
    def start(self, site_id: Union[SiteID, List[SiteID]], start_datetime: Union[Number, datetime], end_datetime: Union[Number, datetime], timescale: int = 5, external_clock: bool = False, realtime: bool = False, wait_for_status: bool = True):
        """Start one run from a model.

        :param site_id: id of site or list of ids
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

        response = self._request(f"sites/{site_id}/start", parameters=parameters)

        assert response.status_code == 204, "Got wrong status_code from alfalfa"

        if wait_for_status:
            self.wait(site_id, "running")

    @parallelize
    def stop(self, site_id: Union[SiteID, List[SiteID]], wait_for_status: bool = True):
        """Stop a run

        :param site_id: id of the site or list of ids
        :param wait_for_status: wait for the site to be "complete" before returning
        """

        response = self._request(f"sites/{site_id}/stop")

        assert response.status_code == 204, "Got wrong status_code from alfalfa"

        if wait_for_status:
            self.wait(site_id, "complete")

    @parallelize
    def advance(self, site_id: Union[SiteID, List[SiteID]]) -> None:
        """Advance a site 1 timestep

        :param site_id: id of site or list of ids"""
        self._request(f"sites/{site_id}/advance")

    def get_inputs(self, site_id: str) -> List[str]:
        """Get inputs of site

        :param site_id: id of site
        :returns: list of input names"""

        response = self._request(f"sites/{site_id}/points/inputs", method="GET")
        response_body = response.json()
        inputs = []
        for point in response_body["data"]:
            if point["name"] != "":
                inputs.append(point["name"])
        return inputs

    def set_inputs(self, site_id: str, inputs: dict) -> None:
        """Set inputs of site

        :param site_id: id of site
        :param inputs: dictionary of point names and input values"""
        point_writes = []
        for name, value in inputs.items():
            point_writes.append({'name': name, 'value': value})
        self._request(f"sites/{site_id}/points/inputs", method="PUT", parameters={'points': point_writes})

    def get_outputs(self, site_id: str) -> dict:
        """Get outputs of site

        :param site_id: id of site
        :returns: dictionary of output names and values"""
        response = self._request(f"sites/{site_id}/points/outputs", method="GET")
        response_body = response.json()
        outputs = {}
        for point in response_body["data"]:
            outputs[point["name"]] = point["value"]

        return outputs

    @parallelize
    def get_sim_time(self, site_id: Union[SiteID, List[SiteID]]) -> datetime:
        """Get sim_time of site

        :param site_id: id of site or list of ids
        :returns: datetime of site
        """
        response = self._request(f"sites/{site_id}/time", method="GET")
        response_body = response.json()
        return datetime.strptime(response_body["time"], '%Y-%m-%d %H:%M:%S')

    def set_alias(self, alias: str, site_id: SiteID) -> None:
        """Set alias to point to a site_id

        :param site_id: id of site to point alias to
        :param alias: alias to use"""

        self._request(f"aliases/{alias}", method="PUT", parameters={"siteId": site_id})

    def get_alias(self, alias: str) -> SiteID:
        """Get site_id from alias

        :param alias: alias
        :returns: Id of site associated with alias"""

        response = self._request(f"aliases/{alias}", method="GET")
        response_body = response.json()
        return response_body
