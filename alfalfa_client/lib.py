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

import os
import time
import uuid
from collections import OrderedDict

import requests
from requests_toolbelt import MultipartEncoder


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


def status(url, run_id):
    status = ''

    query = '{ viewer{ runs(run_id: "%s") { status } } }' % run_id
    for i in range(3):
        response = requests.post(url + '/graphql', json={'query': query})
        if response.status_code == 200:
            break
    if response.status_code != 200:
        print("Could not get status")

    j = response.json()
    runs = j["data"]["viewer"]["runs"]
    if runs:
        status = runs["status"]

    return status


def get_error_log(url, run_id):
    error_log = ''

    query = '{ viewer{ runs(run_id: "%s") { error_log } } }' % run_id
    for i in range(3):
        response = requests.post(url + '/graphql', json={'query': query})
        if response.status_code == 200:
            break
    if response.status_code != 200:
        print("Could not get error log")

    j = response.json()
    runs = j["data"]["viewer"]["runs"]
    if runs:
        error_log = runs["error_log"]

    return error_log


def wait(url, run_id, desired_status):
    pass

    attempts = 0
    while attempts < 6000:
        attempts = attempts + 1
        current_status = status(url, run_id)

        if current_status == "ERROR":
            error_log = get_error_log(url, run_id)
            raise AlfalfaException(error_log)

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
    mutation = 'mutation { addSite(modelName: "%s", uploadID: "%s") }' % (filename, uid)
    run_id = None
    for _ in range(3):
        response = requests.post(url + '/graphql', json={'query': mutation})
        if response.status_code == 200:
            run_id = response.json()['data']['addSite']
            break
    if response.status_code != 200:
        print("Could not addSite")

    wait(url, run_id, "READY")

    return run_id


def start_one(args):
    url = args["url"]
    site_id = args["site_id"]
    kwargs = args["kwargs"]

    mutation = 'mutation { runSite(siteRef: "%s"' % site_id

    mutation = mutation + ', timescale: %s' % kwargs.get("timescale", 5)

    if "start_datetime" in kwargs:
        mutation = mutation + ', startDatetime: "%s"' % kwargs["start_datetime"]
    if "end_datetime" in kwargs:
        mutation = mutation + ', endDatetime: "%s"' % kwargs["end_datetime"]

    mutation = mutation + ', realtime: %s' % kwargs.get("realtime", "false")

    # check if external_clock is bool, if so then convert to
    # downcase string
    v = kwargs.get("external_clock", "false")
    if isinstance(v, bool):
        v = 'true' if v else 'false'

    mutation = mutation + ', externalClock: %s' % v.lower()

    mutation = mutation + ') }'

    for _ in range(3):
        response = requests.post(url + '/graphql', json={'query': mutation})
        if response.status_code == 200:
            break
        else:
            print("Start one status code: {}".format(response.status_code))
            print(f"start_one error: {response.content}")

    wait(url, site_id, "RUNNING")


def stop_one(args):
    url = args["url"]
    site_id = args["site_id"]

    mutation = 'mutation { stopSite(siteRef: "%s") }' % (site_id)
    payload = {'query': mutation}
    requests.post(url + '/graphql', json=payload)

    wait(url, site_id, "COMPLETE")


# Grab only the 'rows' out of a Haystack JSON response.
# Return a list of dictionary entities.
# If no 'rows' exist, return empty list
def process_haystack_rows(haystack_json_response):
    return haystack_json_response.get('rows', [])


class AlfalfaException(Exception):
    """Wrapper for exceptions which come from alfalfa"""
