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

import json
import os
import requests
import time
import uuid
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
        # check if external_clock is bool, if so then convert to
        # downcase string
        v = kwargs["external_clock"]
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

    wait(url, site_id, "Running")


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
