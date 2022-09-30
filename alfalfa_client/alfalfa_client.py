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

from multiprocessing import Pool

import requests

from alfalfa_client.lib import (
    convert,
    process_haystack_rows,
    start_one,
    status,
    stop_one,
    submit_one,
    wait
)


class AlfalfaClient:

    # The url argument is the address of the Alfalfa server
    # default should be http://localhost/api
    def __init__(self, url='http://localhost'):
        self.url = url
        self.haystack_filter = self.url + '/api/read?filter='
        self.haystack_json_header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.readable_site_points = None  # Populated by get_read_site_points
        self.writable_site_points = None  # Populated by get_write_site_points
        self.readable_writable_site_points = None  # Populated by get_read_write_site_points

    def status(self, siteref):
        return status(self.url, siteref)

    def wait(self, siteref, desired_status):
        return wait(self.url, siteref, desired_status)

    def submit(self, path):
        args = {"url": self.url, "path": path}
        return submit_one(args)

    def submit_many(self, paths):
        args = []
        for path in paths:
            args.append({"url": self.url, "path": path})
        p = Pool(10)
        result = p.map(submit_one, args)
        p.close()
        p.join()
        return result

    def start(self, site_id, **kwargs):
        args = {"url": self.url, "site_id": site_id, "kwargs": kwargs}
        return start_one(args)

    # Start a simulation for model identified by id. The id should corrsespond to
    # a return value from the submit method
    # kwargs are timescale, start_datetime, end_datetime, realtime, external_clock
    def start_many(self, site_ids, **kwargs):
        args = []
        for site_id in site_ids:
            args.append({"url": self.url, "site_id": site_id, "kwargs": kwargs})
        p = Pool(10)
        result = p.map(start_one, args)
        p.close()
        p.join()
        return result

    def advance(self, site_ids):
        ids = ', '.join('"{0}"'.format(s) for s in site_ids)
        mutation = 'mutation { advance(siteRefs: [%s]) }' % (ids)
        payload = {'query': mutation}
        requests.post(self.url + '/graphql', json=payload)

    def stop(self, site_id):
        args = {"url": self.url, "site_id": site_id}
        return stop_one(args)

    # Stop a simulation for model identified by id
    def stop_many(self, site_ids):
        args = []
        for site_id in site_ids:
            args.append({"url": self.url, "site_id": site_id})
        p = Pool(10)
        result = p.map(stop_one, args)
        p.close()
        p.join()
        return result

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
            requests.post(self.url + '/graphql', json={'query': mutation})

    # Return a dictionary of the output values
    # result = {
    # output_name1 : output_value1,
    # output_name2 : output_value2
    # }
    def outputs(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % (site_id)
        payload = {'query': query}
        response = requests.post(self.url + '/graphql', json=payload)

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
        response = requests.post(self.url + '/graphql', json=payload)

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
        response = requests.post(self.url + '/graphql', json=payload)

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
        response = requests.post(self.url + '/graphql', json=payload)

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
        response = requests.post(self.url + '/graphql', json=payload)

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
        response = requests.post(self.url + '/graphql', json=payload)

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
        response = requests.post(self.url + '/graphql', json=payload)

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
