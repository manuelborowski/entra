from app import flask_app
from app.data import student as mstudent, photo as mphoto, cardpresso as mcardpresso, utils as mutils
from app.application import settings as msettings, email as memail
import sys, json, datetime

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

# remark; for contactless operations (RFID), use Springcard crazywriter Contactless 0 as encoder


def __process_badges_with_new_rfid(ids):
    try:
        changed_students = []
        deleted_badges = []
        if ids:
            badges = mcardpresso.badge_get_m(ids=ids)
            if badges:
                saved_students = {s.leerlingnummer: s for s in mstudent.student_get_m([('delete', "=", False)])}
                for badge in badges:
                    if badge.rfid != '':
                        if badge.leerlingnummer in saved_students:
                            new_rfid = badge.rfid.upper().replace('Q', 'A')
                            changed_students.append({'changed': ['rfid'], 'rfid': new_rfid, 'student': saved_students[badge.leerlingnummer]})
                            log.info(f'{sys._getframe().f_code.co_name}: new rfid {new_rfid} for {badge.leerlingnummer}')
                        else:
                            log.info(f'{sys._getframe().f_code.co_name}: {badge.leerlingnummer} not found')
                        deleted_badges.append(badge.id)
                if changed_students:
                    mstudent.student_change_m(changed_students)
                if deleted_badges:
                    mcardpresso.badge_delete(deleted_badges)
        log.info(f'__process_badges_with_new_rfid: updated {len(changed_students)} rfids of students')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def badge_delete(ids):
    try:
        mcardpresso.badge_delete(ids)
        log.info(f"done deleting badges: {ids}")
        return {"status": True, "data": "Studenten (-badges) zijn verwijderd"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'generic error {e}'}


def badge_update_rfid(ids):
    try:
        __process_badges_with_new_rfid(ids)
        log.info(f"done updating students with new RFID")
        return {"status": True, "data": "Studenten RFID code zijn aangepast"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'generic error {e}'}


# indicates what badge property is required to have a value (True) or can be empty (False)
REQUIRED_BADGE_PROPERTIES = {
    'naam': True,
    'voornaam': True,
    'leerlingnummer': True,
    'middag': False,
    'vsknummer': True,
    'geboortedatum': True,
    'straat': True,
    'huisnummer': True,
    'busnummer': False,
    'gemeente': True,
    'schoolnaam': True,
    'klascode': True
}

def badge_add(student_ids):
    try:
        if not student_ids:
            return
        nbr_added = 0
        nbr_no_photo = 0
        nbr_empty_propery = 0
        delete_badge_ids = []
        saved_photos = {p.id: p.photo for p in mphoto.photo_get_m()}
        students = mstudent.student_get_m(ids=student_ids)
        for student in students:
            badge = mcardpresso.badge_get([('leerlingnummer', "=", student.leerlingnummer)])
            if badge:
                delete_badge_ids.append(badge.id)
            photo = saved_photos[student.foto_id] if student.foto_id in saved_photos else None
            if photo:
                current_year = mutils.get_current_schoolyear(format=3)
                data = {'photo': photo, "schooljaar": current_year}
                # student_dict = student.to_dict()
                for property, value_is_required in REQUIRED_BADGE_PROPERTIES.items():
                    db_value = getattr(student, property)
                    if db_value != '' or not value_is_required:
                        data.update({property: db_value})
                    else:
                        log.error(f"New badge: {student.naam} {student.voornaam} {student.leerlingnummer} invalid property {property}, {db_value}")
                        data = {}
                        break
                if data:
                    badge = mcardpresso.badge_add(data)
                    if badge:
                        log.info(f"New badge: {student.naam} {student.voornaam} {student.leerlingnummer}")
                        nbr_added += 1
                else:
                    log.error(f"New badge: {student.naam} {student.voornaam} {student.leerlingnummer} not all properties are valid")
                    nbr_empty_propery += 1
            else:
                log.error(f"New badge: {student.naam} {student.voornaam} {student.leerlingnummer} has no valid photo")
                nbr_no_photo += 1
        if delete_badge_ids:
            mcardpresso.badge_delete(ids=delete_badge_ids)

        message = f"{len(student_ids)} leerlingen behandeld, {nbr_added} toegevoegd, {nbr_no_photo} hebben geen foto, {nbr_empty_propery} hebben ongeldige velden"
        email_to = msettings.get_list('cardpresso-inform-emails')
        memail.send_inform_message(email_to, "SDH: wijziging in Cardpresso", message)
        log.info(f'add_bages: {message}')
        return {"status": True, "data": message}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(f"add_badges: {student_ids}")
        return {"status": False, "data": f'generic error {e}'}



