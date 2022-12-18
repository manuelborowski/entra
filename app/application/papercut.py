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


# data is list of lists, e.g [["primary-card-number", "abcd1234"], ["office", "lkr"]]
@papercut_core_wrapper
def user_update(user_obj, data, **kwargs):
    update_properties = []
    if "rfid" in data:
        update_properties.append(["primary-card-number", data["rfid"]])
    if update_properties:
        ret = kwargs["server"].api.setUserProperties(kwargs["token"], user_obj.user_id, update_properties)
        log.info(f'Update to Papercut, {user_obj.user_id} RFID {update_properties}')
        return ret
    return True


@papercut_core_wrapper
def user_add(user_obj, **kwargs):
    ret = kwargs["server"].api.addNewUser(kwargs["token"], user_obj.user_id)
    log.info(f'Add to papercut, {user_obj.user_id}')
    return ret


@papercut_core_wrapper
def user_delete(user_objs, **kwargs):
    for user_obj in user_objs:
        try:
            ret = kwargs["server"].api.deleteExistingUser(kwargs["token"], user_obj.user_id, True)
            log.info(f'Delete from papercut, {user_obj.user_id}, result {ret}')
        except Exception as e:
            if "Fault 262" in str(e):
                log.info(f'user, {user_obj.user_id}, not found in Papercut')
    return True


@papercut_core_wrapper
def user_get(user_id, **kwargs):
    try:
        ret = kwargs["server"].api.getUserProperties(kwargs["token"], user_id, papercut_properties)
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