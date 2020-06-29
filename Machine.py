#-*- coding: utf-8 -*-
from __future__ import print_function
import sys
import requests
import json
import yaml
import time
import os
import traceback
import Project
import datetime

fiveMinTimeDelta = datetime.timedelta(minutes=5)

def isUpdateBlueprint(machine_info):
    try:
        if 'lastTestLaunchDateTime' not in machine_info["lifeCycle"] and 'lastCutoverDateTime' not in machine_info["lifeCycle"]:
            return True
        return False
    except:
        traceback.print_exc()
        return False

def isRunningMigration(machine, now_utc):
    replicationInfo = machine['replicationInfo']
    replicationInitiationStates = replicationInfo['initiationStates']
    if len(replicationInitiationStates['items'])==0:
        return False
    lastStateInfos = replicationInitiationStates['items'][-1]['steps']

    #if 'lastConsistencyDateTime' not in replicationInfo:
    #    return False

    #CheckMachine.py line 42

    #When Last Step Success
    if lastStateInfos[-1]['status']=='SUCCEEDED' and lastStateInfos[-1]['name']=='ESTABLISHING_AGENT_REPLICATOR_COMMUNICATION':

        rescannedStorage = replicationInfo.get('rescannedStorageBytes')
        replicatedStorage = replicationInfo.get('replicatedStorageBytes') if replicationInfo.get('replicatedStorageBytes') else 0
        totalStorage = replicationInfo.get('totalStorageBytes') if replicationInfo.get('totalStorageBytes') else 0

        #re-scan
        if not rescannedStorage==None:
            if rescannedStorage!=replicatedStorage and replicatedStorage:
                return True
        if totalStorage == replicatedStorage:
            return False
        return True
    else:
        if lastStateInfos[0]['status'] == "NOT_STARTED":
            startDateTime = datetime.datetime.strptime(replicationInitiationStates['items'][-1]['startDateTime'], '%Y-%m-%dT%H:%M:%S.%f+00:00')
            #2019-10-30T09:08:33.695587+00:00
            if (now_utc - startDateTime) < fiveMinTimeDelta:
                return True
        else:
            for stateInfo in lastStateInfos:
                if stateInfo['status'] == "FAILED":
                    break
            else:
                return True
        return False

def startReplicationProcess(session, headers, endpoint, HOST, config, localtime):
    print("************************")
    print("*   Start Replication  *")
    print("************************")
    try:
        now_utc = datetime.datetime.utcnow()
        now_local = now_utc+datetime.timedelta(hours=localtime)
        now_local_delta = datetime.timedelta(hours=now_local.hour, minutes=now_local.minute)
        all_project = {}
        for p in Project.getProjectList(session, headers, endpoint, HOST):
            all_project[p['name']]=p['id']
        config_location_infos = config['location_infos'] if config.get('location_infos') else {}
        location_infos = []
        # office_hours :
        #     - 08:00
        #     - 19:00
        # office_hours_max_replication_num
        # max_replication_num
        # project_id_list
        # priority_hostname_list
        # except_hostname_list

        for location_name in config_location_infos.keys():
            location_info = config_location_infos[location_name]

            temp_location_dict = {}
            temp_location_dict['location_name'] = location_name
            temp_project_id_list = []
            temp_project_name_list = []
            max_replication_num = location_info['max_replication_num']

            if location_info['max_replication_num'] != location_info['office_hours_max_replication_num']:
                office_hours = location_info['office_hours']
                startTimeArray = office_hours[0].split(':')
                startTimeDelta = datetime.timedelta(minutes=int(startTimeArray[1]),hours=int(startTimeArray[0]))
                endTimeArray = office_hours[1].split(':')
                endTimeDelta = datetime.timedelta(minutes=int(endTimeArray[1]),hours=int(endTimeArray[0]))
                if startTimeDelta < endTimeDelta:
                    if now_local_delta > startTimeDelta and now_local_delta < endTimeDelta:
                        max_replication_num = location_info['office_hours_max_replication_num']
                else:
                    if (startTimeDelta > now_local_delta and now_local_delta < endTimeDelta)\
                            or startTimeDelta < now_local_delta:
                        max_replication_num = location_info['office_hours_max_replication_num']

            print("Location : {}, max_replication_num : {}".format(location_name, max_replication_num))
            temp_location_dict['max_replication_num']=max_replication_num
            for project in location_info['project_list']:
                if all_project.get(project):
                    temp_project_id_list.append(all_project[project])
                    temp_project_name_list.append(project)
            temp_location_dict['project_id_list'] = temp_project_id_list
            temp_location_dict['project_name_list'] = temp_project_name_list
            temp_location_dict['priority_hostname_list'] = location_info['priority_hostname_list'] if location_info['priority_hostname_list'] else []
            temp_location_dict['except_hostname_list'] = location_info['except_hostname_list'] if location_info['except_hostname_list'] else []
            location_infos.append(temp_location_dict)

        for location_info in location_infos:
            print('[Start Location ( {} ) ]'.format(location_info['location_name']))
            max_replication_num = location_info['max_replication_num']
            except_hostname_list = location_info['except_hostname_list']
            priority_hostname_list = location_info['priority_hostname_list']
            for i in range(len(priority_hostname_list)):
                priority_hostname_list[i] = priority_hostname_list[i].lower()
            machineInfos = []
            replicationStoppedMachines = []
            currentReplicationCnt = 0
            location_info['project_name_list'].reverse()
            for project_id in location_info['project_id_list']:
                machineInfos+=Project.getMachineInfos(session, headers, endpoint, HOST, project_id, location_info['project_name_list'].pop())

            print('** [Start Running Replication Job]')
            for machine in machineInfos:
                if machine['sourceProperties']['name'] in except_hostname_list:
                    continue
                if machine['replicationStatus'] == 'STARTED':
                    if isRunningMigration(machine, now_utc):
                        currentReplicationCnt+=1
                        print('**** Project : {}, Hostname : {}'.format(machine['ce_project_name'], machine['sourceProperties']['name']))
                        print(machine)
                else:
                    try:
                        machine['custom_priority']=priority_hostname_list.index(machine['sourceProperties']['name'].lower())
                    except ValueError:
                        machine['custom_priority']=float("inf")
                    replicationStoppedMachines.append(machine)

            print('** [End Running Replication Job]')

            replicationStoppedMachines.sort(key=lambda x:x['custom_priority'])
            extra = max_replication_num-currentReplicationCnt
            print("**  Extra : {}".format(extra))
            print("** [Start New Replications]")
            if extra > 0:
                for machine in replicationStoppedMachines:
                    if extra < 1:
                        break
                    print('**** Project : {}, HostName : {}'.format(machine['ce_project_name'], machine['sourceProperties']['name']))
                    print(machine)
                    startReplicationOneMachine(session, headers, endpoint, HOST, machine['ce_project_id'], machine['id'])
                    extra-=1
            print("** [END New Replications]")
            print('[END Location ( {} ) ]'.format(location_info['location_name']))
    except:
        traceback.print_exc()
    print("************************")
    print("*   END Replication  *")
    print("************************")

