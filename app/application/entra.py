import sys, datetime, json, re, copy

from app.application.sdh import log
from app.data import group as mgroup, staff as mstaff, student as mstudent, klas as mklas, device as mdevice
from app.data.group import Group
from app.data.models import add, commit, delete
from app.data.entra import entra

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, flask_app
from app.data.utils import get_current_schoolyear

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
                if "cc-" in group["description"]:
                    log.error(f'{sys._getframe().f_code.co_name}: group {group["description"]} in entra but not in database')
                    continue
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
        not_found = []
        for staff in db_staffs:
            if staff not in found:
                log.info(f'{sys._getframe().f_code.co_name}: Staff not found in Entra {staff.code}, {staff.naam} {staff.voornaam}, remove from database')
                not_found.append(staff)
        mstaff.staff_delete_m(staffs=not_found)

        commit()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# team can be a team-object (from the database) or just a team-id (uuid)
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

    def __str__(self):
        return self.team.display_name


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
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team.description}, deleted students {[f"{m.leerlingnummer}, {m.naam} {m.voornaam}" for m in team.get_members_to_remove()]}')
                if remove_persons_data["owners"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team.description}, deleted staff {[m.code for m in team.get_owners_to_remove()]}')
            # update in database
            team.team.del_members(team.get_members_to_remove())
            team.team.del_owners(team.get_owners_to_remove())
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def _update_entra_non_cc_teams(teams):
    try:
        for team in teams:
            # update in entra
            add_persons_data = {"members": [m.entra_id for m in team.get_members_to_add()],
                                "owners": [o.entra_id for o in team.get_owners_to_add()],
                                "id": team.team["id"]}
            resp = entra.add_persons(add_persons_data)
            if resp:
                if add_persons_data["members"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team["name"]}, added students {[f"{m.leerlingnummer}, {m.naam} {m.voornaam}" for m in team.get_members_to_add()]}')
                if add_persons_data["owners"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team["name"]}, added staff {[m.code for m in team.get_owners_to_add()]}')

            # update in entra
            remove_persons_data = {"members": [m.entra_id for m in team.get_members_to_remove()],
                                   "owners": [o.entra_id for o in team.get_owners_to_remove()],
                                   "id": team.team["id"]}
            resp = entra.delete_persons(remove_persons_data)
            if resp:
                if remove_persons_data["members"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team["name"]}, deleted students {[f"{m.leerlingnummer}, {m.naam} {m.voornaam}" for m in team.get_members_to_remove()]}')
                if remove_persons_data["owners"] != []:
                    log.info(f'{sys._getframe().f_code.co_name}: Team {team.team["name"]}, deleted staff {[m.code for m in team.get_owners_to_remove()]}')
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

        # Very exceptional, a sgc in current_staffs can be empty, e.g. sgc "f" is empty because in the database, all the staff of this sgc are marked new, i.e. they're
        # in new_staffs.  But nevertheless sgc does exist (in staff_groep_codes) because it contains staff members in the database.
        # If this happens, move one staff member of new_staffs (from the corresponding sgc) to current_staffs.
        # Since this cron task is after "sync-users-from-entra" it is certain said staff has a valid entra-id.
        for sgc, staffs in current_staffs.items():
            if not staffs and new_staffs[sgc]:
                # find staff with valid entra id
                staffs_with_entra_id = list(filter(lambda x: x.entra_id != "", new_staffs[sgc]))
                if staffs_with_entra_id:
                    staffs.append(staffs_with_entra_id[0])
                    new_staffs[sgc].pop(new_staffs[sgc].index(staffs_with_entra_id[0]))
                else:
                    log.error(f'{sys._getframe().f_code.co_name}: new_staffs[{sgc}] has no valid staff (with entra-id)')

        delete_cc_teams = []
        new_cc_teams = []
        team_ids = []
        for sgc in staff_groep_codes: # a, b, c, ...
            # check if a cc-team is still needed (i.e. klasgroep still exists), else put in delete-list
            for cc_team in db_cc_teams[sgc]: # 1A, 1B, ...
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
                    mgroup.group_add({"entra_id": team_id, "display_name": data["name"], "description": data["description"],
                                      "created": datetime.datetime.now(), "type": mgroup.Group.Types.cc_auto, "owners": json.dumps([o.code for o in current_staffs[sgc]])})
        # for the newly created teams, add all staff (per staff-groep-code) as owner
        for item in team_ids:
            sgc = item[0]
            team_id = item[1]
            add_persons_data = {"owners": [o.entra_id for o in current_staffs[sgc]], "id": team_id}
            entra.add_persons(add_persons_data)

        # iterate over all students, retrieve all the teams a student belong to, add to or delete from a team depending on klascode
        # and current schoolyear
        db_cc_teams = mgroup.group_get_m(("type", "=", mgroup.Group.Types.cc_auto)) # reload the cc-teams (clean list)
        db_cc_meta_teams = [MetaTeam(t) for t in db_cc_teams]
        sgc_meta_teams = {sgc: {dct.team.get_klasgroep_code(): dct for dct in db_cc_meta_teams if dct.team.get_staff_code() == sgc} for sgc in staff_groep_codes}
        # { "a": {"1A": MetaTeam(1A, a), "1B": MetaTeam(1B, a), ...}, "b": {"1A": MetaTeam(1A, b), ...}, ...}
        id_meta_teams = {mt.team.entra_id: mt for mt in db_cc_meta_teams}
        nbr_processed = 0
        delete_student_from_meta_teams = {}
        current_schoolyear = get_current_schoolyear(format=3)

        def __get_meta_team(team):
            id = team["id"]
            if id not in delete_student_from_meta_teams:
                delete_student_from_meta_teams[id] = MetaTeam(team)
            return delete_student_from_meta_teams[id]

        # Check for active students if they're in the correct team
        db_students = mstudent.student_get_m()
        for student in db_students:
            entra_teams = entra.get_user_teams(student.entra_id) # get list of teams from entra
            student_found_in_cc_team = [] #a list of staff-group-codes the student is a member of
            if student.klascode in klassen:
                kgc = klassen[student.klascode]
            else:
                log.error(f'{sys._getframe().f_code.co_name}: klascode {student.klascode} not found in klassentable')
                continue
            for entra_team in entra_teams:
                if entra_team["name"][:3] == "cc-":
                    # it is a classroomcloud team
                    if kgc in entra_team["name"]:
                        # student already in correct CLC team
                        student_found_in_cc_team.append(entra_team["name"][3]) # student found in cc-team with given staff-group-code
                    else:
                        # student in different CLC team
                        if entra_team["id"] in id_meta_teams:
                            # entra team is also present in database
                            id_meta_teams[entra_team["id"]].append_members_to_remove(student)
                        else:
                            # entra team is not in database, create separate list
                            __get_meta_team(entra_team).append_members_to_remove(student)
                elif entra_team["name"][:3] == "[20" and current_schoolyear not in entra_team["name"]:
                    # remove student from archived team
                    __get_meta_team(entra_team).append_members_to_remove(student)
            for sgc in staff_groep_codes:
                if sgc not in student_found_in_cc_team:
                    # student should be member of team with given staff-group-code, but is not, so add student to given meta team.
                    sgc_meta_teams[sgc][kgc].append_members_to_add(student)
            nbr_processed += 1
            if nbr_processed % 100 == 0:
                log.info(f'{sys._getframe().f_code.co_name}: from ENTRA, check active student team-membership, processed students: {nbr_processed} ')

        # Disabled, there are a lot of duplicated students in the database (left and came back).  This disturbs following code
        # Check for deactived students if they're still in teams.  If so, remove them
        # nbr_processed = 0
        # db_deactivated_students = mstudent.student_get_m(active=False)
        # for student in db_deactivated_students:
        #     entra_teams = entra.get_user_teams(student.entra_id)
        #     for entra_team in entra_teams:
        #         if entra_team["id"] in id_meta_teams:
        #             id_meta_teams[entra_team["id"]].append_members_to_remove(student)
        #         else:
        #             __get_meta_team(entra_team).append_members_to_remove(student)
        #     nbr_processed += 1
        #     if nbr_processed % 100 == 0:
        #         log.info(f'{sys._getframe().f_code.co_name}: from ENTRA, check deactived student, remove from teams, processed students: {nbr_processed} ')

        # append new staff to the meta_team objects add-list (MetaTeam::append_owner_to_add)
        # append deleted staff to the meta_team objects remove-list (MetaTeam::append_owner_to_remove)
        if _check_if_not_empty(new_staffs) or _check_if_not_empty(delete_staffs):
            for sgc, klasgroep_meta_teams in sgc_meta_teams.items():
                for kgc, meta_team in klasgroep_meta_teams.items():
                    meta_team.append_owners_to_add(new_staffs[sgc])
                    meta_team.append_owners_to_remove(delete_staffs[sgc])

        # at this point, sgc_meta_teams contain teams with staff (to be added or deleted) or students (to be added or removed )
        team_list = [t for _, sg in sgc_meta_teams.items() for _, t in sg.items()]
        _update_entra_cc_teams(team_list)

        # delete_student_meta_teams, if not empty, contains team-ids (non-cc-teams) and student-ids of students to be deleted from said teams
        # TO DO: skip for now, this function assumes students are always a member of a team, never an owner.  Many teams are made by students, who are owner.
        # team_list = delete_student_from_meta_teams.values()
        # _update_entra_non_cc_teams(team_list)
        commit()

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
        # mark devices, of certain groups, that may not be deleted
        entra_do_not_delete_groups = flask_app.config["DO_NOT_DELETE_DEVICE_ENTRA_GROUPS"]
        entra_do_not_delete_devices = [dev["id"] for grp in [entra.get_group_members(id) for id in entra_do_not_delete_groups] for dev in grp]

        intune_devices = entra.intune_get_devices()
        intune_device_cache = {d["id"]: d for d in intune_devices}
        autopilot_devices = entra.autopilot_get_devices()
        autopilot_device_cache = {d["managedDeviceId"]: d for d in autopilot_devices} # key is intune id
        entra_devices = entra.entra_get_devices()
        entra_device_cache = {d["deviceId"]: d["id"] for d in entra_devices} # key is azureADDeviceId, value is entra object id
        db_devices = mdevice.device_get_m(active=None) # active and non active devices
        db_device_cache = {d.intune_id: d for d in db_devices}

        db_students = mstudent.student_get_m()
        db_staffs = mstaff.staff_get_m()
        db_users = db_staffs + db_students
        user_cache = {p.entra_id: p for p in db_users}

        user_devices = {} # {user-entra-id: [device#1, device#2, ... ], ...}

        def __update_user_devices(user, device):
            if user in user_devices:
                user_devices[user].append(device)
            else:
                user_devices[user] = [device]

        # process the active devices (deleted or changed) of a user.
        not_in_entra = []
        for dd in db_devices:
            if dd.intune_id in intune_device_cache:
                intune_device = intune_device_cache[dd.intune_id]
                lastsync_date = intune_device["lastSyncDateTime"]
                if lastsync_date[0] == "0":
                    lastsync_date = "2000-01-01T00:00:00Z"
                dd.lastsync_date = datetime.datetime.strptime(lastsync_date, "%Y-%m-%dT%H:%M:%SZ")
                enrolled_date = intune_device["enrolledDateTime"]
                if enrolled_date[0] == "0":
                    enrolled_date = "2000-01-01T00:00:00Z"
                dd.enrolled_date = datetime.datetime.strptime(enrolled_date, "%Y-%m-%dT%H:%M:%SZ")
                dd.do_not_delete = dd.entra_id in entra_do_not_delete_devices
                __update_user_devices(dd.user_entra_id, dd)
                del(intune_device_cache[dd.intune_id])
            else:
                not_in_entra.append(dd)
                log.info(f'{sys._getframe().f_code.co_name}: device not found in Intune {dd.device_name}, {dd.user_naam} {dd.user_voornaam}')
        mdevice.device_delete_m(devices=not_in_entra)
        log.info(f"{sys._getframe().f_code.co_name}, deleted devices {len(not_in_entra)}")

        # new devices
        new_devices = []
        for _, intune_device in intune_device_cache.items():
            lastsync_date = intune_device["lastSyncDateTime"]
            if lastsync_date[0] == "0":
                lastsync_date = "2000-01-01T00:00:00Z"
            lastsync_date = datetime.datetime.strptime(lastsync_date, "%Y-%m-%dT%H:%M:%SZ")
            enrolled_date = intune_device["enrolledDateTime"]
            if enrolled_date[0] == "0":
                enrolled_date = "2000-01-01T00:00:00Z"
            enrolled_date = datetime.datetime.strptime(enrolled_date, "%Y-%m-%dT%H:%M:%SZ")
            autopilot_id = autopilot_device_cache[intune_device["id"]]["id"] if intune_device["id"] in autopilot_device_cache else None
            entra_id = entra_device_cache[intune_device["azureADDeviceId"]] if intune_device["azureADDeviceId"] in entra_device_cache else None
            new_device = {
                "intune_id": intune_device["id"],
                "entra_id": entra_id,
                "autopilot_id": autopilot_id,
                "device_name": intune_device["deviceName"],
                "serial_number": intune_device["serialNumber"],
                "user_entra_id": intune_device["userId"],
                "enrolled_date": enrolled_date,
                "lastsync_date": lastsync_date,
                "active": False,
                "do_not_delete": entra_id in entra_do_not_delete_devices
            }
            new_devices.append(new_device)

        db_new_devices = mdevice.device_add_m(new_devices)
        log.info(f"{sys._getframe().f_code.co_name}, new devices {len(new_devices)}")

        for dd in db_new_devices:
            __update_user_devices(dd.user_entra_id, dd)

        #for all users, update most-recent-used device, i.e. check enrolled_date
        for user_id, devices in user_devices.items():
            if user_id not in user_cache:
                continue
            user = user_cache[user_id]
            if user.computer_lastsync_date == None:
                user.computer_lastsync_date = datetime.datetime(2000, 1, 1)

            last_enrolled_date = datetime.datetime(2000, 1, 1)
            last_enrolled_device = None
            for device in devices:
                device.active = False # default
                if device.enrolled_date >= last_enrolled_date:
                    last_enrolled_date = device.enrolled_date
                    last_enrolled_device = device
            if last_enrolled_device:
                last_enrolled_device.active = True
                user.computer_lastsync_date = last_enrolled_device.lastsync_date
                user.computer_intune_id = last_enrolled_device.intune_id
                user.computer_name = last_enrolled_device.device_name
        mdevice.commit()
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def cron_cleanup_db(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        db_students = mstudent.student_get_m(("changed", "!", ""))
        db_students += mstudent.student_get_m(("new", "=", True))
        for student in db_students:
            student.new = False
            student.changed = ""
            student.changed_old = ""
        mstudent.commit()
        db_students = mstudent.student_get_m(("delete", "=", True), active=False)
        mstudent.student_delete_m(students=db_students)

        db_staffs = mstaff.staff_get_m(("changed", "!", ""))
        db_staffs += mstaff.staff_get_m(("new", "=", True))
        for staff in db_staffs:
            staff.new = False
            staff.changed = ""
            staff.changed_old = ""
        mstaff.commit()
        db_staffs = mstaff.staff_get_m(("delete", "=", True))
        mstaff.staff_delete_m(staffs=db_staffs)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')

