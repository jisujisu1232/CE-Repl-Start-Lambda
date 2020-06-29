#-*- coding: utf-8 -*-
from __future__ import print_function
import sys
import requests
import json
import yaml
import time
import os
import traceback


def getProjectList(session, headers, endpoint, HOST):
    # https://console.cloudendure.com/api/latest/projects
    # Get
    try:
        result = requests.get(HOST + endpoint.format('projects'), headers = headers, cookies = session)
        return json.loads(result.text)["items"]
    except:
        print("ERROR: Project List Failed....")
        print(result.status_code)
        traceback.print_exc()
        return []

def getMachineInfos(session, headers, endpoint, HOST, project_id, project_name):
    try:
        result = requests.get(HOST + endpoint.format('projects/{}/machines').format(project_id), headers = headers, cookies = session)
            # Response code translate to message
        if result.status_code == 200:

            project_machines = json.loads(result.text)['items']
            for machine in project_machines:
                machine['ce_project_id'] = project_id
                machine['ce_project_name'] = project_name
            return project_machines
        else:
            print("ERROR")
            print("STATUS : "+result.status_code)
            return []
    except:
        traceback.format_exc()
        return []

def getBlueprintInfos(session, headers, endpoint, HOST, project_id):
    try:
        b = requests.get(HOST + endpoint.format('projects/{}/blueprints').format(project_id), headers=headers, cookies=session)
        if b.status_code == 200:
            return json.loads(b.text)["items"]
        else:
            print("ERROR")
            print("STATUS : "+b.status_code)
            return []
    except:
        traceback.print_exc()
        return []
