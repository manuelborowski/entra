from app import log
from app.application.formio import iterate_components_cb
from app.data import student as mstudent, settings as msettings, photo as mphoto
import app.data.settings
from app.application import formio as mformio, email as memail, util as mutil, ad as mad, papercut as mpapercut
import sys, base64


def delete_students(ids):
    mstudent.delete_students(ids)


# find the first next vsk number, to be assigned to a student, or -1 when not found
def get_next_vsk_number():
    try:
        student = mstudent.get_students({'delete': False}, order_by='-vsknummer', first=True)
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
def update_vsk_numbers(vsknumber):
    try:
        vsknumber = int(vsknumber)
        changed_students = []
        students = mstudent.get_students({'vsknummer': '', 'delete': False})
        nbr_updated = 0
        for student in students:
            changed_students.append({'vsknummer': str(vsknumber), 'student': student, 'changed': ['vsknummer']})
            vsknumber += 1
            nbr_updated += 1
        mstudent.change_students(changed_students)
        return {"status": True, "data": nbr_updated}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'Error: {e}'}


def clear_vsk_numbers():
    students = mstudent.get_students()
    nbr_updated = 0
    for student in students:
        student.vsknummer = ''
        nbr_updated += 1
    mstudent.commit()
    return {"status": True, "data": nbr_updated}


def vsk_numbers_cron_task(opaque=None):
    # check if schooljaar has changed.  If so, clear all vsk numbers first
    schoolyear_changed, _, _ = msettings.get_changed_schoolyear()
    if schoolyear_changed:
        ret = clear_vsk_numbers()
        log.info(f'vsk_numbers_cron_task: deleted {ret["data"]} vsk numbers')
    ret = get_next_vsk_number()
    if ret['status'] and ret['data'] > -1:
        ret = update_vsk_numbers(ret['data'])
        if ret['status']:
            log.info(f'vsk cron task, {ret["data"]} numbers updated')
        else:
            log.error(f'vsk cron task, error: {ret["data"]}')
    else:
        log.error('vsk cron task, error: no vsk numbers available')
        memail.compose_message('sdh-inform-emails', "SDH: Vsk nummers", "Waarschuwing, er zijn geen Vsk nummers toegekend (niet beschikbaar?)")


# students that are marked as deleted are deleted from the database
def delete_marked_students_cron_task(opaque=None):
    try:
        deleted_students = mstudent.get_students({"delete": True})
        mstudent.delete_students(students=deleted_students)
        log.info(f"deleted {len(deleted_students)} students")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def clear_schoolyear_changed_flag_cron_task(opaque=None):
    msettings.reset_changed_schoolyear()


def get_unique_klassen():
    klassen = mstudent.get_students(fields=['klascode'])
    klassen = list(set([k[0] for k in klassen]))
    klassen.sort()
    return klassen


############## api ####################
def get_fields():
    try:
        return mstudent.get_columns()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return False


def api_get_students(options=None):
    try:
        return mutil.api_get_model_data(mstudent.Student, options)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')



def database_integrity_check(data):
    try:
        ret = {"status": False, "data": "Gelieve minstens één database te selecteren!"}
        if 'ad' in data['databases']:
            if data['event'] == 'event-update-database':
                ret = mad.database_integrity_check(return_log=True, mark_changes_in_db=True)
                if ret['status']:
                    ret = mad.cron_ad_student_task()
            elif data['event'] == 'event-start-integrity-check':
                ret = mad.database_integrity_check(return_log=True)
        return ret
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def update_student(data):
    try:
        student = mstudent.get_first_student({'id': data['id']})
        if 'rfid' in data:
            rfid = data['rfid']
            if rfid != '':
                rfids = [r[0] for r in mstudent.get_students(fields=['rfid'])]
                if rfid in set(rfids):
                    student = mstudent.get_first_student({'rfid': rfid})
                    raise Exception(f'RFID {rfid} bestaat al voor {student.voornaam} {student.naam}')
            if not mad.student_update(student, {'rfid': rfid}):
                return {"status": False, "data": f'Kan RFID niet aanpassen in AD'}
            mpapercut.update_student(student, {'rfid': rfid})
        if 'password_data' in data:
            if not mad.student_update(student, {'password': data['password_data']['password'], 'must_update_password': data['password_data']['must_update']}):
                return {"status": False, "data": f'Kan PASWOORD niet aanpassen in AD'}
        mstudent.update_student(student, data)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


############## formio #########################
def prepare_view_cb(component, opaque):
        if component['key'] == 'photo':
            component['attrs'][0]['value'] = component['attrs'][0]['value'] + str(opaque['photo'])


def prepare_view_form(id, read_only=False):
    try:
        student = mstudent.get_first_student({"id": id})
        template = app.data.settings.get_configuration_setting('student-formio-template')
        photo = mphoto.get_first_photo({'filename': student.foto})
        data = {"photo": base64.b64encode(photo.photo).decode('utf-8') if photo else ''}
        iterate_components_cb(template, prepare_view_cb, data)
        return {'template': template,
                'defaults': student.to_dict()}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


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


def get_nbr_photo_not_found():
    nbr_students_no_photo = mstudent.get_students({'foto_id': -1}, count=True)
    return nbr_students_no_photo


def prepare_for_edit(form, flat={}, unfold=False):
    def cb(component):
        if component['key'] == 'photo':
            component['attrs'][0]['value'] = component['attrs'][0]['value'] + str(flat['photo'])

    iterate_components_cb(form, cb)
    return form