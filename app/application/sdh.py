from app.data import student as mstudent, staff as mstaff, klas as mklas
import sys, requests, json
from app import flask_app
#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())



def cron_student_load_from_sdh(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    updated_students = []
    nbr_updated = 0
    new_students = []
    try:
        db_students = mstudent.student_get_m()
        db_leerlingnummer_to_student = {s.leerlingnummer: s for s in db_students} if db_students else {}
        sdh_student_url = flask_app.config["SDH_GET_STUDENT_URL"]
        sdh_key = flask_app.config["SDH_GET_KEY"]

        # check for new and updated students
        res = requests.get(sdh_student_url, headers={'x-api-key': sdh_key})
        if res.status_code == 200:
            sdh_students = res.json()
            if sdh_students['status']:
                log.info(f'{sys._getframe().f_code.co_name}, retrieved {len(sdh_students["data"])} students from SDH')
                for sdh_student in sdh_students["data"]:
                    if int(sdh_student["leerlingnummer"]) < 0: continue
                    if sdh_student["leerlingnummer"] in db_leerlingnummer_to_student:
                        # check for changed rfid or classgroup
                        db_student = db_leerlingnummer_to_student[sdh_student["leerlingnummer"]]
                        update = {}
                        changed_old = {}
                        if db_student.klascode != sdh_student["klascode"]:
                            update["klascode"] = sdh_student["klascode"]
                            changed_old["klascode"] = db_student.klascode
                        if db_student.klasnummer != sdh_student["klasnummer"]:
                            update["klasnummer"] = sdh_student["klasnummer"]
                            changed_old["klasnummer"] = db_student.klasnummer
                        if update:
                            update.update({"student": db_student, "changed_old": changed_old, "changed": list(changed_old.keys())})
                            updated_students.append(update)
                            log.info(f'{sys._getframe().f_code.co_name}, Update student {db_student.leerlingnummer}, update {update}')
                            nbr_updated += 1
                        del(db_leerlingnummer_to_student[sdh_student["leerlingnummer"]])
                    else:
                        new_students.append({"leerlingnummer": sdh_student["leerlingnummer"], "klascode": sdh_student["klascode"], "naam": sdh_student["naam"],
                                             "voornaam": sdh_student["voornaam"], "klasnummer": sdh_student["klasnummer"], "username": sdh_student["username"],
                                             "new": True})
                        log.info(f'{sys._getframe().f_code.co_name}, New student {sdh_student["leerlingnummer"]}')
                mstudent.student_add_m(new_students)
                mstudent.student_change_m(updated_students)
                log.info(f'{sys._getframe().f_code.co_name}, students add {len(new_students)}, update {nbr_updated}')
            else:
                log.info(f'{sys._getframe().f_code.co_name}, error retrieving students from SDH, {sdh_students["data"]}')
        else:
            log.error(f'{sys._getframe().f_code.co_name}: api call to {sdh_student_url} returned {res.status_code}')

        # check for inactive students, with devices that need to be removed from entra/intune/autopilot
        # mark these students for deletion
        deleted_students = []
        res = requests.get(f"{sdh_student_url}&filters=active$=$false,status$=$EOL-REMOVE-DEVICE", headers={'x-api-key': sdh_key})
        if res.status_code == 200:
            sdh_students = res.json()
            if sdh_students['status']:
                log.info(f'{sys._getframe().f_code.co_name}, retrieved {len(sdh_students["data"])} inactive students from SDH')
                for sdh_student in sdh_students["data"]:
                    if int(sdh_student["leerlingnummer"]) < 0: continue
                    if sdh_student["leerlingnummer"] in db_leerlingnummer_to_student:
                        student = db_leerlingnummer_to_student[sdh_student["leerlingnummer"]]
                        deleted_students.append({"student": student, "delete": True, "changed": ["delete"]})
                        log.info(f'{sys._getframe().f_code.co_name}, Delete student {student.leerlingnummer}')
                        del(db_leerlingnummer_to_student[sdh_student["leerlingnummer"]])
                mstudent.student_change_m(deleted_students)
                log.info(f'{sys._getframe().f_code.co_name}, students delete {len(deleted_students)}')
            else:
                log.info(f'{sys._getframe().f_code.co_name}, error retrieving students from SDH, {sdh_students["data"]}')
        else:
            log.error(f'{sys._getframe().f_code.co_name}: api call to {sdh_student_url} returned {res.status_code}')
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return 0, 0, 0
    return len(new_students), nbr_updated, len(deleted_students)


def cron_staff_load_from_sdh(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    updated_staffs = []
    nbr_updated = 0
    new_staffs = []
    deleted_staffs = []
    try:
        groep_codes = mstaff.get_nbr_staff_per_groep()
        sdh_staff_url = flask_app.config["SDH_GET_STAFF_URL"]
        sdh_key = flask_app.config["SDH_GET_KEY"]
        res = requests.get(sdh_staff_url, headers={'x-api-key': sdh_key})
        if res.status_code == 200:
            sdh_staffs = res.json()
            if sdh_staffs['status']:
                log.info(f'{sys._getframe().f_code.co_name}, retrieved {len(sdh_staffs["data"])} staffs from SDH')
                db_staffs = mstaff.staff_get_m()
                db_code_to_staff = {s.code: s for s in db_staffs}
                for sdh_staff in sdh_staffs["data"]:
                    if sdh_staff["code"] in db_code_to_staff:
                        # check for changed rfid or classgroup
                        db_staff = db_code_to_staff[sdh_staff["code"]]
                        update = {}
                        if db_staff.voornaam != sdh_staff["voornaam"]:
                            update["voornaam"] = sdh_staff["voornaam"]
                        if db_staff.naam != sdh_staff["naam"]:
                            update["naam"] = sdh_staff["naam"]
                        if update:
                            update["changed"] = list(update.keys())
                            update.update({"staff": db_staff})
                            updated_staffs.append(update)
                            log.info(f'{sys._getframe().f_code.co_name}, Update staff {db_staff.code}, update {update}')
                            nbr_updated += 1
                        del(db_code_to_staff[sdh_staff["code"]])
                    else:
                        groep_code, groep_codes = mstaff.get_next_groep_code(groep_codes)
                        new_staffs.append({"code": sdh_staff["code"], "naam": sdh_staff["naam"], "voornaam": sdh_staff["voornaam"], "groep_code": groep_code})
                        log.info(f'{sys._getframe().f_code.co_name}, New staff {sdh_staff["code"]}, Groep code {groep_code}')
                deleted_staffs = [v for (k, v) in db_code_to_staff.items()]
                for staff in deleted_staffs:
                    updated_staffs.append({"staff": staff, "delete": True, "changed": ["delete"]})
                    log.info(f'{sys._getframe().f_code.co_name}, Delete staff {staff.code}')
                mstaff.staff_add_m(new_staffs)
                mstaff.staff_change_m(updated_staffs)
                log.info(f'{sys._getframe().f_code.co_name}, staffs add {len(new_staffs)}, update {nbr_updated}, delete {len(deleted_staffs)}')
            else:
                log.info(f'{sys._getframe().f_code.co_name}, error retrieving staffs from SDH, {sdh_staffs["data"]}')
        else:
            log.error(f'{sys._getframe().f_code.co_name}: api call to {sdh_staff_url} returned {res.status_code}')
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return 0, 0, 0
    return len(new_staffs), nbr_updated, len(deleted_staffs)



def cron_klas_load_from_sdh(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    nbr_updated = 0
    new_klassen = []
    deleted_klassen = []
    try:
        # check for new, updated or deleted students
        sdh_klas_url = flask_app.config["SDH_GET_KLAS_URL"]
        sdh_key = flask_app.config["SDH_GET_KEY"]
        res = requests.get(sdh_klas_url, headers={'x-api-key': sdh_key})
        if res.status_code == 200:
            sdh_klassen = res.json()
            if sdh_klassen['status']:
                log.info(f'{sys._getframe().f_code.co_name}, retrieved {len(sdh_klassen["data"])} klassen from SDH')
                db_klassen = mklas.klas_get_m()
                db_klas_cache = {k.klascode: k for k in db_klassen}
                for sdh_klas in sdh_klassen["data"]:
                    if sdh_klas["klascode"] in db_klas_cache:
                        del(db_klas_cache[sdh_klas["klascode"]])
                    else:
                        new_klassen.append({"klascode": sdh_klas["klascode"], "klasgroepcode": sdh_klas["klasgroepcode"]})
                        log.info(f'{sys._getframe().f_code.co_name}, New klas {sdh_klas["klascode"]}')
                deleted_klassen = [v for (k, v) in db_klas_cache.items()]
                for klas in deleted_klassen:
                    log.info(f'{sys._getframe().f_code.co_name}, Delete klas {klas.klascode}')
                mklas.klas_add_m(new_klassen)
                mklas.klas_delete_m(klassen=deleted_klassen)
                log.info(f'{sys._getframe().f_code.co_name}, klassen add {len(new_klassen)}, delete {len(deleted_klassen)}')
            else:
                log.info(f'{sys._getframe().f_code.co_name}, error retrieving klassen from SDH, {sdh_klassen["data"]}')
        else:
            log.error(f'{sys._getframe().f_code.co_name}: api call to {sdh_klas_url} returned {res.status_code}')
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return 0, 0
    return len(new_klassen), len(deleted_klassen)


def cron_push_devices(opaque=None, **kwargs):

    def push_data(data, properties, label):
        try:
            data_out = []
            for item in data:
                data_out.append({
                    properties[0]: item[0],
                    properties[1]: item[1],
                    properties[2]: str(item[2]) if item[2] else None,
                    properties[3]: item[3]
                })
            res = requests.post(sdh_device_url, headers={'x-api-key': sdh_key}, json=data_out)
            if res.status_code == 200:
                status = json.loads(res.text)
                if status["status"]:
                    log.info(f'{sys._getframe().f_code.co_name}, Deviceupdate for {len(data)} {label}, status, {status["data"]}')
                else:
                    log.error(f'{sys._getframe().f_code.co_name}, Deviceupdate for label, error, {status["data"]}')
            else:
                log.error(f'{sys._getframe().f_code.co_name}: api call to {sdh_device_url} returned {res.status_code}')
        except Exception as e:
            log.error(f'{sys._getframe().f_code.co_name}: {e}')

    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        sdh_device_url = flask_app.config["SDH_POST_DEVICE_URL"]
        sdh_key = flask_app.config["SDH_POST_KEY"]

        db_students = mstudent.student_get_m(fields=["leerlingnummer", "computer_name", "computer_lastsync_date", "computer_intune_id"])
        push_data(db_students, ["leerlingnummer", "computer_name", "computer_lastsync_date", "computer_intune_id"], "Students")

        db_staffs = mstaff.staff_get_m(fields=["code", "computer_name", "computer_lastsync_date", "computer_intune_id"])
        push_data(db_staffs, ["code", "computer_name", "computer_lastsync_date", "computer_intune_id"], "Staff")

        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


