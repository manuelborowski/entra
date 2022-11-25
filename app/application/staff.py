from app import log
from app.data import settings as msettings, staff as mstaff
from app.application import util as mutil, ad as mad, papercut as mpapercut
import sys


def delete_staffs(ids):
    mstaff.delete_staffs(ids)


# do not deactivate, but delete
def deactivate_deleted_staff_cron_task(opaque=None):
    try:
        deleted_staffs = mstaff.get_staffs({"delete": True})
        mstaff.delete_staffs(staffs=deleted_staffs)
        log.info(f"deleted {len(deleted_staffs)} staffs")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')

############## api ####################
def get_fields():
    try:
        return mstaff.get_columns()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return False


def api_get_staffs(options=None):
    try:
        return mutil.api_get_model_data(mstaff.Staff, options)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def update_staff(data):
    try:
        staff = mstaff.get_first_staff({'id': data['id']})
        if 'rfid' in data:
            rfid = data['rfid']
            if rfid != '':
                rfids = [r[0] for r in mstaff.get_staffs(fields=['rfid'])]
                if rfid in set(rfids):
                    staff = mstaff.get_first_staff({'rfid': rfid})
                    raise Exception(f'rfid {rfid} bestaat al voor {staff.voornaam} {staff.naam}')
            mad.update_staff(staff, {'rfid': rfid})
            mpapercut.update_staff(staff, {'rfid': rfid})
        if 'password_data' in data:
            mad.update_staff(staff, {'password': data['password_data']['password'], 'must_update_password': data['password_data']['must_update']})
        mstaff.update_staff(staff, data)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


############## formio #########################
def prepare_view_form(id, read_only=False):
    try:
        pass
        # staff = mstaff.get_first_staff({"id": id})
        # template = app.data.settings.get_json_template('staff-formio-template')
        # photo = mphoto.get_first_photo({'filename': staff.foto})
        # data = {"photo": base64.b64encode(photo.photo).decode('utf-8') if photo else ''}
        # template = mformio.prepare_for_edit(template, data)
        # return {'template': template,
        #         'defaults': staff.to_dict()}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


############ datatables: staff overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for staff in db_list:
        em = staff.to_dict()
        em.update({
            'row_action': staff.id,
            'DT_RowId': staff.id
        })
        out.append(em)
    return total_count, filtered_count, out
