import datetime, socket

from sqlalchemy import desc

import app.data.settings
from app import flask_app, log, data, db
from app.data import models as mmodels


def datetime_to_dutch_datetime_string(date, include_seconds=False):
    return mmodels.datetime_to_dutch_datetime_string(date, include_seconds=include_seconds)


def raise_error(message, details=None):
    error = Exception(f'm({message}), d({details}), td({type(details).__name__})')
    raise error


# standardized way to make a key from strings: sort alphabetically and concatenate
def make_key(item_list):
    return make_list(item_list, seperator=',')


def extend_key(item1, item2=None):
    if isinstance(item1, list):
        return ','.join(item1)
    return ','.join([item1, item2])


# standardized way to concatenate strings: sort alphabetically and concatenate; seperated by comma
def make_list(item_list, seperator=', '):
    return seperator.join(sorted(item_list))

# format returns the schoolyear in a certain format, e.g. for the schoolyear 2023-2024, format:
# 1: return 2023 (string)
# 2: return 2023-24 (string)
# 3: return 2023-2024 (string)
def get_current_schoolyear(format=1):
    auto_schoolyear = app.data.settings.get_configuration_setting("sdh-auto-current-schoolyear")
    if auto_schoolyear:
        now = datetime.datetime.now()
        schoolyear = now.year - 1 if now.month <= 8 else now.year
    else:
        schoolyear = app.data.settings.get_configuration_setting("sdh-select-current-schoolyear")
    if format == 2:
        return f"{schoolyear}-{schoolyear - 2000 + 1}"
    elif format == 3:
        return f"{schoolyear}-{schoolyear + 1}"
    return str(schoolyear)



def get_testmode():
    current_server = socket.gethostname()
    configured_server = app.data.settings.get_configuration_setting("generic-servername")
    return current_server != configured_server
