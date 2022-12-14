from app import log
from app.data import settings as msettings, staff as mstaff
from app.application import util as mutil, ad as mad, papercut as mpapercut
from app.application.formio import iterate_components_cb
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
def api_fields_get():
    try:
        return mstaff.get_columns()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return False


def api_staff_get(options=None):
    try:
        data = mutil.api_get_model_data(mstaff.Staff, options)
        for i in data["data"]:
            i["profiel"] = i["profiel"].split(",")
        return data
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def api_staff_add(data):
    try:
        staff = mstaff.get_first_staff({'code': data['code']})
        if staff:
            log.error(f'{sys._getframe().f_code.co_name}, error, staff with {staff.code} already exists in Database')
            return {"status": False, "data": f'Fout, personeelslid {staff.code} bestaat al in Database'}
        staff = mad.staff_get(data["code"])
        if staff:
            log.error(f'{sys._getframe().f_code.co_name}, error, staff with {data["code"]} already exists in AD')
            return {"status": False, "data": f'Fout, personeelslid {data["code"]} bestaat al in AD'}
        staff = mpapercut.user_get(data["code"])
        if staff:
            log.error(f'{sys._getframe().f_code.co_name}, error, staff with {data["code"]} already exists in Papercut')
            return {"status": False, "data": f'Fout, personeelslid {data["code"]} bestaat al in Papercut'}
        if "profiel" in data:
            data["profiel"] = ", ".join(data["profiel"])
        staff = mstaff.add_staff(data)
        if staff:
            res = mad.staff_add(staff)
            if not res:
                mstaff.delete_staffs(staffs=[staff])
                log.error(f'{sys._getframe().f_code.co_name}: could not add staff {data["code"]} in AD')
                return {"status": False, "data": f'Kan personeelslid {data["code"]} niet toevoegen in AD'}
            res = mpapercut.user_add(staff.code)
            if not res:
                mstaff.delete_staffs(staffs=[staff])
                mad.staff_deactivate([staff])
                log.error(f'{sys._getframe().f_code.co_name}: could not add staff {data["code"]} in Papercut')
                return {"status": False, "data": f'Kan personeelslid {data["code"]} niet toevoegen in Papercut'}
        log.info(f"Add staff: {data}")
        return {"status": True, "data": {'code': staff.code}}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(data)
        raise Exception(f'STAFF-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


def api_staff_update(data):
    try:
        staff = mstaff.get_first_staff({'id': data['id']})
        if "profiel" in data:
            data["profiel"] = ", ".join(data["profiel"])
        if 'rfid' in data:
            rfid = data['rfid']
            if rfid != '':
                rfids = [r[0] for r in mstaff.get_staffs(fields=['rfid'])]
                if rfid in set(rfids):
                    staff = mstaff.get_first_staff({'rfid': rfid})
                    raise Exception(f'RFID {rfid} bestaat al voor {staff.code}')
            if not mad.staff_update(staff, {'rfid': rfid}):
                return {"status": False, "data": f'Kan RFID niet aanpassen in AD'}
            if not mpapercut.user_update(staff, [["primary-card-number", rfid]]):
                return {"status": False, "data": f'Kan RFID niet aanpassen in Papercut'}
            if not mstaff.update_staff(staff, data):
                return {"status": False, "data": f'Kan RFID niet aanpassen in Database'}
            return {"status": True}
        if 'password_data' in data:
            if not mad.staff_update(staff, {'password': data['password_data']['password'], 'must_update_password': data['password_data']['must_update']}):
                return {"status": False, "data": f'Kan PASWOORD niet aanpassen in AD'}
            if not mstaff.update_staff(staff, data):
                return {"status": False, "data": f'Kan PASWOORD niet aanpassen in Database'}
            return {"status": True}
        if staff.stamboeknummer != '': # synced from wisa, only profiel, interim or extra can be updated
            new_data = {k: data[k] for k in ["profiel", "interim", "extra"] if k in data}
            if not mstaff.update_staff(staff, new_data):
                return {"status": False, "data": f'Kan personeelslid niet aanpassen in Database'}
        else:
            if not mstaff.update_staff(staff, data):
                return {"status": False, "data": f'Kan personeelslid niet aanpassen in Database'}
            return {"status": True}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


# for AD only, a delete results in deactivating the staff and placing it in the OU=Inactief
def api_staff_delete(data):
    try:
        staff_from_wisa = []
        staff_to_delete = []
        for id in data:
            staff = mstaff.get_first_staff({'id': id})
            if staff.stamboeknummer != '': # not empty means staff is synchronized from WISA and can not be deleted
                staff_from_wisa.append(staff)
            else:
                staff_to_delete.append(staff)
        if staff_to_delete:
            mstaff.delete_staffs(staffs=staff_to_delete)
            mad.staff_deactivate(staff_to_delete)
        if staff_from_wisa:
            return {"status": False, "data": f"{len(staff_to_delete)} verwijderd.<br>Kunnen niet worden verwijderd: {', '.join([s.code for s in staff_from_wisa])}"}
        return {"status": True}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'generic error {e}'}


############## formio #########################
def update_form_cb(component, opaque):
    try:
        if component and "key" in component:
            if "update-properties" in opaque and component["key"] in opaque["update-properties"]:
                for property in opaque["update-properties"][component["key"]]:
                    component[property["name"]] = property["value"]
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def prepare_new_update_staff_form(form):
    try:
        profiles = msettings.get_configuration_setting("ad-staff-profiles")
        profielen = {"values": [{"value": p[0], "label": p[0]} for p in profiles if [1]]}
        form_update = {"update-properties": {"profiel": [{"name": "data", "value": profielen}, {"name": "defaultValue", "value": profiles[0][0]} ]}}
        iterate_components_cb(form, update_form_cb, form_update)
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
