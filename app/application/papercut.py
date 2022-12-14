from app import log, flask_app
from app.data import staff as mstaff, student as mstudent
from app.application import settings as msettings
import xmlrpc.client, sys
from functools import wraps

PROPERTY_RFID = 'primary-card-number'

user_properties = [
    "balance", "primary-card-number", "secondary-card-number", "department", "disabled-print", "email", "full-name", "internal", "notes", "office", "print-stats.job-count", "print-stats.page-count",
    "net-stats.data-mb", "net-stats.time-hours", "restricted", "home", "unauthenticated", "username-alias", "dont-hold-jobs-in-release-station"]


def papercut_core(func):
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
            log.error(f'PAPERCUT: {func.__name__}: {e}')
            raise Exception(f'PAPERCUT-EXCEPTION: {func.__name__}: {e}')
    return wrapper


# data is list of lists, e.g [["primary-card-number", "abcd1234"], ["office", "lkr"]]
@papercut_core
def user_update(obj, data, **kwargs):
    username = None
    if type(obj) is mstudent.Student:
        username = obj.username
    if type(obj) is mstaff.Staff:
        username = obj.code
    if username:
        ret = kwargs["server"].api.setUserProperties(kwargs["token"], username, data)
        log.info(f'Update to Papercut, {username} RFID {data}')
        return ret
    return False


@papercut_core
def user_add(username, **kwargs):
    a = 1 / 0
    ret = kwargs["server"].api.addNewUser(kwargs["token"], username)
    log.info(f'Add to papercut, {username}')
    return ret


@papercut_core
def user_get(username, **kwargs):
    try:
        ret = kwargs["server"].api.getUserProperties(kwargs["token"], username, user_properties)
        info = zip(user_properties, ret)
        return dict(info)
    except Exception as e:
        if "Fault 262" in str(e):
            return {}
        raise e


@papercut_core
def load_staff_rfid_codes(topic=None, opaque=None, **kwargs):
    staffs = mstaff.get_staffs()
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