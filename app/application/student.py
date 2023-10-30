import app.application.api
from app import log
from app.application.formio import iterate_components_cb
from app.data import student as mstudent, settings as msettings, photo as mphoto, person as mperson
import app.data.settings
from app.application import formio as mformio, email as memail, util as mutil, ad as mad, papercut as mpapercut
import sys, base64, json, pandas as pd, datetime, io
from flask import make_response, send_from_directory
from .smartschool import send_message
from app.data.logging import ULog

def student_delete(ids):
    mstudent.student_delete_m(ids)


# find the first next vsk number, to be assigned to a student, or -1 when not found
def vsk_get_next_number():
    try:
        student = mstudent.student_get_m([('delete', "=", False)], order_by='-vsknummer', first=True)
        if student and student.vsknummer != '':
            return {"status": True, "data": int(student.vsknummer) + 1}
        else:
            start_number = msettings.get_configuration_setting('cardpresso-vsk-startnumber')
            return {"status": True, "data": start_number}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'Error: {e}'}


# update students with no vsk number yet.  Start from the given number and increment for each student
# return the number of updated students
def vsk_update_numbers(vsknumber):
    try:
        vsknumber = int(vsknumber)
        changed_students = []
        students = mstudent.student_get_m([('vsknummer', "=", ''), ('delete', "=",  False)])
        nbr_updated = 0
        for student in students:
            changed_students.append({'vsknummer': str(vsknumber), 'student': student, 'changed': ['vsknummer']})
            vsknumber += 1
            nbr_updated += 1
        mstudent.student_change_m(changed_students)
        return {"status": True, "data": nbr_updated}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'Error: {e}'}


def vsk_clear_numbers():
    students = mstudent.student_get_m()
    nbr_updated = 0
    for student in students:
        student.vsknummer = ''
        nbr_updated += 1
    mstudent.commit()
    return {"status": True, "data": nbr_updated}


def cron_task_vsk_numbers(opaque=None):
    # check if schooljaar has changed.  If so, clear all vsk numbers first
    ret = vsk_get_next_number()
    if ret['status'] and ret['data'] > -1:
        ret = vsk_update_numbers(ret['data'])
        if ret['status']:
            log.info(f'vsk cron task, {ret["data"]} numbers updated')
        else:
            log.error(f'vsk cron task, error: {ret["data"]}')
    else:
        log.error('vsk cron task, error: no vsk numbers available')
        memail.send_inform_message('sdh-inform-emails', "SDH: Vsk nummers", "Waarschuwing, er zijn geen Vsk nummers toegekend (niet beschikbaar?)")


# delete student that is flagged delete
# reset new and changed flags
def student_post_processing(opaque=None):
    try:
        log.info(f'{sys._getframe().f_code.co_name}: START')
        deleted_students = mstudent.student_get_m([("delete", "=",  True)])
        mstudent.student_delete_m(students=deleted_students)
        log.info(f"deleted {len(deleted_students)} students")
        changed_new_student = mstudent.student_get_m([("changed", "!", "")])
        changed_new_student.extend(mstudent.student_get_m([("new", "=", True)]))
        for student in changed_new_student:
            mstudent.student_update(student, {"changed": "", "new": False}, commit=False)
        mstudent.commit()
        log.info(f"new, changed {len(changed_new_student)} student")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def student_get_statuses(label=False):
    return mstudent.Student.get_statuses(label=label)


def klassen_get_unique():
    klassen = mstudent.student_get_m(fields=['klascode'])
    klassen = list(set([k[0] for k in klassen]))
    klassen.sort()
    return klassen



export_header = [
    "voornaam", "naam", "klas", "gebruikersnaam", "ww", "email", "naam co1", "voornaam co1", "email co1", "ww co1","naam co2", "voornaam co2", "email co2",  "ww co2"
]

