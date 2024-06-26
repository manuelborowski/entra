import sys, datetime, json, re, copy
from app.data import group as mgroup, staff as mstaff, student as mstudent, klas as mklas, device as mdevice
from app.data.group import Group
from app.data.models import add, commit, delete
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

    def append_owners_to_add(self, owners):
        if type(owners) is not list:
            owners = [owners]
        self._owners_to_add += owners

    def append_owners_to_remove(self, owners):
        if type(owners) is not list:
            owners = [owners]
        self._owners_to_remove += owners

    def append_members_to_add(self, members):
        if type(members) is not list:
            members = [members]
        self._members_to_add += members

    def append_members_to_remove(self, members):
        if type(members) is not list:
            members = [members]
        self._members_to_remove += members


def _update_entra_cc_teams(teams):
    try:
        for team in teams:
            # update in entra
            add_persons_data = {"members": [m.entra_id for m in team.get_members_to_add()],
                                "owners": [o.entra_id for o in team.get_owners_to_add()],
                                "id": team.team.entra_id}
            resp = entra.add_persons(add_persons_data)
            if resp:
                if add_persons_data["members"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team.description}, added students {[f"{m.leerlingnummer}, {m.naam} {m.voornaam}" for m in team.get_members_to_add()]}')
                if add_persons_data["owners"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team.description}, added staff {[m.code for m in team.get_owners_to_add()]}')
                # update in database
                team.team.add_members(team.get_members_to_add())
                team.team.add_owners(team.get_owners_to_add())

            # update in entra
            remove_persons_data = {"members": [m.entra_id for m in team.get_members_to_remove()],
                                   "owners": [o.entra_id for o in team.get_owners_to_remove()],
                                   "id": team.team.entra_id}
            resp = entra.delete_persons(remove_persons_data)
            if resp:
                if remove_persons_data["members"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team.description}, deleted students {[f"{m.leerlingnummer}, {m.naam}{m.voornaam}" for m in team.get_members_to_remove()]}')
                if remove_persons_data["owners"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team.description}, deleted staff {[m.code for m in team.get_owners_to_remove()]}')
            # update in database
            team.team.del_members(team.get_members_to_remove())
            team.team.del_owners(team.get_owners_to_remove())
        commit()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


