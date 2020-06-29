#-*- coding: utf-8 -*-
from __future__ import print_function
import sys
import requests
import json
import yaml
import os
import Project
import Machine
import traceback

old_generation_instance_type = 't2.medium'
new_generation_instance_type = 't3.medium'

def makeTag(key, value):
    return {"key":'{}'.format(key), "value":'{}'.format(value)}

def startUpdateForCutover(session, headers, endpoint, HOST, config):
    return False

def startUpdateForTest(session, headers, endpoint, HOST, config):
    print("********************************")
    print("*   Start Test mode Blueprint  *")
    print("********************************")
    try:
        custom_tags = config['custom_tags'] if config.get('custom_tags') else {}
        default_tag_list = []
        if custom_tags:
            for tag_key in custom_tags.keys():
                default_tag_list.append(makeTag(tag_key, custom_tags[tag_key] if custom_tags[tag_key] else ''))
        project_infos = config['project_infos']
        work_projects = []
        for p in Project.getProjectList(session, headers, endpoint, HOST):
            if project_infos.get(p['name']):
                temp={}
                temp['name']=p['name']
                temp['id']=p['id']
                temp['subnet']=[project_infos[p['name']]['sandbox_subnet_id']]
                temp['sg'] = project_infos[p['name']]['security_group_ids'] if project_infos[p['name']].get('security_group_ids') else []
                temp['project_custom_tags'] = project_infos[p['name']]['project_custom_tags'] if project_infos[p['name']].get('project_custom_tags') else {}
                work_projects.append(temp)
            else:
                print('!!! Project [{}] not in YAML.'.format(p['name']))

        for p in work_projects:
            project_tags = []
            if p['project_custom_tags']:
                for tag_key in p['project_custom_tags'].keys():
                    project_tags.append(makeTag(tag_key, p['project_custom_tags'][tag_key] if p['project_custom_tags'][tag_key] else ''))
            action_machine_id_list = []
            action_machine_list = []
            print("==Start Project [{}]==".format(p['name']))
            try:
                machines = Project.getMachineInfos(session, headers, endpoint, HOST, p['id'], p['name'])
                for m in machines:
                    if Machine.isUpdateBlueprint(m):
                        action_machine_id_list.append(m['id'])
                        action_machine_list.append(m)
                temp = getBlueprintInfosNeedUpdate(Project.getBlueprintInfos(session, headers, endpoint, HOST, p['id']), action_machine_id_list, action_machine_list)
                blueprint_infos = temp[0]
                action_machine_list= temp[1]
                print('All Cnt : {}'.format(len(blueprint_infos)))
                print('Update Cnt : {}'.format(len(action_machine_list)))
                action_machine_list.reverse()
                for b in blueprint_infos:
                    m = action_machine_list.pop()
                    if not m['sourceProperties'].get('os'):
                        print(' ! ! ! [No OS INFO] Machine ID : {}, Machine Name : {}'.format(m['id'], m['sourceProperties']['name'] if m['sourceProperties'].get('name') else 'None'))
                        continue
                    machine_tags = []
                    machine_tags.append(makeTag('Os', m['sourceProperties'].get('os')))
                    machine_tags.append(makeTag('Name', m['sourceProperties']['name']))
                    machine_tags.append(makeTag('OldHostname', m['sourceProperties']['name']))
                    b["subnetIDs"] = p['subnet']
                    b["publicIPAction"] = 'DONT_ALLOCATE'
                    b["privateIPAction"] = 'CREATE_NEW'
                    b["securityGroupIDs"] = p['sg']
                    b["tags"] = default_tag_list + project_tags + machine_tags
                    b["instanceType"] = new_generation_instance_type if isNewGenerationByOS(m, p['name']) else old_generation_instance_type
                    for disk in b['disks']:
                        disk['type']='SSD'


                    if updateBlueprint(session, headers, endpoint, HOST, b, m):
                        Machine.launch("TEST", session, headers, endpoint, HOST, m)
                print("==END Project [{}]==".format(p['name']))
            except:
                print(" ! ! ! [Error]Project [{}] Failed".format(p['name']))
                traceback.print_exc()
    except:
        traceback.print_exc()
    print("********************************")
    print("*   END Test mode Blueprint  *")
    print("********************************")

def isNewGenerationByOS(machine, project_name):
    os = machine['sourceProperties'].get('os').lower() if machine['sourceProperties'].get('os') else 'none'
    if os.startswith('microsoft'):
        splited_os = os.split(' ')
        if len(splited_os) > 3:
            # Microsoft Windows Server 2003
            # Microsoft Windows Server 2008 R1
            # Microsoft Windows Server 2012 R1
            ws_version = splited_os[3]
            if ws_version.isdigit():
                ws_version = int(ws_version)
                if ws_version > 2003:
                    if 2008 == ws_version or 2012 == ws_version:
                        if len(splited_os)>4 and splited_os[4]=='r2':
                            return True
                    else:
                        return True
        return False
    elif os.startswith('linux'):
        #Linux version 3 below
        #Linux version 3.0.101-63-default (geeko@buildhost) (gcc version 4.3.4 [gcc-4_3-branch revision 152973] (SUSE Linux) ) #1 SMP Tue Jun 23 16:02:31 UTC 2015 (4b89d0c)
        splited_os = os.split(' ')
        if len(splited_os) >= 3:
            if len(splited_os[2])>0:
                if splited_os[2][0].isdigit():
                    if int(splited_os[2][0]) > 2:
                        return True
    print("Project : {} , HostName : {} is Unidentified OS".format(project_name, machine['sourceProperties']['name']))
    return False

def getBlueprintInfosNeedUpdate(blueprint_infos, action_machine_id_list, action_machine_list):
    result_blueprint_list = []
    result_machine_list = []
    for b in blueprint_infos:
        try:
            idx = action_machine_id_list.index(b["machineId"])
            result_blueprint_list.append(b)
            result_machine_list.append(action_machine_list[idx])
            del action_machine_id_list[idx]
            del action_machine_list[idx]
        except ValueError:
            pass
    return [result_blueprint_list, result_machine_list]


def updateBlueprint(session, headers, endpoint, HOST, blueprint_info, machine_info):
    try:
        result = requests.patch(HOST + endpoint.format('projects/{}/blueprints/').format(machine_info['ce_project_id']) + blueprint_info['id'], data=json.dumps(blueprint_info), headers=headers, cookies=session)
        if result.status_code == 200:
            print("{}   SUCCESS".format(machine_info['sourceProperties']['name']))
            return True
        else:
            print("ERROR: Updating blueprint failed for machine: " + machine_info['sourceProperties']['name'] +", invalid blueprint config....")
            print(result.status_code)
    except:
        traceback.print_exc()
    return False
