import json
import os
import time
import uuid
from collections import OrderedDict
from datetime import datetime

import requests
from requests_toolbelt import MultipartEncoder


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
    pass

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


def start_one(args: dict):
    url, site_id, mutation = create_run_site_mutation(args)

    successful = False
    attempts = 3
    for _ in range(attempts):
        response = requests.post(url + '/graphql', json={'query': mutation})
        if response.status_code == 200:
            successful = True
            break
        else:
            print("Start one status code: {}".format(response.status_code))
            print(f"start_one error: {response.content}")

    if not successful:
        raise requests.exceptions.ConnectionError(
            f"Unable to connect to Alfalfa server. Attempts: {attempts}.  Last status code: {response.status_code}.  Content: {response.content}")
    wait(url, site_id, "Running")


def create_run_site_mutation(args: dict):
    """
    Create a mutation string necessary for the GraphQL runSite mutation
    :param args: arguments for mutation
    :return: [Tuple(str, str, str)] url, site_id, mutation
    """
    url = args["url"]
    site_id = args["site_id"]
    kwargs = args["kwargs"]
    mutation = 'mutation { runSite(siteRef: "%s"' % site_id

    if "timescale" in kwargs:
        val = kwargs['timescale']
        if not isinstance(val, (int, float)):
            raise TypeError(f"Expected 'timescale' of type: (int, float), got {type(val)}")
        mutation = mutation + f", timescale: {val}".lower()
    if "start_datetime" in kwargs:
        val = kwargs['start_datetime']
        if check_datetime(val):
            mutation = mutation + ', startDatetime: "%s"' % val
    if "end_datetime" in kwargs:
        val = kwargs['end_datetime']
        if check_datetime(val):
            mutation = mutation + ', endDatetime: "%s"' % val
    if "realtime" in kwargs:
        val = kwargs['realtime']
        if not isinstance(val, bool):
            raise TypeError(f"Expected 'realtime' of type: bool, got {type(val)}")

        # This changes from False to false, a JSON bool type
        mutation = mutation + f", realtime: {val}".lower()
    if "external_clock" in kwargs:
        val = kwargs['external_clock']
        if not isinstance(val, bool):
            raise TypeError(f"Expected 'external_clock' of type: bool, got {type(val)}")

        # This changes from False to false, a JSON bool type
        val = f"{val}".lower()
        mutation = mutation + f", externalClock: {val}"

    mutation = mutation + ') }'
    return url, site_id, mutation


def check_datetime(dt: [str, datetime]):
    """
    Check the input is an ISO8601 formatted string or a datetime object
    :param dt:
    :return: [True] if is valid, else raises TypeError
    """
    if isinstance(dt, datetime):
        return True
    elif isinstance(dt, str):
        # This will raise a ValueError if incorrect format
        _ = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
        return True
    else:
        raise TypeError(f"datetime: {dt} must be a datetime object or an ISO8601 formatted string")


def stop_one(args):
    url = args["url"]
    site_id = args["site_id"]

    mutation = 'mutation { stopSite(siteRef: "%s") }' % (site_id)
    payload = {'query': mutation}
    requests.post(url + '/graphql', json=payload)

    wait(url, site_id, "Stopped")


# Grab only the 'rows' out of a Haystack JSON response.
# Return a list of dictionary entities.
# If no 'rows' exist, return empty list
def process_haystack_rows(haystack_json_response):
    return haystack_json_response.get('rows', [])
