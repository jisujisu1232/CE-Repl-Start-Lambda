#-*- coding: utf-8 -*-
from __future__ import print_function
import sys
import argparse
import requests
import json
import yaml
import Machine
import Blueprint
import time
import os


HOST = 'https://console.cloudendure.com'
headers = {'Content-Type': 'application/json'}
session = {}
endpoint = '/api/latest/{}'


def login(config, endpoint):
    print("************************")
    print("* Login to CloudEndure *")
    print("************************")
    login_data = {'username': config['username'], 'password': config['password']}
    r = requests.post(HOST + endpoint.format('login'),
                  data=json.dumps(login_data), headers=headers)
    if r.status_code != 200 and r.status_code != 307:
        if r.status_code == 401:
            print("ERROR: The login credentials provided cannot be authenticated....")
        elif r.status_code == 402:
            print("ERROR: There is no active license configured for this account....")
        elif r.status_code == 429:
            print("ERROR: Authentication failure limit has been reached. The service will become available for additional requests after a timeout....")
        sys.exit(1)

    # check if need to use a different API entry point
    if r.history:
        endpoint = '/' + '/'.join(r.url.split('/')[3:-1]) + '/{}'
        r = requests.post(HOST + endpoint.format('login'),
                      data=json.dumps(login_data), headers=headers)

    session['session'] = r.cookies['session']
    try:
       headers['X-XSRF-TOKEN'] = r.cookies['XSRF-TOKEN']
    except:
       pass
    print("************************")
    print("*    Success Login     *")
    print("************************")
def lambda_handler(event, context):
    with open(os.path.join(sys.path[0], 'real_testreplication.yaml'), 'r') as ymlfile:
        config = yaml.load(ymlfile, Loader=yaml.FullLoader)

    login(config, endpoint)
    Machine.startReplicationProcess(session, headers, endpoint, HOST, config, 9)
