import app.application.api
from app.data import settings as msettings, staff as mstaff
from app.application import util as mutil, ad as mad, papercut as mpapercut, email as memail
from app.application.formio import iterate_components_cb
import sys, datetime

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def __profiel_to_groepen(staff):
    profile_settings = msettings.get_configuration_setting("ad-staff-profiles")
    staff_profiles = staff.profiel.split(", ")
    groepen = set()
    for p in profile_settings:
        if p[0] in staff_profiles:
            groepen |= set(p[2])
    return list(groepen)


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
            i["profiel"] = i["profiel"].split(",")
        return data
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise Exception(f'STAFF-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


# If a staff already exists in database, no further action
# if a staff already exists in AD, reactivate staff and place in OU=Personeel
# if a staff already exists in Papercut, skip
def api_staff_add(data):
    try:
        db_staff = mstaff.staff_get_first({'code': data['code']})
        if db_staff:
            log.error(f'{sys._getframe().f_code.co_name}, error, staff with {db_staff.code} already exists in Database')
            return {"status": False, "data": f'Fout, personeelslid {db_staff.code} bestaat al in Database'}
        if "profiel" in data:
            data["profiel"] = ", ".join(data["profiel"])
        if "einddatum" in data:
            data['einddatum'] = app.application.formio.universal_datestring_to_date(data['einddatum'])
        db_ok = ad_ok = papercut_ok = False
        db_staff = mstaff.staff_add(data)
        if db_staff:
            db_ok = True
            ad_staff = mad.staff_get(db_staff.code)
            if ad_staff:
                ad_ok = True
                log.info(f'{sys._getframe().f_code.co_name}, staff with {db_staff.code} already exists in AD, re-activate')
            else:
                ad_ok = mad.staff_add(db_staff)
            groepen = __profiel_to_groepen(db_staff)
            default_password = msettings.get_configuration_setting('generic-standard-password')
            ad_data = {"groepen": groepen, "password": default_password, "extra": db_staff.extra, "interim": db_staff.interim}
            ad_ok = ad_ok and mad.staff_update(db_staff, ad_data)
            ad_ok = ad_ok and mad.staff_set_active_state(db_staff, active=True)
            papercut_staff = mpapercut.user_get(db_staff.code)
            if papercut_staff:
                log.info(f'{sys._getframe().f_code.co_name}, staff with {db_staff.code} already exists in Papercut, skip')
                papercut_ok = True
            else:
                papercut_ok =  mpapercut.user_add(db_staff)
        if db_ok and ad_ok and papercut_ok:
            log.info(f"Add staff: {data}")
            # send email to staff
            if db_staff.prive_email:
                template = msettings.get_configuration_setting("email-new-staff-html")
                template = mutil.find_and_replace(template, {"%%VOORNAAM%%": db_staff.voornaam, "%%WACHTWOORD%%": default_password, "%%GEBRUIKERSNAAM%%": db_staff.code})
                memail.send_email([db_staff.prive_email], "Je nieuwe schoolaccount", template)
            return {"status": True, "data": f'Personeelslid toegevoegd: {db_staff.code}'}
        log.error(f'{sys._getframe().f_code.co_name}, error, could not add staff with {data["code"]}, DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}')
        return {"status": False, "data": f'Fout bij toevoegen van personeelslid {data["code"]}: DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}'}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(data)
        raise Exception(f'STAFF-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


# manually update (some) properties
# update staff properties that are not present in the source-database (i.e. WISA) and propagate (if required) to other modules (papercut, ad, ...)
def api_staff_update(data):
    try:
        db_ok = papercut_ok = ad_ok = False
        error_data = ''
        db_staff = mstaff.staff_get_first({'id': data['id']})
        if "profiel" in data:
            data["profiel"] = ", ".join(data["profiel"])
        if "einddatum" in data:
            data['einddatum'] = app.application.formio.universal_datestring_to_date(data['einddatum'])
        if 'password_data' in data:
            data.update({'password': data['password_data']['password'], 'must_update_password': data['password_data']['must_update']})
        # only certain properties are allowed to be changed manually (i.e. not synced from the source-database)
        data = {k: data[k] for k in ["profiel", "interim", "extra", "rfid", "password", "must_update_password", "einddatum"] if k in data}
        if 'rfid' in data:
            rfid = data['rfid']
            if rfid != '':
                rfids = [r[0] for r in mstaff.staff_get_m(fields=['rfid'])]
                if rfid in set(rfids):
                    db_staff = mstaff.staff_get_first({'rfid': rfid})
                    log.error(f'{sys._getframe().f_code.co_name}: RFID {rfid} already exists for {db_staff.code}')
                    error_data = f'RFID {rfid} bestaat al voor {db_staff.code}<db>'
                    del(data["rfid"])
        db_staff = mstaff.staff_update(db_staff, data)
        if db_staff:
            db_ok = True
            if "profiel" in data:
                groepen = __profiel_to_groepen(db_staff)
                data["groepen"] = groepen
            ad_ok = mad.staff_update(db_staff, data)
            papercut_ok = mpapercut.user_update(db_staff, data)
        if "password" in data:
            data["password"] = "xxxx"
        if db_ok and ad_ok and papercut_ok:
            log.info(f'{sys._getframe().f_code.co_name}: DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}')
            return {"status": True, "data": f"Personeelslid {db_staff.code} is aangepast"}
        else:
            log.error(f'{sys._getframe().f_code.co_name}: DB {db_ok}, AD {ad_ok}, PAPERCUT {papercut_ok}')
            return {"status": False, "data": f"Fout, kan {db_staff.code} niet aanpassen.<db>{error_data}"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise Exception(f'STAFF-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


# for AD only, a delete results in deactivating the staff and placing it in the OU=Inactief
def api_staff_delete(data):
    try:
        staff_from_wisa = []
        staff_to_delete = []
        for id in data:
            staff = mstaff.staff_get_first({'id': id})
            if staff.stamboeknummer != '': # not empty means staff is synchronized from WISA and can not be deleted
                staff_from_wisa.append(staff)
            else:
                staff_to_delete.append(staff)
        if staff_to_delete:
            mstaff.staff_delete_m(staffs=staff_to_delete)
            for staff in staff_to_delete:
                mad.staff_set_active_state(staff, active=False)
            mpapercut.user_delete(staff_to_delete)
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
