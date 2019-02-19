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
    '--dashboards',
    help='Back up dashboards',
    action='store_true'
)
parser.add_argument(
    '--destination',
    type=str,
    required=True,
    help='Directory to which backup files will be written'
)
parser.add_argument(
    '--detectors',
    help='Back up detectors',
    action='store_true'
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
SF_DETECTOR_API_PATH = "detector/"

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

def backup_thing(thing, thing_path, thing_id, thing_updated):
    if not os.path.exists(thing_path):
        try:
            os.mkdir(thing_path)
        except Exception, e:
            logging.error("Could not create directory: %s", str(e))
            sys.exit(1)
        logging.debug("Created %s", thing_path)
    target_file = thing_path + "/" + thing_updated + ".json"
    if os.path.exists(target_file):
        logging.debug("%s is unchanged", thing_id)
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
    logging.error(
        "Backup directory '%s' not found, create it?", args.destination
    )
    sys.exit(1)

get_headers = {'X-SF-TOKEN': SF_TOKEN}

base_url = "{url}/v{version}/".format(
    url=args.api_url,
    version=str(args.api_version)
)

dashgroup_get_url = base_url + SF_DASHBOARDGROUP_API_PATH + '?limit=50'
dashboard_get_url = base_url + SF_DASHBOARD_API_PATH
chart_get_url = base_url + SF_CHARTS_API_PATH
detector_list_get_url = base_url + SF_DETECTOR_API_PATH + '?limit=50'
detector_get_url = base_url + SF_DETECTOR_API_PATH

def task_backup_detectors():
    api_get = requests.get(detector_list_get_url, headers=get_headers)
    number_of_detectors = json.loads(api_get.text)['count']
    print(api_get.text)
    logging.debug("Found %d detectors", number_of_detectors)

    all_detectors = []
    for i in range(0, (number_of_detectors/50)+1):
        iter_get_url = detector_list_get_url+'&offset='+str(i*50)
        api_get = requests.get(iter_get_url, headers=get_headers)
        print(api_get.text)

        if "/v2/" in detector_get_url:
            all_detectors += json.loads(api_get.text)['results']
        else:
            all_detectors += json.loads(api_get.text)['rs']

        logging.debug("Retrieved %d detectors", len(all_detectors))

        for det_id in all_detectors:
            det_path = args.destination + '/' + det_id
            det_resp = requests.get(detector_get_url + det_id, headers=get_headers)
            det = json.loads(det_resp.text)
            if '/v2/' in detector_get_url:
                # for v1 we need to take some fields to help our backup code
                # work
                pass
            else:
                backup_thing(det, det_path, str(det['sf_id']), str(det['sf_updatedOnMs']))

def task_backup_dashboards():
    api_get = requests.get(dashgroup_get_url, headers=get_headers)
    number_of_dashboard_groups = json.loads(api_get.text)['count']
    logging.debug("Found %d dashboard groups", number_of_dashboard_groups)

    # Retrieve all dashboard groups
    all_dashboard_groups = []
    for i in range(0, (number_of_dashboard_groups/50)+1):
        iter_get_url = dashgroup_get_url+'&offset='+str(i*50)
        api_get = requests.get(iter_get_url, headers=get_headers)
        all_dashboard_groups += json.loads(api_get.text)['results']
        logging.debug("Retrieved %d dashboard groups", len(all_dashboard_groups))

    # Iterate through each dashboard group
    for dg in all_dashboard_groups:
        dg_id = dg['id']
        dg_path = args.destination + '/' + dg_id
        # And write it out
        backup_thing(dg, dg_path, str(dg['id']), str(dg['lastUpdated']))
        # Iterate through each dashboard in the group
        for dash_id in dg['dashboards']:
            # Fetch the full dashboard
            dash_resp = requests.get(dashboard_get_url + dash_id, headers=get_headers)
            dash = json.loads(dash_resp.text)
            dash_path = dg_path + '/' + dash_id + '/'
            # And back that up
            backup_thing(dash, dash_path, str(dash['id']), str(dash['lastUpdated']))
            # Iterate through each chart in the dashboard
            for chart_slot in dash['charts']:
                chart_id = chart_slot['chartId']
                # Fetch the full chart
                chart_resp = requests.get(chart_get_url + chart_id, headers=get_headers)
                chart = json.loads(chart_resp.text)
                chart_path = dash_path + '/' + chart_id + '/'
                # And back that up!
                backup_thing(chart, chart_path, str(chart['id']), str(chart['lastUpdated']))

if __name__ == "__main__":
    if not args.dashboards and not args.detectors:
        logging.error("You probably want to choose one or both of --dashboards or --detectors!")
        parser.print_help()
        sys.exit(1)

    if args.dashboards:
        task_backup_dashboards()
    if args.detectors:
        task_backup_detectors()
