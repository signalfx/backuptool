#!/usr/bin/env python
import argparse
import json
import logging
import os
import requests
import sys
import time

parser = argparse.ArgumentParser()

DEFAULT_API_URL='https://api.signalfx.com'
DEFAULT_API_VERSION = 2

parser.add_argument(
    '--api_url',
    type=str,
    default=DEFAULT_API_URL,
    help='Full URL to use for the API (default: {url})'.format(
        url=DEFAULT_API_URL
    )
)
parser.add_argument(
    '--api_version',
    type=int,
    default=DEFAULT_API_VERSION,
    help='API version (default: {version})'.format(
        version=DEFAULT_API_VERSION
    )
)
parser.add_argument(
    '--config',
    type=str,
    required=True,
    help='Path to configuration file'
)
parser.add_argument(
    '--destination',
    type=str,
    required=True,
    help='Directory to which backup files will be written'
)
parser.add_argument(
    '--verbose',
    help='Be verbose about what we doing',
    action='store_true'
)

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)

SF_DIMENSION_API_PATH = "dimension/"
SF_DASHBOARDGROUP_API_PATH = "dashboardgroup/"

SF_DASHBOARD_API_PATH = "dashboard/"
SF_CHARTS_API_PATH = "chart/"

if len(sys.argv) < 2:
    logging.error("Please specify a config file path!")
    sys.exit(1)

config = {}
try:
    with open(os.path.expanduser(args.config), 'r') as cfile:
        config = json.load(cfile)
except Exception, e:
    logging.error("Failed to load config file: %s", str(e))
    sys.exit(1)

SF_TOKEN = config.get('token', None)
if SF_TOKEN is None:
    logging.error("Config must provide a `token`!")
    sys.exit(1)

def backup_thing(thing, thing_path):

    if not os.path.exists(thing_path):
        try:
            os.mkdir(thing_path)
        except Exception, e:
            logging.error("Could not create directory: %s", str(e))
            sys.exit(1)
        logging.debug("Created %s", thing_path)
    target_file = thing_path + "/" + str(thing['lastUpdated']) + ".json"
    if os.path.exists(target_file):
        logging.debug("%s is unchanged", thing['id'])
    else:
        try:
            with open(target_file, 'w') as out_file:
                json.dump(thing, out_file)
        except Exception, e:
            logging.error(
                "Could not create backup file: %s", str(e)
            )
            sys.exit(1)

if not os.path.exists(args.destination):
    logging.err(
        "Backup directory '%s' not found, create it?", args.destination
    )
    sys.exit(1)

get_headers = {'X-SF-TOKEN': SF_TOKEN}

base_url = "{url}/v{version}/".format(
    url=args.api_url,
    version=str(args.api_version)
)

get_url = base_url + SF_DASHBOARDGROUP_API_PATH + '?limit=50'
dashboard_get_url = base_url + SF_DASHBOARD_API_PATH
chart_get_url = base_url + SF_CHARTS_API_PATH

api_get = requests.get(get_url, headers=get_headers)
number_of_dashboard_groups = json.loads(api_get.text)['count']
logging.debug("Found %d dashboard groups", number_of_dashboard_groups)

# Retrieve all dashboard groups
all_dashboard_groups = []
for i in range(0, (number_of_dashboard_groups/50)+1):
    iter_get_url = get_url+'&offset='+str(i*50)
    api_get = requests.get(iter_get_url, headers=get_headers)
    all_dashboard_groups += json.loads(api_get.text)['results']
    logging.debug("Retrieved %d dashboard groups", len(all_dashboard_groups))

# Iterate through each dashboard group
for dg in all_dashboard_groups:
    dg_id = dg['id']
    dg_path = args.destination + '/' + dg_id
    # And write it out
    backup_thing(dg, dg_path)
    # Iterate through each dashboard in the group
    for dash_id in dg['dashboards']:
        # Fetch the full dashboard
        dash_resp = requests.get(dashboard_get_url + dash_id, headers=get_headers)
        dash = json.loads(dash_resp.text)
        dash_path = dg_path + '/' + dash_id + '/'
        # And back that up
        backup_thing(dash, dash_path)
        # Iterate through each chart in the dashboard
        for chart_slot in dash['charts']:
            chart_id = chart_slot['chartId']
            # Fetch the full chart
            chart_resp = requests.get(chart_get_url + chart_id, headers=get_headers)
            chart = json.loads(chart_resp.text)
            chart_path = dash_path + '/' + chart_id + '/'
            # And back that up!
            backup_thing(chart, chart_path)
