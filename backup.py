from __future__ import print_function
import argparse
import requests
import json
import os
import sys
import time

parser = argparse.ArgumentParser()

SF_API_URL = "https://api.signalfx.com/"
SF_API_VERSION = "v2/"
SF_DIMENSION_API_PATH = "dimension/"
SF_DASHBOARDGROUP_API_PATH = "dashboardgroup/"

SF_DASHBOARD_API_PATH = "dashboard/"
SF_CHARTS_API_PATH = "chart/"

SF_BACKUP_PATH = "backups/"

if len(sys.argv) < 2:
    print("Please specify a config file path!", file=sys.stderr)
    sys.exit(1)

config_file = sys.argv[1]
config = {}
try:
    with open(config_file, 'r') as cfile:
        config = json.load(cfile)
except Exception, e:
    print("Failed to load config file: {error}".format(error=str(e)), file=sys.stderr)
    sys.exit(1)

SF_TOKEN = config.get('token', None)
if SF_TOKEN is None:
    print("Config must provide a `token`!", file=sys.stderr)
    sys.exit(1)

def backup_thing(thing, thing_path):

    if not os.path.exists(thing_path):
        try:
            os.mkdir(thing_path)
        except Exception, e:
            print(
                "Could not create directory: {error}".format(error=str(e)), file=sys.stderr
            )
            sys.exit(1)
        print("Created {path}".format(path=thing_path))
    target_file = thing_path + "/" + str(thing['lastUpdated']) + ".json"
    if os.path.exists(target_file):
        print("{id} is unchanged".format(id=thing['id']))
    else:
        try:
            with open(target_file, 'w') as out_file:
                json.dump(thing, out_file)
        except Exception, e:
            print(
                "Could not create backup file: {error}".format(error=str(e)),
                file=sys.stderr
            )
            sys.exit(1)

if not os.path.exists(SF_BACKUP_PATH):
    print(
        "Backup directory '{dir}' not found, create it?".format(dir=SF_BACKUP_PATH),
        file=sys.stderr
    )
    sys.exit(1)

get_headers = {'X-SF-TOKEN': SF_TOKEN}

get_url = SF_API_URL + SF_API_VERSION + SF_DASHBOARDGROUP_API_PATH + '?limit=50'
dashboard_get_url = SF_API_URL + SF_API_VERSION + SF_DASHBOARD_API_PATH
chart_get_url = SF_API_URL + SF_API_VERSION + SF_CHARTS_API_PATH

api_get = requests.get(get_url, headers=get_headers)
number_of_dashboard_groups = json.loads(api_get.text)['count']
print("Found {count} dashboard groups".format(count=str(number_of_dashboard_groups)))

# Retrieve all dashboard groups
all_dashboard_groups = []
for i in range(0, (number_of_dashboard_groups/50)+1):
    iter_get_url = get_url+'&offset='+str(i*50)
    api_get = requests.get(iter_get_url, headers=get_headers)
    all_dashboard_groups += json.loads(api_get.text)['results']
    print("Retrieved {count} dashboard groups".format(count=str(len(all_dashboard_groups))))

# Iterate through each dashboard group
for dg in all_dashboard_groups:
    dg_id = dg['id']
    dg_path = './' + SF_BACKUP_PATH + '/' + dg_id
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
