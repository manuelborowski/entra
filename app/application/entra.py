import sys, datetime, json, re, copy
from app.data import group as mgroup, staff as mstaff, student as mstudent, klas as mklas
from app.data.group import Group
from app.data.models import add, commit
from app.data.entra import entra

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


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


def cron_sync_team_activities(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        db_groups = mgroup.group_get_m()
        group_cache = {g.entra_id: g for g in db_groups} if db_groups else {}
        activities = entra.get_team_activity_details()
        for activity in activities:
            if "Team Id" in activity and activity["Team Id"] in group_cache:
                if activity["Last Activity Date"] != "":
                    last_activity = datetime.datetime.strptime(activity["Last Activity Date"], "%Y-%m-%d").date()
                    group_cache[activity["Team Id"]].last_activity = last_activity
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



#Sync classroomcloud auto-teams, i.e. which are automatically created from klassen, klasgroepen, studenten en staff from SDH
# for all classes in the students table, create a team, add the students as members and add all teachers as owners.
def cron_sync_cc_auto_teams(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        class MetaTeam():
            def __init__(self, team=None):
                self.team = team
                self._owners_to_add = []
                self._owners_to_remove = []
                self._members_to_add = []
                self._members_to_remove = []

            def get_owners_to_add(self):
                return self._owners_to_add

            def get_owners_to_remove(self):
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

        db_klassen = mklas.klas_get_m()
        klassen = {k.klascode: k.klasgroepcode for k in db_klassen}
        klasgroepen_cache = list(set([k.klasgroepcode for k in db_klassen]))
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto))
        new_staffs = mstaff.staff_get_m(("new", "=", True))
        delete_staffs = mstaff.staff_get_m(("delete", "=", True))
        current_staffs = mstaff.staff_get_m([("delete", "=", False), ("new", "=", False)])

        delete_cc_teams = []
        new_cc_teams = []
        for cc_team in db_cc_teams:
            klasgroepcode = cc_team.get_klasgroepcode()
            if klasgroepcode in klasgroepen_cache:
                klasgroepen_cache.remove(klasgroepcode)
            else:
                delete_cc_teams.append(cc_team)
        # deleted klasgroepen
        for cc_team in delete_cc_teams:
            entra.delete_group(cc_team.entra_id)
        mgroup.group_delete_m(groups=delete_cc_teams)
        # new klasgroepen
        for klasgroepcode in klasgroepen_cache:
            data = {
                "name": mgroup.Group.get_cc_display_name(klasgroepcode),
                "description": mgroup.Group.get_cc_description(klasgroepcode),
                "owners": [o.entra_id for o in current_staffs]
            }
            team_id = entra.create_team_with_members(data)
            if team_id:
                new_cc_teams.append({"entra_id": team_id, "display_name": data["name"], "description": data["description"],
                                  "created": datetime.datetime.now(), "type": mgroup.Group.Types.cc_auto, "owners": json.dumps(data["owners"])})
        mgroup.group_add_m(new_cc_teams)
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto))
        meta_teams = {t.get_klasgroepcode(): MetaTeam(team=t) for t in db_cc_teams}

        db_students = mstudent.student_get_m(("new", "=", True))
        for student in db_students:
            if student.klascode in klassen:
                klasgroepcode = klassen[student.klascode]
                meta_teams[klasgroepcode].add_members_to_add(student)
            else:
                log.error(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')

        db_students = mstudent.student_get_m(("delete", "=", True))
        for student in db_students:
            if student.klascode in klassen:
                klasgroepcode = klassen[student.klascode]
                if klasgroepcode in meta_teams:
                    meta_teams[klasgroepcode].add_members_to_remove(student)
            else:
                log.error(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')

        db_students = mstudent.student_get_m(("changed", "!", ""))
        for student in db_students:
            if "klascode" in student.changed:
                if student.klascode in klassen:
                    klasgroepcode = klassen[student.klascode]
                    meta_teams[klasgroepcode].add_members_to_add(student)
                    prev_klascode = json.loads(student.changed_old)["klascode"]
                    if prev_klascode in klassen:
                        prev_klasgroepcode = klassen[prev_klascode]
                        if prev_klasgroepcode in meta_teams:
                            meta_teams[prev_klasgroepcode].add_members_to_remove(student)
                else:
                    log.error(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')

        if new_staffs or delete_staffs:
            for klasgroepcode, meta_team in meta_teams.items():
                for staff in new_staffs:
                    meta_team.add_owners_to_add(staff)
                for staff in delete_staffs:
                    meta_team.add_owners_to_remove(staff)

        for _, meta_team in meta_teams.items():
            add_persons_data = {"members": meta_team.get_members_to_add(), "owners":  meta_team.get_owners_to_add(), "id": meta_team.team.entra_id}
            resp = entra.add_persons(add_persons_data)
            if resp:
                meta_team.team.add_members(add_persons_data["members"])
                meta_team.team.add_owners(add_persons_data["owners"])

            remove_persons_data = {"members": meta_team.get_members_to_remove(), "owners":  meta_team.get_owners_to_remove(), "id": meta_team.team.entra_id}
            entra.delete_persons(remove_persons_data)
            meta_team.team.del_members(remove_persons_data["members"])
            meta_team.team.del_owners(remove_persons_data["owners"])
        commit()

    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')





