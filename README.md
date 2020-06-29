##
pip install pyyaml requests

CloudWatch Event 5min - Lambda


##yaml
username : cloudendure email
password : cloudendure password
location_infos:
    location1:
        office_hours :
            - 'hh:mm'   # Start
            - 'hh:mm'   # End
        office_hours_max_replication_num : 2 # Max Replication Number in Office houres
        max_replication_num : 4 # Max Replication Number after Office houres
        project_list:
            - proejct name 1
            ...
            - project name N
        priority_hostname_list:
            - hostname1
            ...
            - hostnameN
        except_hostname_list:
            - hostname1
            ...
            - hostnameN
    location2:
        office_hours :
            - '08:00'
            - '19:00'
        office_hours_max_replication_num : 2
        max_replication_num : 3
        project_list:
            - proejct name 1
            ...
            - project name N
        priority_hostname_list:
            - hostname1
            ...
            - hostnameN
        except_hostname_list:
            - hostname1
            ...
            - hostnameN
    locationN:
        office_hours :
            - '08:00'
            - '19:00'
        office_hours_max_replication_num : 2
        max_replication_num : 5
        project_list:
            - proejct name 1
            ...
            - project name N
        priority_hostname_list:
            - hostname1
            ...
            - hostnameN
        except_hostname_list:
            - hostname1
            ...
            - hostnameN

##replication Log pattern


************************
* Login to CloudEndure *
************************
************************
*    Success Login     *
************************
************************
*   Start Replication  *
************************
Location : DC1, max_replication_num : 4
Location : DC2, max_replication_num : 1
[Start Location ( DC1 ) ]
** [Start Running Replication Job]
**** Project : {}, Hostname : {}
**** Project : {}, Hostname : {}
** [End Running Replication Job]
**  Extra : 4
** [Start New Replications]
**** Project : {}, Hostname : {}
**** Project : {}, Hostname : {}
** [END New Replications]
[END Location ( DC1 ) ]
[Start Location ( DC2 ) ]
** [Start Running Replication Job]
**** Project : {}, Hostname : {}
**** Project : {}, Hostname : {}
** [End Running Replication Job]
**  Extra : 1
** [Start New Replications]
**** Project : {}, Hostname : {}
**** Project : {}, Hostname : {}
** [END New Replications]
[END Location ( DC2 ) ]
************************
*   END Replication  *
************************




## 1.Blueprint Setting
Migration Factory 로 대체
##Input yaml
username : {cloudendure email}
password : {cloudendure password}
project_infos:
    {project Name 1}:
        sandbox_subnet_id : {subnet id}
        security_group_id : {sg id1,sg id2...,sg idN}
    {project Name N}:
        sandbox_subnet_id : {subnet id}
        security_group_id : {sg id1,sg id2...,sg idN}
## 실행 명령어
CloudEndure.py --configfile real_testblueprint.yaml --type testblueprint
