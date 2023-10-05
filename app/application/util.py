import random, string, sys
from app.data import utils as mutils, settings as msettings

import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def datetime_to_dutch_datetime_string(date):
    return mutils.datetime_to_dutch_datetime_string(date)


def create_random_string(len=32):
    return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(len))


# If the roepnaam is filled in and it is different from the voornaam, then the roepnaam is used
def get_student_voornaam(student):
    if student.roepnaam != '' and student.roepnaam != student.voornaam:
        return student.roepnaam
    return student.voornaam


def deepcopy(table):
    if type(table) == dict:
        out = {}
        for k, v in table.items():
            if type(v) == list or type(v) == dict:
                out[k] = deepcopy(v)
            else:
                out[k] = v
    elif type(table) == list:
        out = []
        for i in table:
            if type(i) == list or type(i) == dict:
                out.append(deepcopy(i))
            else:
                out.append(i)
    else:
        out = table
    return out


# in text, find tags and replace with values
# data: dict (tag: value, tag: value, ...)
def find_and_replace(text, data):
    for tag, value in data.items():
        text = text.replace(tag, value)
    return text


PWD_ALLOWED_CHARS = [
    ["a","b","c","d","e","f","g","h","i","j","k","m","n","p","q","r","s","t","u","v","w","x","y","z"],
    ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","P","Q","R","S","T","U","V","W","X","Y","Z"],
    ["1","2","3","4","5","6","7","8","9", "_","!","?","/"]
]

def ss_create_password(seed, length=8, use_standard_password=False):
    try:
        if use_standard_password:
            default_password = msettings.get_configuration_setting('generic-standard-password')
            return default_password
        else:
            a = pow(seed, 5)
            b = 0
            pwd1 = ""
            while a > 0:
                l = len(PWD_ALLOWED_CHARS[b])
                c = a % l
                a = (a - c) / l
                pwd1 += PWD_ALLOWED_CHARS[b][int(c)]
                b += 1
                if b > 2:
                    b = 0
            return pwd1[:length]
    except Exception as e:
        log.error(f"{sys._getframe().f_code.co_name}, error {e}")


def get_keys(level, tag="local"):
    api_keys = msettings.get_configuration_setting('api-keys')[level - 1]
    api_keys = [k for k, v in api_keys.items() if v == tag]
    return api_keys
