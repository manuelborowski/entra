from app import flask_app
from azure.identity import ClientSecretCredential
from msgraph.core import GraphClient
import sys, datetime, json, re
from app.data import group as mgroup, staff as mstaff, student as mstudent, klas as mklas
from app.data.group import Group
from app.data.models import add, commit

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
            data["id"] = team_id
            data["owners"].pop(0)
            self.add_persons(data)
            log.info(f'{sys._getframe().f_code.co_name}: New cc-team {team_id}')
            return team_id
        else:
            log.error(f'{sys._getframe().f_code.co_name}: post.teams returned status_code {resp.status_code}')
        return None

    def delete_group(self, group_id):
        resp = self.client.delete(f"/groups/{group_id}")
        if resp.status_code == 204:
            log.info(f'{sys._getframe().f_code.co_name}: Delete group {group_id}')
            return group_id
        else:
            log.error(f'{sys._getframe().f_code.co_name}: delete.groups/{group_id} returned status_code {resp.status_code}')
        return None

    def add_persons(self, data):
        values =[]
        for member in data["members"]:
            values.append({"@odata.type": "microsoft.graph.aadUserConversationMember", "roles":[], "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{member}')"})
        for owner in data["owners"]:
            values.append({"@odata.type": "microsoft.graph.aadUserConversationMember", "roles":["owner"], "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{owner}')"})
        if values:
            resp = self.client.post(f"/teams/{data['id']}/members/add", json={"values": values})
            if resp.status_code == 200:
                log.info(f'{sys._getframe().f_code.co_name}: Add members and owners to {data["id"]}')
                return True
            log.error(f'{sys._getframe().f_code.co_name}: post.teams{data["id"]}/members/add returned status_code {resp.status_code}')
            return False
        return True

    def delete_persons(self, data):
        values =[]
        for member in data["members"]:
            resp = self.client.delete(f"/teams/{data['id']}/members/{member}")
            if resp.status_code == 204:
                log.info(f'{sys._getframe().f_code.co_name}: Delete member {member} from {data["id"]}')
            else:
                log.error(f'{sys._getframe().f_code.co_name}: post.teams{data["id"]}/members/add returned status_code {resp.status_code}')

        for member in data["owners"]:
            resp = self.client.delete(f"/teams/{data['id']}/members/{member}")
            if resp.status_code == 204:
                log.info(f'{sys._getframe().f_code.co_name}: Delete owner {member} from {data["id"]}')
            else:
                log.error(f'{sys._getframe().f_code.co_name}: post.teams{data["id"]}/members/add returned status_code {resp.status_code}')
        return False



    def get_computers(self, link=None):
        if link:
            request_url = link
        else:
            endpoint = '/deviceManagement/managedDevices'
            select="complianceState,managedDeviceOwnerType,deviceName,userPrincipalName"
            order_by = 'deviceName'
            request_url = f'{endpoint}?$select={select}&$orderBy={order_by}'
        response = self.client.get(request_url)
        return response.json()

    def get_teams(self):
        items = []
        url = f'/groups?$select=id,createdDateTime,creationOptions,description,displayName'
        while url:
            resp = self.client.get(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.status_code}')
                return []
            data = resp.json()
            items += data["value"]
            url = data["@odata.nextLink"] if "@odata.nextLink" in data else None
        return items

    def get_team_details(self, id):
        url = f"/teams/{id}?$select=isArchived"
        resp = self.client.get(url, timeout=200)
        if resp.status_code != 200:
            log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.status_code}')
            return None
        data = resp.json()
        return data

    def get_users(self):
        items = []
        url = f'/users?$select=id,userPrincipalName'
        while url:
            resp = self.client.get(url)
            if resp.status_code != 200:
                log.error(f'{sys._getframe().f_code.co_name}: {url} returned status_code {resp.status_code}')
                return []
            data = resp.json()
            items += data["value"]
            url = data["@odata.nextLink"] if "@odata.nextLink" in data else None
        return items