def export_passwords(ids):
    try:
        students = mstudent.student_get_m(ids=ids)
        students_to_export = []
        for student in students:
            passwd0 = mutil.ss_create_password_for_account(student.leerlingnummer, 0)
            passwd1 = mutil.ss_create_password_for_account(student.leerlingnummer, 1)
            passwd2 = mutil.ss_create_password_for_account(student.leerlingnummer, 2)
            student_export = {}
            student_export["voornaam"] = student.voornaam
            student_export["naam"] = student.naam
            student_export["klas"] = student.klascode
            student_export["gebruikersnaam"] = student.username
            student_export["ww"] = passwd0
            student_export["email"] = student.prive_email if student.prive_email != "" else "-"
            student_export["naam co1"] = student.lpv1_naam
            student_export["voornaam co1"] = student.lpv1_voornaam
            student_export["email co1"] = student.lpv1_email if student.lpv1_email != "" else "-"
            student_export["ww co1"] = passwd1 if student.lpv1_naam != "" else ""
            student_export["naam co2"] = student.lpv2_naam
            student_export["voornaam co2"] = student.lpv2_voornaam
            student_export["email co2"] = student.lpv2_email if student.lpv2_email != "" else "-"
            student_export["ww co2"] = passwd2 if student.lpv2_naam != "" else ""
            students_to_export.append(student_export)
            status = json.loads(student.status) if student.status else []
            if mstudent.Student.export in status:
                status.remove(mstudent.Student.export)
            mstudent.student_update(student, {"status": json.dumps(status)}, commit=False)
        mstudent.commit()
        df = pd.DataFrame(students_to_export)
        out = io.BytesIO()
        excel_writer = pd.ExcelWriter(out, engine="xlsxwriter")
        df.to_excel(excel_writer, index=False)
        excel_writer.close()
        res = make_response(out.getvalue())
        res.headers["Content-Disposition"] = f"attachment; filename=smartschool-export-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')}.xlsx"
        res.headers["Content-type"] = "data:text/xlsx"
        log.error(f'{sys._getframe().f_code.co_name}: Exported Smartschool info, {len(students)} students')
        return res
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"data": f"Fout: {e}"}


############## api ####################
def api_student_get_fields():
    try:
        return mstudent.get_columns()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return False


