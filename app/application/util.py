import random, string
from app.data import utils as mutils


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