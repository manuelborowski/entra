import datetime, sys, app.data.logging
from flask_login import current_user
from app.data.logging import Logging

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def new(severity, line):
    try:
        owner = current_user.username if current_user else "NONE"
        timestamp = datetime.datetime.now()
        warning = app.data.logging.add({'message': line, "owner": owner, "severity": severity, 'timestamp': timestamp})
        return warning
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def add_line(warning, line):
    try:
        warning = app.data.logging.update(warning, {"message": warning.message + "<br>" + line})
        return warning
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_log_levels():
    return Logging.levels


warning_updated_cbs = []
def subscribe_updated(cb, opaque):
    try:
        warning_updated_cbs.append((cb, opaque))
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def inform_warning_updated(type, value=None, opaque=None):
    for cb in warning_updated_cbs:
        cb[0](value, cb[1])


def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for warning in db_list:
        em = warning.to_dict()
        em.update({
            'row_action': warning.id,
            'DT_RowId': warning.id
        })
        out.append(em)
    return total_count, filtered_count, out



# w = new(Logging.info, "honderste eerste lijn")
# add_line(w, "honderd en tweede lijn")


# new_warning('test1')
# new_warning('test2')
# new_warning('Een extra lange test om te zien of het wel klopt wat er allemaal gezegd is geweest.  Ik denk het wel, maar toch')