#Sync classroomcloud auto-teams, i.e. which are automatically created from klassen, klasgroepen, studenten en staff from SDH
# for all classes in the students table, create a team, add the students as members and add all teachers as owners.
def cron_sync_cc_auto_teams(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        def _check_if_not_empty(dict_list):
            for _, l in dict_list.items():
                if l != []:
                    return True
            return False

        # groups::description: cc-b-3BO1, where "b" is staff-groep-code and 3B01 is klasgroep-code
        db_klassen = mklas.klas_get_m()
        klassen = {k.klascode: k.klasgroepcode for k in db_klassen} # {"1Aa": "1A", "1Ab": "1A", ...}
        staff_groep_codes = mstaff.get_groep_codes() # ["a", "b", ...]
        klasgroepen = {sgc: list(set([k.klasgroepcode for k in db_klassen])) for sgc in staff_groep_codes} # ["a": ["1A", "1B"...], "b": ["1A", "1B"...], ..}
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto))
        db_cc_teams = {sgc: [dct for dct in db_cc_teams if dct.get_staff_code() == sgc] for sgc in staff_groep_codes} # ["a": [groups[12], groups[1],...], "b": [groups[12], groups[1],...],...}
        new_staffs = mstaff.staff_get_m(("new", "=", True))
        new_staffs = {sgc : [s for s in new_staffs if s.groep_code == sgc ] for sgc in staff_groep_codes} # ["b": [staff[123]], "e": [staff[125]]
        delete_staffs = mstaff.staff_get_m(("delete", "=", True))
        delete_staffs = {sgc : [s for s in delete_staffs if s.groep_code == sgc ] for sgc in staff_groep_codes} # ["a": [staff[12]], "c": [staff[83]]
        current_staffs = mstaff.staff_get_m([("delete", "=", False), ("new", "=", False)]) # [staff[1], staff[2], ...]
        current_staffs = {sgc : [s for s in current_staffs if s.groep_code == sgc ] for sgc in staff_groep_codes} # {"a": [staff[1], staff[2], ...], "b": [staff[47], ..], ...}

        delete_cc_teams = []
        new_cc_teams = []
        team_ids = []
        for sgc in staff_groep_codes:
            # check if a cc-team is still needed (i.e. klasgroep still exists), else put in delete-list
            for cc_team in db_cc_teams[sgc]:
                kgc = cc_team.get_klasgroep_code()
                if kgc in klasgroepen[sgc]:
                    klasgroepen[sgc].remove(kgc)
                else:
                    delete_cc_teams.append(cc_team)
            # deleted klasgroepen: delete in database and in entra
            for cc_team in delete_cc_teams:
                entra.delete_group(cc_team.entra_id)
            mgroup.group_delete_m(groups=delete_cc_teams)
            # new klasgroepen, i.e. not in database or entra yet
            for kgc in klasgroepen[sgc]:
                data = {
                    "name": mgroup.Group.get_cc_display_name(sgc, kgc),
                    "description": mgroup.Group.get_cc_description(sgc, kgc),
                    "owners": [current_staffs[sgc][0].entra_id]
                }
                # Create new team in entra, with default owner (first one in the list of staff)
                team_id = entra.create_team(data)
                if team_id:
                    team_ids.append((sgc, team_id)) # [("a", "234zé234é"), ("b", "23423zf"), ...]
                    new_cc_teams.append({"entra_id": team_id, "display_name": data["name"], "description": data["description"],
                                      "created": datetime.datetime.now(), "type": mgroup.Group.Types.cc_auto, "owners": json.dumps([o.code for o in current_staffs[sgc]])})
        # for the newly created teams, add all staff (per staff-groep-code) as owner
        for item in team_ids:
            sgc = item[0]
            team_id = item[1]
            add_persons_data = {"owners": [o.entra_id for o in current_staffs[sgc]], "id": team_id}
            entra.add_persons(add_persons_data)

        # save new teams/groups in database
        mgroup.group_add_m(new_cc_teams)
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto)) # reload the cc-teams (clean list)
        meta_teams = {sgc: {dct.get_klasgroep_code(): MetaTeam(dct) for dct in db_cc_teams if dct.get_staff_code() == sgc} for sgc in staff_groep_codes}
        # { "a": {"1A": MetaTeam(1A, a), "1B": MetaTeam(1B, a), ...}, "b": {"1A": MetaTeam(1A, b), ...}, ...}

        # new students, append them to the appropriate meta_team objects add-list (MetaTeam::append_member_to_add), i.e. once for every staff-groep-code
        db_students = mstudent.student_get_m(("new", "=", True))
        for student in db_students:
            if student.klascode in klassen:
                kgc = klassen[student.klascode]
                for staff_groep_code in staff_groep_codes:
                    meta_teams[staff_groep_code][kgc].append_members_to_add(student)
            else:
                log.error(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')

        # deleted students, append them to the appropriate meta_team objects remove-list (MetaTeam::append_member_to_remove), i.e. once for every staff-groep-code
        db_students = mstudent.student_get_m(("delete", "=", True))
        for student in db_students:
            if student.klascode in klassen:
                kgc = klassen[student.klascode]
                for staff_groep_code in staff_groep_codes:
                    if kgc in meta_teams[staff_groep_code]:
                        meta_teams[staff_groep_code][kgc].append_members_to_remove(student)
            else:
                log.info(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')


        # students that changed klas, append them to the meta_team objects add-list (MetaTeam::append_member_to_add), for the new klas
        # and append them to the meta_team objects remove-list (MetaTeam::append_member_to_remove), for the previous klas
        db_students = mstudent.student_get_m(("changed", "!", ""))
        for student in db_students:
            if "klascode" in student.changed:
                if student.klascode in klassen:
                    kgc = klassen[student.klascode]
                    prev_klascode = json.loads(student.changed_old)["klascode"]
                    prev_klasgroep_code = klassen[prev_klascode] if prev_klascode in klassen else None
                    for staff_groep_code in staff_groep_codes:
                        meta_teams[staff_groep_code][kgc].append_members_to_add(student)
                        if prev_klasgroep_code in meta_teams[staff_groep_code]:
                            meta_teams[staff_groep_code][prev_klasgroep_code].append_members_to_remove(student)
                else:
                    log.error(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')

        # append new staff to the meta_team objects add-list (MetaTeam::append_owner_to_add)
        # append deleted staff to the meta_team objects remove-list (MetaTeam::append_owner_to_remove)
        if _check_if_not_empty(new_staffs) or _check_if_not_empty(delete_staffs):
            for sgc, klasgroep_meta_teams in meta_teams.items():
                for kgc, meta_team in klasgroep_meta_teams.items():
                    meta_team.append_owners_to_add(new_staffs[sgc])
                    meta_team.append_owners_to_remove(delete_staffs[sgc])

        # at this point, the meta_teams are up-to-date, i.e. they contain, if appropriate, lists of owners/members to be added to or removed from the team
        team_list = [t for _, sg in meta_teams.items() for _, t in sg.items()]
        _update_entra_cc_teams(team_list)

    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# Verify if all teachers and students are in the correct cc-teams
def cron_verify_cc_auto_teams(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        # groups::description: cc-b-3BO1, where "b" is staff-groep-code and 3B01 is klasgroep-code
        db_klassen = mklas.klas_get_m()
        db_klasgroep_klassen = {k.klascode: k.klasgroepcode for k in db_klassen} # {"1Aa": "1A", "1Ab": "1A", ...}
        klassen = [k.klascode for k in db_klassen] # ["1Aa", "1Ab", ...]
        staff_groep_codes = mstaff.get_groep_codes() # ["a", "b", ...]
        klasgroepen = list(set([k.klasgroepcode for k in db_klassen]))  # ["1A", "1B", "7LOG", ... ]
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto))
        db_description_cc_teams = {t.description: t for t in db_cc_teams} # {"cc-a-3E": groups[12], "cc-e-7MT": "groups[1], ...}
        staffs = mstaff.staff_get_m() # [staff[1], staff[2], ...]
        code2staffs = {s.code: s for s in staffs}
        id2staff = {s.entra_id: s for s in staffs}
        students = mstudent.student_get_m() # [student[1], student[2], ...]
        id2student = {s.entra_id: s for s in students}
        leerlingnummer2student = {s.leerlingnummer: s for s in students}

        # Delete double entries in owners field (only once)
        # for db_cc_team in db_cc_teams:
        #     db_cc_team.owners = json.dumps(list(set(json.loads(db_cc_team.owners))))

        # Check if all staffs are present in the cc-teams
        log.info(f"{sys._getframe().f_code.co_name}, Check if all staff are present in DB teams")
        for staff in staffs:
            for klasgroep in klasgroepen:
                description = f"cc-{staff.groep_code}-{klasgroep}"
                if description in db_description_cc_teams:
                    if staff.code not in db_description_cc_teams[description].owners:
                        log.error(f'{sys._getframe().f_code.co_name}: staff {staff.code} NOT found in DB cc-team {description}')
                        owners = json.loads(db_description_cc_teams[description].owners)
                        owners.append(staff.code)
                        db_description_cc_teams[description].owners = json.dumps(owners)
                else:
                    log.error(f'{sys._getframe().f_code.co_name}: cc-team {description} NOT found in ENTRA')
        log.info(f'{sys._getframe().f_code.co_name}: processed {len(staffs)} nbr of staff')

        # Check if all students are present in the cc-teams
        log.info(f"{sys._getframe().f_code.co_name}, Check if all students are present in DB teams")
        for student in students:
            for staff_groep_code in staff_groep_codes:
                description = f"cc-{staff_groep_code}-{db_klasgroep_klassen[student.klascode]}"
                if description in db_description_cc_teams:
                    if student.leerlingnummer not in db_description_cc_teams[description].members:
                        log.error(f'{sys._getframe().f_code.co_name}: student {student.leerlingnummer}, {student.naam} {student.voornaam} NOT found in DB cc-team {description}')
                        members = json.loads(db_description_cc_teams[description].members)
                        members.append(student.leerlingnummer)
                        db_description_cc_teams[description].members = json.dumps(members)
                else:
                    log.error(f'{sys._getframe().f_code.co_name}: cc-team {description} NOT found in ENTRA')
        log.info(f'{sys._getframe().f_code.co_name}: processed {len(students)} nbr of students')

        # find obsolete teams in database (based on staff-group-code and klasgroepcode)
        log.info(f"{sys._getframe().f_code.co_name}, Find obsolete teams in DB")
        for staff_groep_code in staff_groep_codes:
            for klasgroep in klasgroepen:
                description = f"cc-{staff_groep_code}-{klasgroep}"
                if description in db_description_cc_teams:
                    del(db_description_cc_teams[description])
        for description, team in db_description_cc_teams.items():
            log.error(f'{sys._getframe().f_code.co_name}: cc-team {description} NOT found in database')
            delete(team)
        commit()

        # clean up owners and members of the teams
        log.info(f"{sys._getframe().f_code.co_name}, Remove, from teams in DB, nonexisting staff en students")
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto))
        for db_team in db_cc_teams:
            owners = json.loads(db_team.owners)
            new_owners = []
            for code in owners:
                if code in code2staffs:
                    new_owners.append(code)
                else:
                    log.error(f'{sys._getframe().f_code.co_name}: {db_team.description}, staff {code} is not present in DB')
            db_team.owners = json.dumps(sorted(new_owners))

            students = json.loads(db_team.members)
            new_students = []
            for leerlingnummer in students:
                if leerlingnummer in leerlingnummer2student:
                    new_students.append(leerlingnummer)
                else:
                    log.error(f'{sys._getframe().f_code.co_name}: {db_team.description}, student {leerlingnummer} is not present in DB')
            db_team.students = json.dumps(sorted(new_students))
        commit()

        log.info(f"{sys._getframe().f_code.co_name}, Sync teams in Entra with DB")
        group_ctr = 0
        team_list = []
        for db_cc_team in db_cc_teams:
            group_ctr += 1
            if group_ctr % 500 == 0:
                log.info(f'{sys._getframe().f_code.co_name}: processed {group_ctr} teams')
            db_owners = json.loads(db_cc_team.owners)
            db_members = json.loads(db_cc_team.members)
            entra_team_members = entra.get_team_members(db_cc_team.entra_id)
            meta_team = MetaTeam(db_cc_team)
            for member_data in entra_team_members["value"]:
                id = member_data["id"]
                if member_data["officeLocation"] in klassen:
                    if id in id2student:
                        student = id2student[id]
                        if student.leerlingnummer in db_members:
                            db_members.remove(student.leerlingnummer)
                        else:
                            log.error(f'{sys._getframe().f_code.co_name}: Entra student {student.leerlingnummer}, {student.naam} {student.voornaam} NOT found in DB team {db_cc_team.description}')
                            meta_team.append_members_to_remove(student)
                    else:
                        log.error(f'{sys._getframe().f_code.co_name}: Entra student {id} NOT found in DB')
                else:
                    if id in id2staff:
                        staff = id2staff[id]
                        if staff.code in db_owners:
                            db_owners.remove(staff.code)
                        else:
                            log.error(f'{sys._getframe().f_code.co_name}: Entra staff {staff.code}, {staff.naam} {staff.voornaam} NOT found in DB team {db_cc_team.description}')
                            meta_team.append_owners_to_remove(staff)
                    else:
                        log.error(f'{sys._getframe().f_code.co_name}: Entra staff {id} NOT found in DB')
            for code in db_owners:
                staff = code2staffs[code]
                meta_team.append_owners_to_add(staff)
                log.error(f'{sys._getframe().f_code.co_name}: DB staff {staff.code} NOT found in Entra team {db_cc_team.description}')
            for leerlingnummer in db_members:
                student = leerlingnummer2student[leerlingnummer]
                meta_team.append_members_to_add(student)
                log.error(f'{sys._getframe().f_code.co_name}: DB student {student.leerlingnummer}, {student.naam} {student.voornaam} NOT found in Entra team {db_cc_team.description}')
            team_list.append(meta_team)
        _update_entra_cc_teams(team_list)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def cron_sync_devices(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        entra_devices = entra.get_devices()
        device_cache = {d["id"]: d for d in entra_devices}
        db_devices = mdevice.device_get_m()

        db_students = mstudent.student_get_m()
        db_staffs = mstaff.staff_get_m()
        db_persons = db_staffs + db_students
        person_cache = {p.entra_id: p for p in db_persons}

        # process the active devices (deleted or changed) of a user.
        not_in_entra = []
        for dd in db_devices:
            if dd.intune_id in device_cache:
                intune_device = device_cache[dd.intune_id]
                lastsync_date = intune_device["lastSyncDateTime"]
                if lastsync_date[0] == "0":
                    lastsync_date = "2000-01-01T00:00:00Z"
                dd.lastsync_date = datetime.datetime.strptime(lastsync_date, "%Y-%m-%dT%H:%M:%SZ")
                enrolled_date = intune_device["enrolledDateTime"]
                if enrolled_date[0] == "0":
                    enrolled_date = "2000-01-01T00:00:00Z"
                dd.enrolled_date = datetime.datetime.strptime(enrolled_date, "%Y-%m-%dT%H:%M:%SZ")
                person_entra_id = intune_device["userId"]
                if person_entra_id in person_cache:
                    person = person_cache[person_entra_id]
                    person.computer_lastsync_date = dd.lastsync_date
                    person.computer_name = dd.device_name
                    person.computer_intune_id = dd.intune_id
                    dd.user_entra_id = person_entra_id
                    dd.user_voornaam = person.voornaam,
                    dd.user_naam = person.naam
                    dd.user_klascode = person.klascode if isinstance(person, mstudent.Student) else "",
                    dd.user_username = person.username if isinstance(person, mstudent.Student) else person.code,
                del(device_cache[dd.intune_id])
            else:
                not_in_entra.append(dd)
                log.info(f'{sys._getframe().f_code.co_name}: Active device not found in Entra {dd.device_name}, {dd.user_naam} {dd.user_voornaam}')
        mdevice.device_delete_m(devices=not_in_entra)
        log.info(f"{sys._getframe().f_code.co_name}, deleted, active devices {len(not_in_entra)}")

        # process the non-active devices (deleted or changed) of a user
        not_in_entra = []
        db_devices = mdevice.device_get_m(active=False)
        for dd in db_devices:
            if dd.intune_id in device_cache:
                del(device_cache[dd.entra_id])
            else:
                not_in_entra.append(dd)
                log.info(f'{sys._getframe().f_code.co_name}: Non-active device not found in Entra {dd.device_name}, {dd.user_naam} {dd.user_voornaam}')
        mdevice.device_delete_m(devices=not_in_entra)
        log.info(f"{sys._getframe().f_code.co_name}, deleted, non-active devices {len(not_in_entra)}")

        new_devices = []
        for _, ed in device_cache.items():
            new_device = {
                "intune_id": ed["id"],
                "entra_id": ed["azureADDeviceId"],
                "device_name": ed["deviceName"],
                "serial_number": ed["serialNumber"],
                "user_entra_id": ed["userId"],
            }
            person = None
            if ed["userId"] in person_cache:
                person = person_cache[ed["userId"]]
                new_device.update({
                    "user_voornaam": person.voornaam,
                    "user_naam": person.naam,
                    "user_klascode": person.klascode if isinstance(person, mstudent.Student) else "",
                    "user_username": person.username if isinstance(person, mstudent.Student) else person.code,
                })

            if ed["complianceState"] != "compliant" or ed["deviceEnrollmentType"] == "windowsAutoEnrollment":
                # non-active device
                lastsync_date = None
                enrolled_date = None
                new_device.update({"active": False})
            else:
                # active device
                lastsync_date = ed["lastSyncDateTime"]
                if lastsync_date[0] == "0":
                    lastsync_date = "2000-01-01T00:00:00Z"
                lastsync_date = datetime.datetime.strptime(lastsync_date, "%Y-%m-%dT%H:%M:%SZ")
                enrolled_date = ed["enrolledDateTime"]
                if enrolled_date[0] == "0":
                    enrolled_date = "2000-01-01T00:00:00Z"
                enrolled_date = datetime.datetime.strptime(enrolled_date, "%Y-%m-%dT%H:%M:%SZ")
                if person:
                    person.computer_lastsync_date = lastsync_date
                    person.computer_name = ed["deviceName"]
                    person.computer_intune_id = ed["id"]

            new_device.update({"enrolled_date": enrolled_date, "lastsync_date": lastsync_date,})
            new_devices.append(new_device)

        mdevice.device_add_m(new_devices)
        log.info(f"{sys._getframe().f_code.co_name}, new devices {len(new_devices)}")
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')