entra = Graph()


def cron_sync_groups(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        #get groups from entra
        new_groups = []
        retry_groups = []
        db_groups = mgroup.group_get_m()
        group_cache = {g.entra_id: g for g in db_groups} if db_groups else {}
        entra_groups = entra.get_teams()
        group_ctr = 0
        for group in entra_groups:
            group_ctr += 1
            if group_ctr % 500 == 0:
                log.info(f'{sys._getframe().f_code.co_name}: processed {group_ctr} groups')
            if group["id"] in group_cache: # update
                db_group = group_cache[group["id"]]
                if group["description"] != db_group.description:
                    db_group.description = group["description"]
                if group["displayName"] != db_group.display_name:
                    db_group.display_name = group["displayName"]
                del(group_cache[group["id"]])
            else: # new
                ng = Group()
                if "classAssignments" in group["creationOptions"]:
                    type = Group.Types.klas
                    props = entra.get_team_details(group["id"])
                    if props:
                        ng.archived = props["isArchived"]
                    else:
                        retry_groups.append(group["id"])
                elif "Team" in group["creationOptions"]:
                    type = Group.Types.team
                else:
                    type = Group.Types.groep
                ng.description = group["description"]
                ng.display_name = group["displayName"]
                ng.entra_id = group["id"]
                ng.type = type
                ng.created = datetime.datetime.strptime(group["createdDateTime"], "%Y-%m-%dT%H:%M:%SZ")
                add(ng)
        deleted_groups = [v for (k, v) in group_cache.items()]
        mgroup.group_delete_m(groups=deleted_groups)
        commit()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def cron_sync_users(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        entra_users = entra.get_users()
        user_cache = {u["userPrincipalName"].split("@")[0]: u for u in entra_users}
        db_students = mstudent.student_get_m()
        for student in db_students:
            if student.username in user_cache:
                student.entra_id = user_cache[student.username]["id"]
        db_staffs = mstaff.staff_get_m()
        for staff in db_staffs:
            if staff.code in user_cache:
                staff.entra_id = user_cache[staff.code]["id"]
        commit()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')



# for all classes in the students table, create a team, add the students as members and add all teachers as owners.
def cron_sync_cc_teams(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        class MetaTeam():
            def __init__(self, team=None, klasgroepcode=None):
                self.team = team
                self.klasgroepcode = klasgroepcode
                self._owners_to_add = []
                self._owners_to_remove = []
                self._members_to_add = []
                self._members_to_remove = []

            def get_owners_to_add(self):
                return self._owners_to_add

            def get_ownser_to_remove(self):
                return self._owners_to_remove

            def get_members_to_add(self):
                return self._members_to_add

            def get_members_to_remove(self):
                return self._members_to_remove

            def add_owners_to_add(self, owner):
                self._owners_to_add.append(owner.entra_id)

            def add_owners_to_remove(self, owner):
                self._owners_to_remove.append(owner.entra_id)

            def add_members_to_add(self, member):
                self._members_to_add.append(member.entra_id)

            def add_members_to_remove(self, member):
                self._members_to_remove.append(member.entra_id)

        update_teams = {}
        db_klassen = mklas.klas_get_m()
        klassen = {k.klascode: k.klasgroepcode for k in db_klassen}
        klasgroepen_cache = [k.klasgroepcode for k in db_klassen]
        db_cc_teams = mgroup.group_get_m(("type", "=", "cc"))
        meta_teams = {t.description.split("-")[1]: MetaTeam(team=t) for t in db_cc_teams}
        new_staffs = mstaff.staff_get_m(("new", "=", True))
        delete_staffs = mstaff.staff_get_m(("delete", "=", True))
        current_staffs = mstaff.staff_get_m(("delete", "=", False))

        delete_cc_teams = []
        new_cc_teams = []
        for cc_team in db_cc_teams:
            klasgroepcode = cc_team.get_klasgroepcode()
            if klasgroepcode in klasgroepen_cache:
                del(klasgroepen_cache[klasgroepcode])
            else:
                delete_cc_teams.append(cc_team)
        # deleted klasgroepen
        for cc_team in delete_cc_teams:
            entra.delete_group(cc_team.entra_id)
        mgroup.group_delete_m(groups=delete_cc_teams)
        # new klasgroepen
        for klasgroepcode in klasgroepen_cache:
            data = {
                "name": f"cc-{klasgroepcode}",
                "description": f"cc-{klasgroepcode}",
                "owners": [o.entra_id for o in current_staffs]
            }
            team_id = entra.create_team(data)
            if team_id:
                new_cc_teams.append({"entra_id": team_id, "display_name": data["name"], "description": data["description"],
                                  "created": datetime.datetime.now(), "type": mgroup.Group.Types.cc, "owners": data["owners"]})
        mgroup.group_add_m(new_cc_teams)

        db_students = mstudent.student_get_m(("new", "=", True))
        for student in db_students:
            klasgroepcode = klassen[student.klascode]
            if klasgroepcode not in meta_teams:
                meta_teams[klasgroepcode] = MetaTeam(klasgroepcode=klasgroepcode)
            meta_teams[klasgroepcode].add_members_to_add(student)

        db_students = mstudent.student_get_m(("delete", "=", True))
        for student in db_students:
            klasgroepcode = klassen[student.klascode]
            if klasgroepcode in meta_teams:
                meta_teams[klasgroepcode].add_members_to_remove(student)

        db_students = mstudent.student_get_m(("changed", "!", ""))
        for student in db_students:
            if "klascode" in student.changed:
                klasgroepcode = klassen[student.klascode]
                if klasgroepcode not in meta_teams:
                    meta_teams[klasgroepcode] = MetaTeam(klasgroepcode=klasgroepcode)
                meta_teams[klasgroepcode].add_members_to_add(student)
                prev_klascode = json.loads(student.changed_old)["klascode"]
                if prev_klascode in klassen:
                    prev_klasgroepcode = klassen[prev_klascode]
                    if prev_klasgroepcode in meta_teams:
                        meta_teams[prev_klascode].add_members_to_remove(student)

        if new_staffs or delete_staffs:
            for klasgroepcode, meta_team in meta_teams.items():
                for staff in new_staffs:
                    meta_team.add_owners_to_add(staff)
                for staff in delete_staffs:
                    meta_team.add_owners_to_remove(staff)

        new_teams = []
        update_teams = []
        for _, meta_team in meta_teams.items():
            if meta_team.klasgroepcode is not None: # i.e. team does not exist yet
                data = {
                    "name": f"cc-{meta_team.klasgroepcode}",
                    "description": f"cc-{meta_team.klasgroepcode}",
                    "members": meta_team.get_members_to_add(),
                    "owners": [o.entra_id for o in current_staffs]
                }
                team_id = entra.create_team(data)
                if team_id:
                    new_teams.append({"entra_id": team_id, "display_name": data["name"], "description": data["description"],
                        "created": datetime.datetime.now(), "type": mgroup.Group.Types.cc, "members": data["members"], "owners": data["owners"] })

            if meta_team.team is not None:
                del(klasgroepen_cache[meta_team.team.get_klasgroepcode()])
                add_persons_data = {"members": meta_team.get_members_to_add(), "owners":  meta_team.get_owners_to_add(), "id": meta_team.team.entra_id}
                meta_team.team.add_members(add_persons_data["members"])
                meta_team.team.add_owners(add_persons_data["owners"])
                entra.add_persons(add_persons_data)
                
                remove_persons_data = {"members": meta_team.get_members_to_remove(), "owners":  meta_team.get_owners_to_remove(), "id": meta_team.team.entra_id}
                meta_team.team.del_members(remove_persons_data["members"])
                meta_team.team.del_owners(remove_persons_data["owners"])
                entra.delete_persons(remove_persons_data)


        mgroup.group_add_m(new_teams)
        commit()


        print(meta_teams)

    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')



