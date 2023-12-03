from app.data import settings as msettings, student as mstudent, staff as mstaff, klas as mklas
import sys, requests, base64, json
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
    deleted_students = []
    try:
        # check for new, updated or deleted students
        sdh_student_url = flask_app.config["SDH_GET_STUDENT_URL"]
        sdh_key = flask_app.config["SDH_KEY"]
        res = requests.get(sdh_student_url, headers={'x-api-key': sdh_key})
        if res.status_code == 200:
            sdh_students = res.json()
            if sdh_students['status']:
                log.info(f'{sys._getframe().f_code.co_name}, retrieved {len(sdh_students["data"])} students from SDH')
                db_students = mstudent.student_get_m()
                db_leerlingnummer_to_student = {s.leerlingnummer: s for s in db_students} if db_students else {}
                for sdh_student in sdh_students["data"]:
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
                deleted_students = [v for (k, v) in db_leerlingnummer_to_student.items()]
                for student in deleted_students:
                    updated_students.append({"student": student, "delete": True, "changed": ["delete"]})
                    log.info(f'{sys._getframe().f_code.co_name}, Delete student {student.leerlingnummer}')
                mstudent.student_add_m(new_students)
                mstudent.student_change_m(updated_students)
                # mstudent.student_delete_m(students=deleted_students)
                log.info(f'{sys._getframe().f_code.co_name}, students add {len(new_students)}, update {nbr_updated}, delete {len(deleted_students)}')
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
        groep_codes = mstaff.init_groep_codes()
        sdh_staff_url = flask_app.config["SDH_GET_STAFF_URL"]
        sdh_key = flask_app.config["SDH_KEY"]
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
                            update.update({"item": db_staff})
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
        sdh_key = flask_app.config["SDH_KEY"]
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


def cron_cleanup_sdh(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        db_students = mstudent.student_get_m(("changed", "!", ""))
        db_students += mstudent.student_get_m(("new", "=", True))
        for student in db_students:
            student.new = False
            student.changed = ""
            student.changed_old = ""
        mstudent.commit()
        db_students = mstudent.student_get_m(("delete", "=", True))
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

