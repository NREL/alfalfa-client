import json
from multiprocessing import Pool

import requests
import hszinc

from alfalfa_client.lib import process_haystack_rows, start_one, status, stop_one, submit_one, wait


class AlfalfaClient:

    # The url argument is the address of the Alfalfa server
    # default should be http://localhost/api
    def __init__(self, url='http://localhost'):
        self.url = url
        self.api_read_filter = self.url + '/api/read?filter='
        self.api_point_write = self.url + '/api/pointWrite'
        self.haystack_json_header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.readable_site_points = None  # Populated by get_read_site_points
        self.writable_site_points = None  # Populated by get_write_site_points
        self.readable_writable_site_points = None  # Populated by get_read_write_site_points

    @staticmethod
    def construct_point_write_grid(point_id: hszinc.Ref, value: hszinc.Quantity,
                                   level: hszinc.Quantity = hszinc.Quantity(2),
                                   who: str = 'alfalfa-client'):
        cols = [
            ('id', {}),
            ('value', {}),
            ('level', {}),
            ('who', {}),
        ]
        grid = hszinc.Grid(version=hszinc.VER_2_0, columns=cols)
        grid.insert(0, {
            'id': point_id,
            'value': value,
            'level': level,
            'who': who
        })
        return grid

    @staticmethod
    def get_point_given_point_dis(grid: hszinc.Grid, dis, site_id):
        """

        :param grid [hszinc.Grid] grid to search
        :param dis: [str] display name of string to match
        :param site_id:
        :return: [dict] a row from an hszinc.Grid
        """
        rows = []
        for row in grid:
            if 'dis' in row:
                if dis == row['dis']:
                    rows.append(row)
        if len(rows) == 1:
            return rows[0]
        elif len(rows) > 1:
            print(f"Returning first row - multiple matches for dis: {dis} on site: {site_id}")
            return rows[0]
        else:
            print(f"No match for dis: {dis} on site: {site_id}")
            return {}

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

    def remove_site(self, site_id):
        """
        Remove a site from the host
        :param site_id: site to remove_site
        :return: [requests.Response]
        """
        mutation = 'mutation { removeSite(siteRef: "%s") }' % site_id

        payload = {'query': mutation}

        return requests.post(self.url + '/graphql', json=payload)

    def point_write(self, point_id: (str, hszinc.Ref), value: (int, float, hszinc.Quantity),
                    level: (int, float, hszinc.Quantity) = 2, who: str = 'alfalfa-client'):
        """
        Write a value to the point at the specified level.  All parameters get
        'converted' to Haystack JSON types before being written.
        See https://project-haystack.org/doc/Ops#pointWrite

        :param point_id:
        :param value:
        :param level:
        :param who:
        :return: [requests.Response] the server response
        """
        new_id = point_id if isinstance(point_id, hszinc.Ref) else hszinc.Ref(point_id)
        new_value = value if isinstance(value, hszinc.Quantity) else hszinc.Quantity(value)
        new_level = level if isinstance(level, hszinc.Quantity) else hszinc.Quantity(level)

        grid = self.construct_point_write_grid(new_id,
                                               new_value,
                                               new_level,
                                               who)
        response = requests.post(self.api_point_write,
                                 data=hszinc.dump(grid, hszinc.MODE_JSON),
                                 headers=self.haystack_json_header)
        return response

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
        query = 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % (
            site_id)
        payload = {'query': query}
        response = requests.post(self.url + '/graphql', json=payload)

        j = json.loads(response.text)
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = {}

        for point in points:
            tags = point["tags"]
            for tag in tags:
                if tag["key"] == "curVal":
                    # Remove Haystack typing info
                    dis = hszinc.parse_scalar(point['dis'], mode=hszinc.MODE_JSON)
                    val = hszinc.parse_scalar(point['value'], mode=hszinc.MODE_JSON)
                    result[dis] = val
                    break

        return result

    # Return a list of all of the points in the
    # model which have the 'cur' tag.
    # result = [output_name1, output_name2, ...]
    # TODO this is semi-duplicate of the get_read_site_points method.
    def all_cur_points(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % (
            site_id)
        payload = {'query': query}
        response = requests.post(self.url + '/graphql', json=payload)

        j = json.loads(response.text)
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = []

        for point in points:
            # Remove Haystack typing info
            dis = hszinc.parse_scalar(point['dis'], mode=hszinc.MODE_JSON)
            result.append(dis)

        return result

    # Return a dictionary of the units for each
    # of the points.  Only points with units are returned.
    # result = {
    # output_name1 : unit1,
    # output_name2 : unit12
    # }
    def all_cur_points_with_units(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % (
            site_id)
        payload = {'query': query}
        response = requests.post(self.url + '/graphql', json=payload)

        j = json.loads(response.text)
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = {}

        for point in points:
            tags = point["tags"]
            for tag in tags:
                if tag["key"] == "unit":
                    # Remove Haystack typing info
                    dis = hszinc.parse_scalar(point['dis'], mode=hszinc.MODE_JSON)
                    val = hszinc.parse_scalar(point['value'], mode=hszinc.MODE_JSON)
                    result[dis] = val
                    break

        return result

    # Return the current time, as understood by the simulation
    # result = String(%Y-%m-%dT%H:%M:%S)
    def get_sim_time(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { datetime } } }' % (site_id)
        payload = {'query': query}
        response = requests.post(self.url + '/graphql', json=payload)

        j = json.loads(response.text)
        dt = j["data"]["viewer"]["sites"][0]["datetime"]
        return dt

    # Return a list of all the points in the model which
    # have the 'writable' tag.
    # result = [output_name1, output_name2, ...]
    def all_writable_points(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(writable: true) { dis tags { key value } } } } }' % (
            site_id)
        payload = {'query': query}
        response = requests.post(self.url + '/graphql', json=payload)

        j = json.loads(response.text)
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = []

        for point in points:
            # Remove Haystack typing info
            dis = hszinc.parse_scalar(point['dis'], mode=hszinc.MODE_JSON)
            result.append(dis)

        return result

    # Return a list of all the points in the model which
    # have the 'cur' and 'writable' tag.
    # result = [output_name1, output_name2, ...]
    def all_cur_writable_points(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(writable: true, cur: true) { dis tags { key value } } } } }' % (
            site_id)
        payload = {'query': query}
        response = requests.post(self.url + '/graphql', json=payload)

        j = json.loads(response.text)
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = []

        for point in points:
            # Remove Haystack typing info
            dis = hszinc.parse_scalar(point['dis'], mode=hszinc.MODE_JSON)
            result.append(dis)

        return result

    # Return list of dictionary
    # point entities.  The entities will be filtered by
    # to correspond to the site_id passed, with the following:
    #   - point and cur and not equipRef
    def get_read_site_points(self, site_id):
        query = 'siteRef==@{} and point and cur and not equipRef'.format(site_id)
        response = requests.get(self.api_read_filter + query,
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
        response = requests.get(self.api_read_filter + query,
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
        response = requests.get(self.api_read_filter + query,
                                headers=self.haystack_json_header)
        try:
            temp = response.json()
            readable_writable_site_points = process_haystack_rows(temp)
        except BaseException:
            readable_writable_site_points = []
        return readable_writable_site_points

    def get_thermal_zones(self, site_id):
        query = 'siteRef==@{} and zone'.format(site_id)
        response = requests.get(self.api_read_filter + query,
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

        j = json.loads(response.text)
        points = j["data"]["viewer"]["sites"][0]["points"]
        result = {}

        for point in points:
            tags = point["tags"]
            for tag in tags:
                if tag["key"] == "writeStatus":
                    # Remove Haystack typing info
                    dis = hszinc.parse_scalar(point['dis'], mode=hszinc.MODE_JSON)
                    val = hszinc.parse_scalar(point['value'], mode=hszinc.MODE_JSON)
                    result[dis] = val
                    break

        return result

    def query_points(self, site_id):
        """
        Get all points on the site
        :param site_id: [str]
        :return: [hszinc.Grid] if successful
        """
        id = hszinc.Ref(site_id)

        # Haystack query filter requires ZINC formatted string
        # hszinc.Ref.__str__ looks like '@abc-123'
        query = f"siteRef=={id} and point"
        response = requests.get(self.api_read_filter + query,
                                headers=self.haystack_json_header)
        if response.status_code == 200:
            return hszinc.parse(response.content, mode=hszinc.MODE_JSON)
        else:
            raise requests.exceptions.ConnectionError
