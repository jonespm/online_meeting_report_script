# Script to get all sites where Zoom is visible and retrieve the meetings to generate a report

import json
import re
import os

import requests
import logging

from canvasapi import Canvas
from canvasapi.exceptions import ResourceDoesNotExist
from collections import OrderedDict
from bs4 import BeautifulSoup as bs
from urllib.parse import urljoin

# read configurations
try:
    with open(os.path.join('config', 'env.json')) as env_file:
        ENV = json.loads(env_file.read())
except FileNotFoundError:
    logger.error(
        'Configuration file could not be found; please add env.json to the config directory.')

LOG_LEVEL = ENV.get('LOG_LEVEL', 'DEBUG')
logging.basicConfig(level=LOG_LEVEL)

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
import http.client as http_client
if LOG_LEVEL == logging.DEBUG:
    http_client.HTTPConnection.debuglevel = 1

# You must initialize logging, otherwise you'll not see debug output.
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(LOG_LEVEL)
requests_log.propagate = True

#sites_to_update = [109190]

CANVAS = Canvas(ENV.get("CANVAS_API_URL"), ENV.get("CANVAS_API_KEY"))

account = CANVAS.get_account(ENV.get("CANVAS_ACCOUNT" ,1))

courses = account.get_courses(enrollment_term_id=ENV.get("CANVAS_TERM", 1))
for course in courses:
    logger.info("Fetching course %s", course)
    # Get tabs and look for zoom
    tabs = course.get_tabs()
    for tab in tabs:
        # Hidden only included if true
        if (tab.label=="Zoom" and not hasattr(tab, "hidden")):
            logger.info("Found a course with zoom as %s", tab.id)
            r = CANVAS._Canvas__requester.request("GET", _url=tab.url)
            external_url = r.json().get("url")
            r = requests.get(external_url)
            # Parse out the form from the response
            soup = bs(r.text, 'html.parser')
            # Get the form and parse out all of the inputs
            form = soup.find('form')
            fields = form.findAll('input')
            formdata = dict((field.get('name'), field.get('value')) for field in fields)

            # Get the URL to post back to
            posturl = form.get('action')

            # Start up the zoom session
            zoom_s = requests.Session()
            # Initiate the LTI launch to Zoom in a session
            r = zoom_s.post(url=posturl, data=formdata)

            # Get the XSRF Token
            pattern = re.search('"X-XSRF-TOKEN".* value:"(.*)"', r.text)
            if pattern:
                zoom_s.headers.update({
                    'X-XSRF-TOKEN': pattern.group(1)
                })
            # Get tab 1 (Previous Meetings)
                data = {'page': 1,
                        'total': 0,
                        'storage_timezone': 'America/Montreal',
                        'client_timezone' : 'America/Detroit'
                }
                r = zoom_s.get("https://applications.zoom.us/api/v1/lti/rich/meeting/history/COURSE/all", params=data)
                print (json.loads(r.text))
                # Currently for testing quit on the first match
                logger.warn("FOR DEBUG QUIT ON FIRST MATCH")
                quit()