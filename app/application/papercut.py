from app.data import staff as mstaff, student as mstudent
from app.application import settings as msettings
import xmlrpc.client, sys
from functools import wraps

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


PROPERTY_RFID = 'primary-card-number'

papercut_properties = [
    "balance", "primary-card-number", "secondary-card-number", "department", "disabled-print", "email", "full-name", "internal", "notes", "office", "print-stats.job-count", "print-stats.page-count",
    "net-stats.data-mb", "net-stats.time-hours", "restricted", "home", "unauthenticated", "username-alias", "dont-hold-jobs-in-release-station"]


def papercut_core_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            url = msettings.get_configuration_setting('papercut-server-url')
            port = msettings.get_configuration_setting('papercut-server-port')
            token = msettings.get_configuration_setting('papercut-auth-token')
            with xmlrpc.client.ServerProxy(f'http://{url}:{port}/rpc/api/xmlrpc') as server:
                kwargs["server"] = server
                kwargs["token"] = token
                return func(*args, **kwargs)
        except Exception as e:
            log.error(f'PAPERCUT-EXCEPTION: {func.__name__}: {e}')
            raise Exception(f'PAPERCUT-EXCEPTION: {func.__name__}: {e}')
    return wrapper


@papercut_core_wrapper
def person_update(person, data, **kwargs):
    update_properties = []
    if "rfid" in data:
        update_properties.append(["primary-card-number", data["rfid"]])
    if update_properties:
        ret = kwargs["server"].api.setUserProperties(kwargs["token"], person.person_id, update_properties)
        log.info(f'Update to Papercut, {person.person_id} RFID {update_properties}')
        return ret
    return True


@papercut_core_wrapper
def person_add(person, **kwargs):
    papercut_staff = person_get(person.person_id)
    if papercut_staff:
        log.info(f'{sys._getframe().f_code.co_name}, staff with {person.person_id} already exists in Papercut, skip')
        return True
    ret = kwargs["server"].api.addNewUser(kwargs["token"], person.person_id)
    log.info(f'Add to papercut, {person.person_id}')
    return ret


@papercut_core_wrapper
def person_delete_m(persons, **kwargs):
    for person in persons:
        try:
            ret = kwargs["server"].api.deleteExistingUser(kwargs["token"], person.person_id, True)
            log.info(f'Delete from papercut, {person.person_id}, result {ret}')
        except Exception as e:
            if "Fault 262" in str(e):
                log.info(f'user, {person.person_id}, not found in Papercut')
    return True


@papercut_core_wrapper
def person_get(person_id, **kwargs):
    try:
        ret = kwargs["server"].api.getUserProperties(kwargs["token"], person_id, papercut_properties)
        info = zip(papercut_properties, ret)
        return dict(info)
    except Exception as e:
        if "Fault 262" in str(e):
            return {}
        raise e


@papercut_core_wrapper
def load_staff_rfid_codes(topic=None, opaque=None, **kwargs):
    staffs = mstaff.staff_get_m()
    nbr_found = 0
    nbr_not_found = 0
    for staff in staffs:
        try:
            rfid = kwargs["server"].api.getUserProperty(kwargs["token"], staff.code, PROPERTY_RFID)
            staff.rfid = rfid.upper()
            log.info(f'{sys._getframe().f_code.co_name}, {staff.code} has rfid {rfid}')
            nbr_found += 1
        except:
            log.info(f'{sys._getframe().f_code.co_name}, {staff.code} is not present in papercut')
            nbr_not_found += 1
    log.info(f'{sys._getframe().f_code.co_name}: gevonden in papercut {nbr_found}, niet gevonden {nbr_not_found}')
    mstaff.commit()



msettings.subscribe_handle_button_clicked('papercut-load-rfid-event', load_staff_rfid_codes, None)