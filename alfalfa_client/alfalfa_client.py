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

from collections import OrderedDict
from datetime import datetime
import json
from multiprocessing import Pool
from numbers import Number
import os
from typing import List, Union
from urllib.parse import urljoin
import uuid

import requests

from requests_toolbelt import MultipartEncoder


from alfalfa_client.lib import (
    convert,
    process_haystack_rows,
    status,
    wait
)


class AlfalfaClient:

    # The url argument is the address of the Alfalfa server
    # default should be http://localhost/api
    def __init__(self, host='http://localhost', version='v2'):
        self.host = host.lstrip('/')
        self.haystack_filter = self.host + '/api/read?filter='
        self.haystack_json_header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.readable_site_points = None  # Populated by get_read_site_points
        self.writable_site_points = None  # Populated by get_write_site_points
        self.readable_writable_site_points = None  # Populated by get_read_write_site_points

        self.host = host
        self.version = version

    @property
    def url(self):
        return urljoin(self.host, f"api/{self.version}/")

    def _request(self, endpoint, method="POST", parameters=None):
        response = requests.request(method=method, url=self.url + endpoint, json=parameters)
        response.raise_for_status()

        return response

    def status(self, siteref):
        return status(self.host, siteref)

    def wait(self, siteref, desired_status):
        return wait(self.host, siteref, desired_status)

    def submit_many(self, paths, wait_for_status=True):
        args = []
        for path in paths:
            args.append((path, False))
        p = Pool(10)
        run_ids = p.starmap(self.submit, args)
        p.close()
        p.join()

        if wait_for_status:
            for run_id in run_ids:
                wait(self.host, run_id, "READY")

        return run_ids

    def start_many(self, model_ids: List[str], *args, wait_for_status: bool = True, **kwargs):
        kwargs['wait_for_status'] = False
        for model_id in model_ids:
            self.start(model_id, *args, **kwargs)
        
        if wait_for_status:
            for model_id in model_ids:
                wait(self.host, model_id, "RUNNING")

    def stop_many(self, model_ids: List[str], *args, wait_for_status: bool = True, **kwargs):
        kwargs['wait_for_status'] = False
        for model_id in model_ids:
            self.stop(model_id, *args, **kwargs)
        
        if wait_for_status:
            for model_id in model_ids:
                wait(self.host, model_id, "COMPLETE")

    def submit(self, path: str, wait_for_status: bool = True):
        """Submit a model to alfalfa
        
        :param path: path to the model to upload
        :param wait_for_status: wait for model to be "READY" before returning
        
        :returns: id of created run
        :rtype: str"""

        filename = os.path.basename(path)
        uid = str(uuid.uuid1())

        key = 'uploads/' + uid + '/' + filename
        payload = {'name': key}

        # Get a template for the file upload form data
        # The server has an api to give this to us
        for i in range(3):
            response = requests.post(self.host + '/upload-url', json=payload)
            if response.status_code == 200:
                break
        if response.status_code != 200:
            print("Could not get upload-url")

        json = response.json()
        postURL = json['url']
        formData = OrderedDict(json['fields'])
        formData['file'] = ('filename', open(path, 'rb'))

        # Use the form data from the server to actually upload the file
        encoder = MultipartEncoder(fields=formData)
        for _ in range(3):
            response = requests.post(postURL, data=encoder, headers={'Content-Type': encoder.content_type})
            if response.status_code == 204:
                break
        if response.status_code != 204:
            print("Could not post file")

        # After the file has been uploaded, then tell BOPTEST to process the site
        # This is done not via the haystack api, but through a graphql api
        mutation = 'mutation { addSite(modelName: "%s", uploadID: "%s") }' % (filename, uid)
        for _ in range(3):
            response = requests.post(self.host + '/graphql', json={'query': mutation})
            if response.status_code == 200:
                break
        if response.status_code != 200:
            print("Could not addSite")

        if wait_for_status:
            wait(self.host, uid, "READY")

        return uid

    def start(self, model_id: str, start_datetime: Union[Number, datetime], end_datetime: Union[Number, datetime], timescale: int=5, external_clock:bool = False, realtime:bool = False, wait_for_status: bool=True):
        """Start one run from a model.

        :param model_id: id of model to start run from
        :param start_datetime: time to start the model from
        :param end_datetime: time to stop the model at (may not be honored for external_clock=True)
        :param timescale: multiple of real time to run model at (for external_clock=False)
        :param realtime: run model with timescale=1
        :param wait_for_status: wait for model to be "RUNNING" before returning
        """
        parameters = {}
        parameters['startDatetime'] = str(start_datetime)
        parameters['endDatetime'] = str(end_datetime)
        parameters['timescale'] = timescale
        parameters['externalClock'] = external_clock
        parameters['realtime'] = realtime

        response = self._request(f"models/{model_id}/start", parameters=parameters)

        assert response.status_code == 204, "Got wrong status_code from alfalfa"

        if wait_for_status:
            wait(self.host, model_id, "RUNNING")

    def stop(self, model_id: str, wait_for_status:bool=True):
        """Stop a run
        
        :param model_id: id of the model to stop
        :wait_for_status: waif for the model to be "COMPLETE" before returning
        """

        response = self._request(f"models/{model_id}/stop")
        
        assert response.status_code == 204, "Got wrong status_code from alfalfa"

        if wait_for_status:
            wait(self.host, model_id, "COMPLETE")

    def advance(self, site_ids):
        ids = ', '.join('"{0}"'.format(s) for s in site_ids)
        mutation = 'mutation { advance(siteRefs: [%s]) }' % (ids)
        payload = {'query': mutation}
        requests.post(self.host + '/graphql', json=payload)

    # TODO remove a site for model identified by id
    # def remove(self, id):
    #    mutation = 'mutation { removeSite(siteRef: "%s") }' % (id)

    #    payload = {'query': mutation}

    #    response = requests.post(self.url + '/graphql', json=payload )
    #    print('remove site API response: \n')
    # print(response.text)
    #

    # Set inputs for model identified by display name
    # The inputs argument should be a dictionary of
    # with the form
    # inputs = {
    #  input_name: value1,
    #  input_name2: value2
    # }
    def setInputs(self, site_id, inputs):
        for key, value in inputs.items():
            if value or (value == 0):
                mutation = 'mutation { writePoint(siteRef: "%s", pointName: "%s", value: %s, level: 1 ) }' % (
                    site_id, key, value)
            else:
                mutation = 'mutation { writePoint(siteRef: "%s", pointName: "%s", level: 1 ) }' % (site_id, key)
            requests.post(self.host + '/graphql', json={'query': mutation})

    # Return a dictionary of the output values
    # result = {
    # output_name1 : output_value1,
    # output_name2 : output_value2
    # }
    def outputs(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % (site_id)
        payload = {'query': query}
        response = requests.post(self.host + '/graphql', json=payload)

        j = response.json()
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = {}

        for point in points:
            tags = point["tags"]
            for tag in tags:
                if tag["key"] == "curVal":
                    result[convert(point["dis"])] = convert(tag["value"])
                    break

        return result

    # Return a list of all of the points in the
    # model which have the 'cur' tag.
    # result = [output_name1, output_name2, ...]
    # TODO this is semi-duplicate of the get_read_site_points method.
    def all_cur_points(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % (site_id)
        payload = {'query': query}
        response = requests.post(self.host + '/graphql', json=payload)

        j = response.json()
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = []

        for point in points:
            result.append(convert(point["dis"]))

        return result

    # Return a dictionary of the units for each
    # of the points.  Only points with units are returned.
    # result = {
    # output_name1 : unit1,
    # output_name2 : unit12
    # }
    def all_cur_points_with_units(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % (site_id)
        payload = {'query': query}
        response = requests.post(self.host + '/graphql', json=payload)

        j = response.json()
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = {}

        for point in points:
            tags = point["tags"]
            for tag in tags:
                if tag["key"] == "unit":
                    result[convert(point["dis"])] = convert(tag["value"])
                    break

        return result

    # Return the current time, as understood by the simulation
    # result = String(%Y-%m-%dT%H:%M:%S)
    def get_sim_time(self, site_id):
        query = 'query { viewer { runs(run_id: "%s") { sim_time } } }' % (site_id)
        payload = {'query': query}
        response = requests.post(self.host + '/graphql', json=payload)

        j = response.json()
        dt = j["data"]["viewer"]["runs"]["sim_time"]
        return dt

    # Return a list of all the points in the model which
    # have the 'writable' tag.
    # result = [output_name1, output_name2, ...]
    def all_writable_points(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(writable: true) { dis tags { key value } } } } }' % (
            site_id)
        payload = {'query': query}
        response = requests.post(self.host + '/graphql', json=payload)

        j = response.json()
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = []

        for point in points:
            result.append(convert(point["dis"]))

        return result

    # Return a list of all the points in the model which
    # have the 'cur' and 'writable' tag.
    # result = [output_name1, output_name2, ...]
    def all_cur_writable_points(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(writable: true, cur: true) { dis tags { key value } } } } }' % (
            site_id)
        payload = {'query': query}
        response = requests.post(self.host + '/graphql', json=payload)

        j = response.json()
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = []

        for point in points:
            result.append(convert(point["dis"]))

        return result

    # Return list of dictionary
    # point entities.  The entities will be filtered by
    # to correspond to the site_id passed, with the following:
    #   - point and cur and not equipRef
    def get_read_site_points(self, site_id):
        query = 'siteRef==@{} and point and cur and not equipRef'.format(site_id)
        response = requests.get(self.haystack_filter + query,
                                headers=self.haystack_json_header)
        try:
            temp = response.json()
            readable_site_points = process_haystack_rows(temp)
        except BaseException:
            readable_site_points = []
        return readable_site_points

    # Return list of dictionary point entities.
    # Entities will be filtered to correspond to the site_id
    # passed, with the following:
    #   - point and writable and not equipRef
    def get_write_site_points(self, site_id):
        query = 'siteRef==@{} and point and writable and not equipRef'.format(site_id)
        response = requests.get(self.haystack_filter + query,
                                headers=self.haystack_json_header)
        try:
            temp = response.json()
            writable_site_points = process_haystack_rows(temp)
        except BaseException:
            writable_site_points = []
        return writable_site_points

    # Return list of dictionary point entities.
    # Entities will be filtered to correspond to the site_id
    # passed, with the following:
    #   - point and writable and cur and not equipRef
    def get_read_write_site_points(self, site_id):
        query = 'siteRef==@{} and point and writable and cur and not equipRef'.format(site_id)
        response = requests.get(self.haystack_filter + query,
                                headers=self.haystack_json_header)
        try:
            temp = response.json()
            readable_writable_site_points = process_haystack_rows(temp)
        except BaseException:
            readable_writable_site_points = []
        return readable_writable_site_points

    def get_thermal_zones(self, site_id):
        query = 'siteRef==@{} and zone'.format(site_id)
        response = requests.get(self.haystack_filter + query,
                                headers=self.haystack_json_header)
        try:
            temp = response.json()
            readable_writable_site_points = process_haystack_rows(temp)
        except BaseException:
            readable_writable_site_points = []
        return readable_writable_site_points

    # Return a dictionary of the current input values
    # result = {
    # input_name1 : input_value1,
    # input_name2 : input_value2
    # }
    def inputs(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(writable: true) { dis tags { key value } } } } }' % (
            site_id)
        payload = {'query': query}
        response = requests.post(self.host + '/graphql', json=payload)

        j = response.json()
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = {}

        for point in points:
            tags = point["tags"]
            for tag in tags:
                if tag["key"] == "writeStatus":
                    result[convert(point["dis"])] = convert(tag["value"])
                    break

        return result