def cardpresso_entry_update(data):
    try:
        if not data or "id" not in data or "rfid" not in data:
            return {"status": False, "data": f"Fout, onvoldoende gegevens, {data}"}
        db_cardpresso = mcardpresso.badge_get([("id", "=", data["id"])])
        if db_cardpresso:
            db_cardpresso.rfid = data["rfid"]
            db_cardpresso.changed = '["rfid"]'
            mcardpresso.commit()
            return {"status": True, "data": f"rfid van {db_cardpresso.leerlingnummer}, {db_cardpresso.naam} {db_cardpresso.voornaam} is aangepast"}
        return {"status": False, "data": f"Fout, kan student {data} niet vinden in database."}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'generic error {e}'}




check_properties_changed = ['middag', 'vsknummer', 'photo', 'schooljaar', 'klascode', 'klasgroepcode']


# Check for new students or students with changed, relevant properties.  Add them to the cardpresso table
# Check for deleted students and delete (if present) their badges
def cron_task_new_badges(opaque=None):
    try:
        new_students = mstudent.student_get_m([('new', "=", True)])
        ids = [student.id for student in new_students]
        badge_add(ids)
        updated_students = mstudent.student_get_m([('changed', "!", ''), ('new', "=", False)])  # find students with changed property not equal to '' and not new
        if updated_students:
            ids = []
            for student in updated_students:
                changed = json.loads(student.changed)
                if list(set(check_properties_changed).intersection(changed)):
                    ids.append(student.id)
            badge_add(ids)
        deleted_students = mstudent.student_get_m([('delete', "=", True)])
        deleted_badges = []
        for student in deleted_students:
            badge = mcardpresso.badge_get([('leerlingnummer', "=", student.leerlingnummer)])
            if badge:
                    deleted_badges.append(badge.id)
        if deleted_badges:
            mcardpresso.badge_delete(deleted_badges)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


msettings.subscribe_handle_button_clicked('button-new-badges', cron_task_new_badges, None)

# check for all badges with udpated RFID code.  If found, update the associated student with the RFID code and remove the badge.
def cron_task_new_rfid_to_database(opaque=None):
    try:
        rfid_code = msettings.get_configuration_setting('test-rfid-start-code')
        if rfid_code != '' and '#' not in rfid_code:
            try:
                code = int(rfid_code, 16)
                badges = mcardpresso.badge_get_m()
                for badge in badges:
                    badge.rfid = hex(code)[2:]
                    badge.changed = '["rfid"]'
                    code += 1
                mcardpresso.commit()
                msettings.set_configuration_setting('test-rfid-start-code', hex(code)[2:])
                log.info('new_rfid_to_database_cron_task: test: inserted dummy rfid codes')
            except Exception as e:
                log.error(f'new_rfid_to_database_cron_task: error, not a valid hex rfid-code {rfid_code}, {e}')
                pass
        else:
            badges = mcardpresso.badge_get_m([('changed', "=", '["rfid"]')])
            ids = [b.id for b in badges]
            __process_badges_with_new_rfid(ids)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'generic error {e}'}


############ badges overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for item in db_list:
        em = item.to_dict()
        em.update({
            'row_action': item.id,
            'DT_RowId': item.id
        })
        out.append(em)
    return total_count, filtered_count, out