def startReplicationOneMachine(session, headers, endpoint, HOST, project_id, machine_id):
    # POST /projects/{projectId}/startReplication
    try:
        machine_ids = {'machineIDs': [machine_id]}
        response = requests.post(HOST + endpoint.format('projects/{}/startReplication').format(project_id),
                                     data=json.dumps(machine_ids), headers = headers, cookies = session)
        items = json.loads(response.text)["items"]
        if len(items)<1:
            return False
        if items[0]['replicationStatus']=='STARTED':
            return True
        return False
    except:
        traceback.print_exc()
        return False

def getMachineDetail(session, headers, endpoint, HOST, project_id, machine_id):
    # https://console.cloudendure.com/api/latest/projects/{projectId}/machines/{machineId}

    # POST /projects/{projectId}/startReplication
    response = requests.get(HOST + endpoint.format('projects/{}/machines/{}').format(project_id,machine_id),
                                 headers = headers, cookies = session)
    print(json.loads(response.text))
    return False


#launchtype
#   "TEST"
#   "CUTOVER"
def launch(launchtype, session, headers, endpoint, HOST, machine_info):
    if 'lastConsistencyDateTime' not in machine_info['replicationInfo'].keys():
        print('**[ERROR] (Running Replication) Launch Type : {}, Project : {}, HostName : {}'.format(launchtype, machine_info['ce_project_name'], machine_info['sourceProperties']['name']))
        return
    if ('lastTestLaunchDateTime' in machine_info["lifeCycle"].keys() if launchtype == 'TEST' else 'lastTestLaunchDateTime' not in machine_info["lifeCycle"].keys()) or 'lastCutoverDateTime' in machine_info["lifeCycle"].keys():
        prefixStr = '(Already launched the Cutover Machine or Not Tested.)'
        if launchtype == 'TEST':
            prefixStr = '(Already launched the target Machine.)'
        print('**[ERROR] {} Launch Type : {}, Project : {}, HostName : {}'.format(prefixStr, launchtype, machine_info['ce_project_name'], machine_info['sourceProperties']['name']))
        return
    a = int(machine_info['replicationInfo']['lastConsistencyDateTime'][11:13])
    b = int(machine_info['replicationInfo']['lastConsistencyDateTime'][14:16])
    x = int(datetime.datetime.utcnow().isoformat()[11:13])
    y = int(datetime.datetime.utcnow().isoformat()[14:16])
    result = (x - a) * 60 + (y - b)
    if result > 180:
        print("ERROR: Machine: " + machine_info['sourceProperties']['name'] + " replication lag is more than 180 minutes....")
        print("- Current Replication lag for " + machine_info['sourceProperties']['name'] + " is: " + str(result) + " minutes....")
        return
    machine_ids = []
    machine_names = []
    machine_data={}

    machine_ids.append({"machineId": machine_info['id']})
    machine_data['items'] = machine_ids
    machine_data["launchType"] = launchtype

    result = requests.post(HOST + endpoint.format('projects/{}/launchMachines').format(machine_info['ce_project_id']), data = json.dumps(machine_data), headers = headers, cookies = session)
        # Response code translate to message
    if result.status_code == 202:
        print('[SUCCESS] Launch Type : {}, Project : {}, HostName : {}'.format(launchtype, machine_info['ce_project_name'], machine_info['sourceProperties']['name']))
    else:
        print('**[ERROR] Project : {}, HostName ')
        if result.status_code == 409:
            print("**[ERROR] Source machines have job in progress....")
        elif result.status_code == 402:
            print("**[ERROR] Project license has expired....")
        else:
            print(result.text)
            print("**[ERROR] Launch target machine failed....")
