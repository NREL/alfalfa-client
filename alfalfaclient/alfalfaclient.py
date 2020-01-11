import uuid
import requests
import json
import os
import time
from requests_toolbelt import MultipartEncoder
from multiprocessing import Pool
from collections import OrderedDict


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
        response = requests.post(self.url + '/graphql', json=payload)

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
    ##    mutation = 'mutation { removeSite(siteRef: "%s") }' % (id)

    ##    payload = {'query': mutation}

    ##    response = requests.post(self.url + '/graphql', json=payload )
    ##    print('remove site API response: \n')
    # print(response.text)
    ##

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
            response = requests.post(self.url + '/graphql', json={'query': mutation})

    # Return a dictionary of the output values
    # result = {
    # output_name1 : output_value1,
    # output_name2 : output_value2
    # }
    def outputs(self, site_id):
        query = 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % (site_id)
        payload = {'query': query}
        response = requests.post(self.url + '/graphql', json=payload)

        j = json.loads(response.text)
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

        j = json.loads(response.text)
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

        j = json.loads(response.text)
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

        j = json.loads(response.text)
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
        except:
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
        except:
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
        except:
            readable_writable_site_points = []
        return readable_writable_site_points

    def get_thermal_zones(self, site_id):
        query = 'siteRef==@{} and zone'.format(site_id)
        response = requests.get(self.haystack_filter + query,
                                headers=self.haystack_json_header)
        try:
            temp = response.json()
            readable_writable_site_points = process_haystack_rows(temp)
        except:
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
                    result[convert(point["dis"])] = convert(tag["value"])
                    break

        return result


# remove any hastack type info from value and convert numeric strings
# to python float. ie s: maps to python string n: maps to python float,
# other values are simply returned unchanged, thus retaining any haystack type prefix
def convert(value):
    if value[0:2] == 's:':
        return value[2:]
    elif value[0:2] == 'n:':
        return float(value[2:])
    else:
        return value


# Remove haystack type info (s: and n: ONLY) from a list of strings.
# Return list
def convert_all(values):
    v2 = []
    for v in values:
        v2.append(convert(v))
    return v2


def status(url, siteref):
    status = ''

    query = '{ viewer{ sites(siteRef: "%s") { simStatus } } }' % siteref
    for i in range(3):
        response = requests.post(url + '/graphql', json={'query': query})
        if response.status_code == 200:
            break
    if response.status_code != 200:
        print("Could not get status")

    j = json.loads(response.text)
    sites = j["data"]["viewer"]["sites"]
    if sites:
        status = sites[0]["simStatus"]

    return status


def wait(url, siteref, desired_status):
    sites = []

    attempts = 0
    while attempts < 6000:
        attempts = attempts + 1
        current_status = status(url, siteref)

        if desired_status:
            if attempts % 2 == 0:
                print("Desired status: {}\t\tCurrent status: {}".format(desired_status, current_status))
            if current_status == desired_status:
                break
        elif current_status:
            break
        time.sleep(2)


def submit_one(args):
    url = args["url"]
    path = args["path"]

    filename = os.path.basename(path)
    uid = str(uuid.uuid1())

    key = 'uploads/' + uid + '/' + filename
    payload = {'name': key}

    # Get a template for the file upload form data
    # The server has an api to give this to us
    for i in range(3):
        response = requests.post(url + '/upload-url', json=payload)
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
    mutation = 'mutation { addSite(osmName: "%s", uploadID: "%s") }' % (filename, uid)
    for _ in range(3):
        response = requests.post(url + '/graphql', json={'query': mutation})
        if response.status_code == 200:
            break
    if response.status_code != 200:
        print("Could not addSite")

    wait(url, uid, "Stopped")

    return uid


def start_one(args):
    url = args["url"]
    site_id = args["site_id"]
    kwargs = args["kwargs"]

    mutation = 'mutation { runSite(siteRef: "%s"' % site_id

    if "timescale" in kwargs:
        mutation = mutation + ', timescale: %s' % kwargs["timescale"]
    if "start_datetime" in kwargs:
        mutation = mutation + ', startDatetime: "%s"' % kwargs["start_datetime"]
    if "end_datetime" in kwargs:
        mutation = mutation + ', endDatetime: "%s"' % kwargs["end_datetime"]
    if "realtime" in kwargs:
        mutation = mutation + ', realtime: %s' % kwargs["realtime"]
    if "external_clock" in kwargs:
        mutation = mutation + ', externalClock: %s' % kwargs["external_clock"]

    mutation = mutation + ') }'

    for _ in range(3):
        response = requests.post(url + '/graphql', json={'query': mutation})
        if response.status_code == 200:
            break
        else:
            print("Start one status code: {}".format(response.status_code))

    wait(url, site_id, "Running")


def stop_one(args):
    url = args["url"]
    site_id = args["site_id"]

    mutation = 'mutation { stopSite(siteRef: "%s") }' % (site_id)
    payload = {'query': mutation}
    response = requests.post(url + '/graphql', json=payload)

    wait(url, site_id, "Stopped")


# Grab only the 'rows' out of a Haystack JSON response.
# Return a list of dictionary entities.
# If no 'rows' exist, return empty list
def process_haystack_rows(haystack_json_response):
    return haystack_json_response.get('rows', [])