def api_student_get(options=None):
    try:
        return app.application.api.api_get_model_data(mstudent.Student, options)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise Exception(f'STUDENT-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


def api_student_update(data):
    try:
        db_ok = papercut_ok = ad_ok = True
        db_student = mstudent.student_get([('id', "=", data['id'])])
        if "password_data" in data:
            new_password = data["password_data"]["password"]
            must_change_password = data["password_data"]["must_update"]
            ad_ok = ad_ok and mad.person_set_password(db_student, new_password, must_change_password)
            data["password_data"] = "xxx"
        elif "rfid" in data:
            rfid = data['rfid']
            person = mperson.check_if_rfid_already_exists(data["rfid"])
            if person:
                log.error("FLUSH-TO-EMAIL")  # this will trigger an email with ERROR-logs (if present)
                return {"status": False, "data": f"RFID {rfid} bestaat al voor {person.person_id}"}
        changed_attributes = [k for k, v in data.items() if hasattr(db_student, k) and v != getattr(db_student, k)]
        data = {k: v for k,v in data.items() if k in changed_attributes}
        if data:
            ad_ok = ad_ok and mad.student_update(db_student, data)
            papercut_ok = papercut_ok and mpapercut.person_update(db_student, data)
            db_student = mstudent.student_update(db_student, data)
            db_ok = db_ok and db_student is not None
        if db_ok and ad_ok and papercut_ok:
            log.info(f'{sys._getframe().f_code.co_name}: DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}, data {data}')
            log.error("FLUSH-TO-EMAIL")  # this will trigger an email with ERROR-logs (if present)
            return {"status": True, "data": f"Student {db_student.person_id} is aangepast"}
        else:
            log.error(f'{sys._getframe().f_code.co_name}: DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}, data {data}')
            log.error("FLUSH-TO-EMAIL")  # this will trigger an email with ERROR-logs (if present)
            return {"status": False, "data": f"Fout, kan student {db_student.person_id} niet aanpassen."}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error("FLUSH-TO-EMAIL")  # this will trigger an email with ERROR-logs (if present)
        return {"status": False, "data": f"Fout, {e}"}


def api_upload_leerid(files):
    try:
        lid_students = []
        for file in files:
            lid_file = pd.read_excel(file)
            lid_students += lid_file.to_dict("records")

        if lid_students:
            db_students = mstudent.student_get_m()
            db_student_cache = {(s.naam + s.voornaam).lower(): s for s in db_students}
            nbr_found = 0
            nbr_not_in_sdh = 0
            nbr_not_in_lid = 0
            for student in lid_students:
                key = (student["Achternaam"] + student["Voornaam"]).lower()
                if key in db_student_cache:
                    nbr_found += 1
                    db_student = db_student_cache[key]
                    db_student.leerid_username = student["LeerID Gebruikersnaam"]
                    db_student.leerid_password = student["LeerID Wachtwoord"]
                    status = json.loads(db_student.status) if db_student.status else []
                    status.append(mstudent.Student.leerid)
                    db_student.status = json.dumps(status)
                    del(db_student_cache[key])
                else:
                    nbr_not_in_sdh += 1
            for _, student in db_student_cache.items():
                nbr_not_in_lid += 1
                log.info(f'{sys._getframe().f_code.co_name}: Found in SDH, not in LID, {student.naam} {student.voornaam}')
            log.info(f'{sys._getframe().f_code.co_name}: ok {nbr_found}, NOT in SDH {nbr_not_in_sdh}, NOT in LID {nbr_not_in_lid}')
            mstudent.commit()

    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error("FLUSH-TO-EMAIL")  # this will trigger an email with ERROR-logs (if present)
        return {"status": False, "data": f"Fout, {e}"}


def api_update_student_data(data):
    try:
        key_cols = data["key_cols"]
        db_students = mstudent.student_get_m()
        db_students_cache = {"".join([str(getattr(s, f)) for f in key_cols]).lower() : s for s in db_students}
        update_students = []
        for student in data["students"]:
            if student["key"] in db_students_cache:
                db_student = db_students_cache[student["key"]]
                student_data = {"student": db_student, "changed": data["fields"]}
                student_data.update(student["data"])
                update_students.append(student_data)
        mstudent.student_change_m(update_students)
        return {"status": True}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error("FLUSH-TO-EMAIL")  # this will trigger an email with ERROR-logs (if present)
        return {"status": False, "data": f"Fout, {e}"}


def api_upload_student_data(file):
    try:
        pd_data = pd.read_excel(file)
        data_list = pd_data.to_dict("records")
        cmd0_col = pd_data.head().columns[0]
        cmd1_col = pd_data.head().columns[1]
        cmd2_col = pd_data.head().columns[2]

        db_students = mstudent.student_get_m()
        db_students_cache = {}
        key_cols = ["leerlingnummer"]
        key_field = key_cols[0]
        concat_cols = []
        relevant_fields = []
        aliases = []
        nbr_double = 0
        nbr_found = 0
        nbr_not_found = 0
        nbr_invalid_line = 0
        # found_cache = []
        update_students = []
        students_processed = []
        for item in data_list:
            if "$key$" == item[cmd0_col]:
                key_cols = item[cmd1_col].split("-")
                key_field = "".join(key_cols)
                continue
            elif "$concat$" == item[cmd0_col]:
                new_field = item[cmd1_col]
                concat_fields = item[cmd2_col].split("-")
                concat_cols.append((new_field, concat_fields))
                continue
            elif "$fields$" == item[cmd0_col]:
                relevant_fields = item[cmd1_col].split(",")
                continue
            elif "$alias$" == item[cmd0_col]:
                aliases.append((item[cmd1_col], item[cmd2_col]))
                continue

            if not db_students_cache:
                for student in db_students:
                    key_value = "".join([str(getattr(student, f)) for f in key_cols]).lower()
                    db_students_cache[key_value] = student

            try:
                for alias in aliases:
                    item[alias[1]] = item[alias[0]]
                key = "".join([item[k] for k in key_cols])
                item[key_field] = key.lower()
                for cc in concat_cols:
                    item[cc[0]] = "".join([str(item[k]) for k in cc[1]])

                if item[key_field] in db_students_cache:
                    if item[key_field] in students_processed:
                        log.info(f"Student appears twice, {db_students_cache[item[key_field]].naam} {db_students_cache[item[key_field]].voornaam}")
                        nbr_double += 1
                    else:
                        nbr_found += 1
                        data = {k: item[k] for k in relevant_fields}
                        student = {"key": item[key_field], "data": data }
                        update_students.append(student)
                        students_processed.append(item[key_field])
                else:
                    log.error(f"Student not found, {item[key_field]}")
                    nbr_not_found += 1
            except:
                nbr_invalid_line += 1
        log.info(f"{sys._getframe().f_code.co_name}: found {nbr_found}, double {nbr_double}, not found {nbr_not_found}, invalid {nbr_invalid_line}")
        return {"status": True, "data": {"nbr_found": nbr_found, "nbr_double": nbr_double, "nbr_not_found": nbr_not_found, "nbr_invalid": nbr_invalid_line,
                                         "key_cols": key_cols, "students": update_students, "fields": relevant_fields}}

    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error("FLUSH-TO-EMAIL")  # this will trigger an email with ERROR-logs (if present)
        return {"status": False, "data": f"Fout, {e}"}


def api_send_leerid(ids):
    try:
        if ids:
            nbr_send = 0
            warning = ULog(ULog.warning, "LeerID verzenden:")
            students = mstudent.student_get_m(ids=ids)
            for student in students:
                if not student.leerid_password or not student.leerid_username:
                    log.info(f'{sys._getframe().f_code.co_name}: {student.leerlingnummer}, {student.naam} {student.voornaam} has no LeerID')
                    warning.add(f"{student.naam} {student.voornaam}, {student.leerlingnummer} heeft geen LeerID account")
                    continue
                body = msettings.get_configuration_setting("leerid-message-content")
                subject = msettings.get_configuration_setting("leerid-message-subject")
                send_to = student.leerlingnummer
                # send_from = "sdh"
                send_from = "20210708017" #boro
                body = body.replace("%%FIRSTNAME%%", student.voornaam)
                body = body.replace("%%USERNAME%%", student.leerid_username)
                body = body.replace("%%PASSWORD%%", student.leerid_password)
                send_message(send_to, send_from, subject, body)
                status = json.loads(student.status) if student.status else []
                if mstudent.Student.leerid in status:
                    status.remove(mstudent.Student.leerid)
                    student.status = json.dumps(status)
                nbr_send += 1
            mstudent.commit()
            valid_warning = warning.finish()
            if valid_warning:
                return {"status": True, "data": valid_warning.message}
            return {"status": True, "data": f"Leerid is verstuurd naar {nbr_send} leerlingen"}
        return {"status": True, "data": "Fout, geen studenten geselecteerd"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f"Fout, {e}"}


def api_database_integrity_check(data):
    try:
        ret = {"status": False, "data": "Gelieve minstens één database te selecteren!"}
        if 'ad' in data['databases']:
            if data['event'] == 'event-update-database':
                ret = mad.database_integrity_check(return_log=True, mark_changes_in_db=True)
                if ret['status']:
                    ret = mad.ad_student_process_flagged()
            elif data['event'] == 'event-start-integrity-check':
                ret = mad.database_integrity_check(return_log=True)
        return ret
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f"Fout, {e}"}

