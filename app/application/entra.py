import sys, datetime, json, re, copy
from app.data import group as mgroup, staff as mstaff, student as mstudent, klas as mklas, device as mdevice
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
        user_cache = {u["userPrincipalName"].split("@")[0].lower(): u for u in entra_users}
        db_students = mstudent.student_get_m()
        found = []
        for student in db_students:
            if student.username.lower() in user_cache:
                student.entra_id = user_cache[student.username.lower()]["id"]
                found.append(student)
        for student in db_students:
            if student not in found:
                log.info(f'{sys._getframe().f_code.co_name}: Student not found in Entra {student.leerlingnummer}, {student.naam} {student.voornaam}')

        found = []
        db_staffs = mstaff.staff_get_m()
        for staff in db_staffs:
            if staff.code.lower() in user_cache:
                staff.entra_id = user_cache[staff.code.lower()]["id"]
                found.append(staff)
        for staff in db_staffs:
            if staff not in found:
                log.info(f'{sys._getframe().f_code.co_name}: Staff not found in Entra {staff.code}, {staff.naam} {staff.voornaam}')

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

            def add_owners_to_add(self, owners):
                if type(owners) is not list:
                    owners = [owners]
                self._owners_to_add += owners

            def add_owners_to_remove(self, owners):
                if type(owners) is not list:
                    owners = [owners]
                self._owners_to_remove += owners

            def add_members_to_add(self, members):
                if type(members) is not list:
                    members = [members]
                self._members_to_add += members

            def add_members_to_remove(self, members):
                if type(members) is not list:
                    members = [members]
                self._members_to_remove += members


        def _check_if_not_empty(dict_list):
            for _, l in dict_list.items():
                if l != []:
                    return True
            return False

        db_klassen = mklas.klas_get_m()
        staff_groep_codes = mstaff.get_groep_codes()
        klassen = {k.klascode: k.klasgroepcode for k in db_klassen}
        klasgroepen = {sgc: list(set([k.klasgroepcode for k in db_klassen])) for sgc in staff_groep_codes}
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto))
        db_cc_teams = {sgc: [dct for dct in db_cc_teams if dct.get_staff_code() == sgc] for sgc in staff_groep_codes}
        new_staffs = mstaff.staff_get_m(("new", "=", True))
        new_staffs = {sgc : [s for s in new_staffs if s.groep_code == sgc ] for sgc in staff_groep_codes}
        delete_staffs = mstaff.staff_get_m(("delete", "=", True))
        delete_staffs = {sgc : [s for s in delete_staffs if s.groep_code == sgc ] for sgc in staff_groep_codes}
        current_staffs = mstaff.staff_get_m([("delete", "=", False), ("new", "=", False)])
        current_staffs = {sgc : [s for s in current_staffs if s.groep_code == sgc ] for sgc in staff_groep_codes}

        delete_cc_teams = []
        new_cc_teams = []
        team_ids = []
        for sgc in staff_groep_codes:
            for cc_team in db_cc_teams[sgc]:
                kgc = cc_team.get_klasgroep_code()
                if kgc in klasgroepen[sgc]:
                    klasgroepen[sgc].remove(kgc)
                else:
                    delete_cc_teams.append(cc_team)
            # deleted klasgroepen
            for cc_team in delete_cc_teams:
                entra.delete_group(cc_team.entra_id)
            mgroup.group_delete_m(groups=delete_cc_teams)
            # new klasgroepen
            for kgc in klasgroepen[sgc]:
                data = {
                    "name": mgroup.Group.get_cc_display_name(sgc, kgc),
                    "description": mgroup.Group.get_cc_description(sgc, kgc),
                    "owners": [current_staffs[sgc][0].entra_id]
                }
                team_id = entra.create_team(data)
                if team_id:
                    team_ids.append((sgc, team_id))
                    new_cc_teams.append({"entra_id": team_id, "display_name": data["name"], "description": data["description"],
                                      "created": datetime.datetime.now(), "type": mgroup.Group.Types.cc_auto, "owners": json.dumps([o.code for o in current_staffs[sgc]])})
        for item in team_ids:
            sgc = item[0]
            team_id = item[1]
            add_persons_data = {"owners": [o.entra_id for o in current_staffs[sgc]], "id": team_id}
            entra.add_persons(add_persons_data)

        mgroup.group_add_m(new_cc_teams)
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto))
        meta_teams = {sgc: {dct.get_klasgroep_code(): MetaTeam(dct) for dct in db_cc_teams if dct.get_staff_code() == sgc} for sgc in staff_groep_codes}

        db_students = mstudent.student_get_m(("new", "=", True))
        for student in db_students:
            if student.klascode in klassen:
                kgc = klassen[student.klascode]
                for staff_groep in staff_groep_codes:
                    meta_teams[staff_groep][kgc].add_members_to_add(student)
            else:
                log.error(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')

        db_students = mstudent.student_get_m(("delete", "=", True))
        for student in db_students:
            if student.klascode in klassen:
                kgc = klassen[student.klascode]
                for staff_groep in staff_groep_codes:
                    if kgc in meta_teams[staff_groep]:
                        meta_teams[staff_groep][kgc].add_members_to_remove(student)
            else:
                log.info(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')

        db_students = mstudent.student_get_m(("changed", "!", ""))
        for student in db_students:
            if "klascode" in student.changed:
                if student.klascode in klassen:
                    kgc = klassen[student.klascode]
                    prev_klascode = json.loads(student.changed_old)["klascode"]
                    prev_klasgroep_code = klassen[prev_klascode] if prev_klascode in klassen else None
                    for staff_groep in staff_groep_codes:
                        meta_teams[staff_groep][kgc].add_members_to_add(student)
                        if prev_klasgroep_code in meta_teams[staff_groep]:
                            meta_teams[staff_groep][prev_klasgroep_code].add_members_to_remove(student)
                else:
                    log.error(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')

        if _check_if_not_empty(new_staffs) or _check_if_not_empty(delete_staffs):
            for sgc, klasgroep_meta_teams in meta_teams.items():
                for kgc, meta_team in klasgroep_meta_teams.items():
                    meta_team.add_owners_to_add(new_staffs[sgc])
                    meta_team.add_owners_to_remove(delete_staffs[sgc])

        for _, klasgroep_meta_teams in meta_teams.items():
            for _, meta_team in klasgroep_meta_teams.items():
                add_persons_data = {"members": [m.entra_id for m in meta_team.get_members_to_add()],
                                    "owners":  [o.entra_id for o in meta_team.get_owners_to_add()],
                                    "id": meta_team.team.entra_id}
                resp = entra.add_persons(add_persons_data)
                if resp:
                    meta_team.team.add_members(meta_team.get_members_to_add())
                    meta_team.team.add_owners(meta_team.get_owners_to_add())

                remove_persons_data = {"members": [m.entra_id for m in meta_team.get_members_to_remove()],
                                       "owners":  [o.entra_id for o in meta_team.get_owners_to_remove()],
                                       "id": meta_team.team.entra_id}
                entra.delete_persons(remove_persons_data)
                meta_team.team.del_members(meta_team.get_members_to_remove())
                meta_team.team.del_owners(meta_team.get_owners_to_remove())
        commit()

    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def cron_sync_devices(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        not_in_entra = []
        entra_devices = entra.get_devices()
        device_cache = {d["id"]: d for d in entra_devices}
        db_devices = mdevice.device_get_m()

        for device in db_devices:
            if device.entra_id in device_cache:
                entra_device = device_cache[device.entra_id]
                device.lastsync_date = entra_device["lastSyncDateTime"]
                del(device_cache[device.entra_id])
            else:
                not_in_entra.append(device)
                log.info(f'{sys._getframe().f_code.co_name}: Device not found in Entra {device.device_name}, {device.user_naam} {device.user_voornaam}')
        mdevice.device_delete_m(devices=not_in_entra)
        new_devices = []
        db_students = mstudent.student_get_m()
        db_staffs = mstaff.staff_get_m()
        db_persons = db_staffs + db_students
        person_cache = {p.entra_id: p for p in db_persons}
        for _, ed in device_cache.items():
            user = None
            if ed["userId"] in person_cache:
                person = person_cache[ed["userId"]]
                user = {
                    "user_voornaam": person.voornaam,
                    "user_naam": person.naam,
                    "user_klascode": person.klascode if isinstance(person, mstudent.Student) else "",
                    "user_username": person.username if isinstance(person, mstudent.Student) else person.code,
                }
            new_device = {
                "entra_id": ed["id"],
                "device_name": ed["deviceName"],
                "serial_number": ed["serialNumber"],
                "enrolled_date": datetime.datetime.strptime(ed["enrolledDateTime"], "%Y-%m-%dT%H:%M:%SZ"),
                "lastsync_date": datetime.datetime.strptime(ed["lastSyncDateTime"], "%Y-%m-%dT%H:%M:%SZ"),
                "user_entra_id": ed["userId"],
            }
            if user:
                new_device.update(user)
            new_devices.append(new_device)
        mdevice.device_add_m(new_devices)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')





