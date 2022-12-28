import app.application.api
from app.data import settings as msettings, staff as mstaff, person as mperson
from app.application import util as mutil, ad as mad, papercut as mpapercut, email as memail
from app.application.formio import iterate_components_cb
import sys, json

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def staff_delete(ids):
    mstaff.staff_delete_m(ids)


# do not deactivate, but delete
def cron_task_deactivate_deleted_staff(opaque=None):
    try:
        deleted_staffs = mstaff.staff_get_m({"delete": True})
        mstaff.staff_delete_m(staffs=deleted_staffs)
        log.info(f"deleted {len(deleted_staffs)} staffs")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


############## api ####################
def api_staff_get_fields():
    try:
        return mstaff.get_columns()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return False


def api_staff_get(options=None):
    try:
        data = app.application.api.api_get_model_data(mstaff.Staff, options)
        for i in data["data"]:
            i["profiel"] = json.loads(i["profiel"])
        return data
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise Exception(f'STAFF-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


# If a staff already exists in database, no further action
# if a staff already exists in AD, reactivate staff and place in OU=Personeel
# if a staff already exists in Papercut, skip
def api_staff_add(data):
    try:
        db_staff = mstaff.staff_get({'code': data['code']})
        if db_staff:
            log.error(f'{sys._getframe().f_code.co_name}, error, staff with {db_staff.code} already exists in Database')
            return {"status": False, "data": f'Fout, personeelslid {db_staff.code} bestaat al in Database'}
        if "rfid" in data:
            if mperson.check_if_rfid_already_exists(data["rfid"]):
                del (data["rfid"])
        data = mstaff.massage_data(data)
        db_ok = ad_ok = papercut_ok = False
        db_staff = mstaff.staff_add(data)
        if db_staff:
            db_ok = True
            ad_ok = mad.process_add_update_delete_staff([db_staff])
            papercut_ok = mpapercut.person_add(db_staff)
            db_staff = mstaff.staff_update(db_staff, {"changed": "", "new": False, "delete": False})
        if db_ok and ad_ok and papercut_ok:
            log.info(f"Add staff: {data}")
            return {"status": True, "data": f'Personeelslid toegevoegd: {db_staff.code}'}
        log.error(f'{sys._getframe().f_code.co_name}, error, could not add staff with {data["code"]}, DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}')
        return {"status": False, "data": f'Fout bij toevoegen van personeelslid {data["code"]}: DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}'}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(data)
        raise Exception(f'STAFF-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


# manually update (some) properties
def api_staff_update(data):
    try:
        db_ok = papercut_ok = ad_ok = False
        error_data = ''
        db_staff = mstaff.staff_get({'id': data['id']})
        data = mstaff.massage_data(data)
        if "rfid" in data:
            if mperson.check_if_rfid_already_exists(data["rfid"]):
                error_data = f'RFID {data["rfid"]} bestaat al voor {db_staff.person_id}<db>'
                del (data["rfid"])
        changed_attributes = [k for k, v in data.items() if hasattr(db_staff, k) and v != getattr(db_staff, k)]
        data.update({"changed": json.dumps(changed_attributes)})
        db_staff = mstaff.staff_update(db_staff, data)
        if db_staff:
            db_ok = True
            ad_ok = mad.process_add_update_delete_staff([db_staff])
            papercut_ok = mpapercut.person_update(db_staff, data)
        db_staff = mstaff.staff_update(db_staff, {"changed": "", "new": False, "delete": False})
        new_password = data["new-password"] if "new-password" in data else None
        must_change_password = data["user-must-update-password"] if "user-must-update-password" in data else False
        if new_password:
            ad_ok = ad_ok and mad.person_set_password(db_staff, new_password, must_change_password)
            data["new-password"] = "xxx"
        if db_ok and ad_ok and papercut_ok:
            log.info(f'{sys._getframe().f_code.co_name}: DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}, data {data}')
            return {"status": True, "data": f"Personeelslid {db_staff.code} is aangepast"}
        else:
            log.error(f'{sys._getframe().f_code.co_name}: DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}, data {data}')
            return {"status": False, "data": f"Fout, kan {db_staff.code} niet aanpassen.<db>{error_data}"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise Exception(f'STAFF-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


# for AD only, a delete results in deactivating the staff and placing it in the OU=Inactief
# data: list of database-id's
def api_staff_delete(data):
    try:
        staff_from_wisa = []
        staff_to_delete = []
        for id in data:
            staff = mstaff.staff_get({'id': id})
            if staff.stamboeknummer != '': # not empty means staff is synchronized from WISA and can not be deleted
                staff_from_wisa.append(staff)
            else:
                staff_to_delete.append(staff)
        if staff_to_delete:
            for staff in staff_to_delete:
                mstaff.staff_update(staff, {"changed": "", "new": False, "delete": True})
            mad.process_add_update_delete_staff(staff_to_delete)
            mpapercut.person_delete_m(staff_to_delete)
            mstaff.staff_delete_m(staffs=staff_to_delete)
        if staff_from_wisa:
            return {"status": True, "data": f"{len(staff_to_delete)} verwijderd.<br>Kunnen niet worden verwijderd: {', '.join([s.code for s in staff_from_wisa])}"}
        return {"status": True, "data": f"{len(staff_to_delete)} verwijderd."}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise Exception(f'STAFF-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


############## formio #########################
def form_update_cb(component, opaque):
    try:
        if component and "key" in component:
            if "update-properties" in opaque and component["key"] in opaque["update-properties"]:
                for property in opaque["update-properties"][component["key"]]:
                    component[property["name"]] = property["value"]
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def form_prepare_new_update_staff(form):
    try:
        profiles = msettings.get_configuration_setting("ad-staff-profiles")
        profielen = {"values": [{"value": p[0], "label": p[0]} for p in profiles if [1]]}
        form_update = {"update-properties": {"profiel": [{"name": "data", "value": profielen}, {"name": "defaultValue", "value": profiles[0][0]} ]}}
        iterate_components_cb(form, form_update_cb, form_update)
        return form
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

def post_sql_order(l, on, direction):
    return sorted(l, key=lambda x: x[on], reverse=direction=="desc")