############## formio #########################
def form_prepare_for_view_cb(component, opaque):
        if component['key'] == 'photo':
            component['attrs'][0]['value'] = component['attrs'][0]['value'] + str(opaque['photo'])


def form_prepare_for_view(id, read_only=False):
    try:
        student = mstudent.student_get([("id", "=", id)])
        template = app.data.settings.get_configuration_setting('student-formio-template')
        photo = mphoto.photo_get({'filename': student.foto})
        data = {"photo": base64.b64encode(photo.photo).decode('utf-8') if photo else ''}
        iterate_components_cb(template, form_prepare_for_view_cb, data)
        return {'template': template,
                'defaults': student.to_dict()}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def form_prepare_for_edit(form, flat={}, unfold=False):
    def cb(component):
        if component['key'] == 'photo':
            component['attrs'][0]['value'] = component['attrs'][0]['value'] + str(flat['photo'])

    iterate_components_cb(form, cb)
    return form


############ datatables: student overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for student in db_list:
        em = student.to_dict()
        if student.foto_id == -1:
            em['overwrite_cell_color'] = [['foto', 'pink']]
        em.update({
            'row_action': student.id,
            'DT_RowId': student.id
        })
        out.append(em)
    return total_count, filtered_count, out


def photo_get_nbr_not_found():
    nbr_students_no_photo = mstudent.student_get_m([('foto_id', "=", -1)], count=True)
    return nbr_students_no_photo


