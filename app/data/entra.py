from azure.identity import ClientSecretCredential
from msgraph.core import GraphClient
from requests import ReadTimeout

from app import flask_app
import sys, re, copy, time

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())



class Graph:
    client_credential: ClientSecretCredential
    client: GraphClient

    def __init__(self):
        # in Azure Directory Admin center, in the App Registration, in the app (Python Graph Tutorial), in  API permissions, make sure the TYPE of the permission is Application, NOT Delegated
        #  The required permissions can be found in the API reference, e.g. https://learn.microsoft.com/en-us/graph/api/user-list?view=graph-rest-1.0&tabs=http
        client_id = flask_app.config['ENTRA_CLIENT_ID']
        tenant_id = flask_app.config['ENTRA_TENANT_ID']
        client_secret = flask_app.config['ENTRA_CLIENT_SECRET']
        self.client_credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        self.client = GraphClient(credential=self.client_credential, scopes=['https://graph.microsoft.com/.default'])

    def create_team(self, data):
        body = {
            "template@odata.bind": "https://graph.microsoft.com/v1.0/teamsTemplates('educationClass')",
            "displayName": data["name"],
            "description": data["description"],
            "members": [{"@odata.type": "#microsoft.graph.aadUserConversationMember", "roles": ["owner"],
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{data['owners'][0]}')"
                }
            ]
        }
        resp = self.client.post("/teams", json=body)
        if resp.status_code == 202:
            location = resp.headers.get("location")
            team_id = re.match("/teams\('(.*)'\)/oper", location)[1]
            log.info(f'{sys._getframe().f_code.co_name}: New cc-team {team_id}')
            return team_id
        else:
            log.error(f'{sys._getframe().f_code.co_name}: post.teams returned error {resp.text}')
        return None

    def create_team_with_members(self, data):
        body = {
            "template@odata.bind": "https://graph.microsoft.com/v1.0/teamsTemplates('educationClass')",
            "displayName": data["name"],
            "description": data["description"],
            "members": [{"@odata.type": "#microsoft.graph.aadUserConversationMember", "roles": ["owner"],
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{data['owners'][0]}')"
                }
            ]
        }
        resp = self.client.post("/teams", json=body)
        if resp.status_code == 202:
            location = resp.headers.get("location")
            team_id = re.match("/teams\('(.*)'\)/oper", location)[1]
            data["id"] = team_id
            persons_data = copy.deepcopy(data)
            persons_data["owners"].pop(0)
            self.add_persons(persons_data)
            log.info(f'{sys._getframe().f_code.co_name}: New cc-team {team_id}')
            return team_id
        else:
            log.error(f'{sys._getframe().f_code.co_name}: post.teams returned error {resp.text}')
        return None

    def delete_group(self, group_id):
        resp = self.client.delete(f"/groups/{group_id}")
        if resp.status_code == 204:
            log.info(f'{sys._getframe().f_code.co_name}: Delete group {group_id}')
            return group_id
        else:
            log.error(f'{sys._getframe().f_code.co_name}: delete.groups/{group_id} returned error {resp.text}')
        return None

    def add_persons(self, data):
        values =[]
        if "members" in data:
            for member in data["members"]:
                if member != "":
                    values.append({"@odata.type": "microsoft.graph.aadUserConversationMember", "roles":[], "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{member}')"})
        if "owners" in data:
            for owner in data["owners"]:
                if owner != "":
                    values.append({"@odata.type": "microsoft.graph.aadUserConversationMember", "roles":["owner"], "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{owner}')"})
        if values:
            retry_ctr = 0
            delay = 5
            while retry_ctr < 5:
                resp = self.client.post(f"/teams/{data['id']}/members/add", json={"values": values})
                if resp.status_code == 200:
                    return True
                retry_ctr += 1
                log.info(f'{sys._getframe().f_code.co_name}: post.teams retry {retry_ctr}, delay {delay}')
                time.sleep(delay)
            log.error(f'{sys._getframe().f_code.co_name}: post.teams {data["id"]}/members/add timeout')
            return False
        return False

    def delete_persons(self, data):
        retry_ctr = 0
        delay = 5
        while retry_ctr < 5:
            try:
                ret = True
                for member in data["members"]:
                    resp = self.client.delete(f"/groups/{data['id']}/members/{member}/$ref")
                    if resp.status_code != 204:
                        log.error(f'{sys._getframe().f_code.co_name}: delete.groups/{data["id"]}/members/{member} returned error {resp.text}')
                        ret = False

                for member in data["owners"]:
                    resp = self.client.delete(f"/groups/{data['id']}/members/{member}/$ref")
                    if resp.status_code != 204:
                        log.error(f'{sys._getframe().f_code.co_name}: delete.groups/{data["id"]}/members/{member} returned error {resp.text}')
                        ret = False
                    resp = self.client.delete(f"/groups/{data['id']}/owners/{member}/$ref")
                    if resp.status_code != 204:
                        log.error(f'{sys._getframe().f_code.co_name}: delete.groups/{data["id"]}/owners/{member} returned error {resp.text}')
                        ret = False
                return ret
            except ReadTimeout as e:
                retry_ctr += 1
                log.info(f'{sys._getframe().f_code.co_name}: post.teams retry {retry_ctr}, delay {delay}')
                time.sleep(delay)
        log.error(f'{sys._getframe().f_code.co_name}: post.teams {data["id"]}/members/delete timeout')

    def intune_get_devices(self):
        items = []
        select = "lastSyncDateTime,enrolledDateTime,deviceName,userId,id,serialNumber,complianceState,deviceEnrollmentType,azureADDeviceId"
        order_by = 'deviceName'
        url = f'/deviceManagement/managedDevices?$select={select}&$orderBy={order_by}'
        while url:
            resp = self.client.get(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
                return []
            data = resp.json()
            items += data["value"]
            url = data["@odata.nextLink"] if "@odata.nextLink" in data else None
        return items

    def entra_get_devices(self):
        items = []
        url = "https://graph.microsoft.com/v1.0/devices?$select=id,deviceId"
        while url:
            resp = self.client.get(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
                return []
            data = resp.json()
            items += data["value"]
            url = data["@odata.nextLink"] if "@odata.nextLink" in data else None
        return items

    def autopilot_get_devices(self):
        items = []
        url = f'/deviceManagement/windowsAutopilotDeviceIdentities'
        while url:
            resp = self.client.get(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
                return []
            data = resp.json()
            items += data["value"]
            url = data["@odata.nextLink"] if "@odata.nextLink" in data else None
        return items

    def delete_device(self, device):
        if device.intune_id:
            url = f'https://graph.microsoft.com/v1.0/deviceManagement/managedDevices/{device.intune_id}'
            resp = self.client.delete(url)
            if resp.status_code != 204:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')

        if device.autopilot_id:
            url = f'https://graph.microsoft.com/v1.0/deviceManagement/windowsAutopilotDeviceIdentities/{device.autopilot_id}'
            resp = self.client.delete(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')

        if device.entra_id:
            url = f'https://graph.microsoft.com/v1.0/devices/{device.entra_id}'
            resp = self.client.delete(url)
            if resp.status_code != 204:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')

    def get_teams(self):
        items = []
        url = f'/groups?$select=id,createdDateTime,creationOptions,description,displayName'
        while url:
            resp = self.client.get(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
                return []
            data = resp.json()
            items += data["value"]
            url = data["@odata.nextLink"] if "@odata.nextLink" in data else None
        return items

    def get_team_details(self, id):
        url = f"/teams/{id}?$select=isArchived"
        resp = self.client.get(url, timeout=200)
        if resp.status_code != 200:
            log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
            return None
        data = resp.json()
        return data

    def get_team_members(self, id):
        url = f"/groups/{id}/members?$select=id,officeLocation"
        resp = self.client.get(url, timeout=200)
        if resp.status_code != 200:
            log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
            return None
        data = resp.json()
        return data

    def get_users(self):
        items = []
        url = f'/users?$select=id,userPrincipalName'
        while url:
            resp = self.client.get(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
                return []
            data = resp.json()
            items += data["value"]
            url = data["@odata.nextLink"] if "@odata.nextLink" in data else None
        return items


    def get_user_teams(self, id):
        items = []
        url = f'/users/{id}/joinedTeams'
        while url:
            resp = self.client.get(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
                return []
            data = resp.json()
            items += data["value"]
            url = data["@odata.nextLink"] if "@odata.nextLink" in data else None
        data = [{"id": i["id"], "name": i["displayName"], "description": i["description"]} for i in items]
        return data



    def get_team_activity_details(self):
        url = "/reports/getTeamsTeamActivityDetail(period='D180')"
        resp = self.client.get(url)
        if resp.status_code != 200:
            log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.text}')
            return []
        data = re.sub("\".*\"", "", resp.text)
        list_of_list = [i.split(",") for i in data.split("\n")]
        data = [dict(zip(list_of_list[0], i)) for i in list_of_list]
        data.pop(0)
        return data


entra = Graph()
