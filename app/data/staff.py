import sys, json, datetime

import app.data.formio
from app import db
import app.data.models
from sqlalchemy import text, func, desc
from sqlalchemy_serializer import SerializerMixin
from app.data.formio import iso_datestring_to_date
from app.data import settings as msettings


#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


class Staff(db.Model, SerializerMixin):
    __tablename__ = 'staff'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'
    serialize_rules = ("is_interim_to_text", "is_wisa_to_text",)

    id = db.Column(db.Integer(), primary_key=True)

    voornaam = db.Column(db.String(256), default='')
    naam = db.Column(db.String(256), default='')
    rijksregisternummer = db.Column(db.String(256), default='')
    stamboeknummer = db.Column(db.String(256), default='')
    code = db.Column(db.String(256), default='')
    geslacht = db.Column(db.String(256), default='')
    geboortedatum = db.Column(db.Date)
    geboorteplaats = db.Column(db.String(256), default='')
    instellingsnummer = db.Column(db.String(256), default='')
    email = db.Column(db.String(256), default='')
    prive_email = db.Column(db.String(256), default='')
    rfid = db.Column(db.String(256), default='')
    profiel = db.Column(db.String(256), default='["lkr"]')
    interim = db.Column(db.Boolean, default=False)
    extra = db.Column(db.TEXT, default='')
    einddatum = db.Column(db.Date)

    timestamp = db.Column(db.DateTime)

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term
    enable = db.Column(db.Boolean, default=True)    # short term
    changed = db.Column(db.TEXT, default='')

    def is_interim_to_text(self):
        return "JA" if self.interim else "NEE"

    def is_wisa_to_text(self):
        return "JA" if self.stamboeknummer != "" else "NEE"

    @property
    def person_id(self):
        return self.code

    @property
    def einddatum_date(self):
        return self.einddatum


def get_columns():
    return [p for p in dir(Staff) if not p.startswith('_')]


def commit():
    return app.data.models.commit()


def staff_add(data = {}, commit=True):
    data["timestamp"] = datetime.datetime.now()
    return app.data.models.add_single(Staff, data, commit)


def staff_add_m(data = []):
    return app.data.models.add_multiple(Staff, data)


def staff_update(staff, data={}, commit=True):
    data["timestamp"] = datetime.datetime.now()
    return app.data.models.update_single(Staff, staff, data, commit)


def staff_delete_m(ids=[], staffs=[]):
    return app.data.models.delete_multiple(ids, staffs)


def staff_get_m(data={}, fields=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Staff, data=data, fields=fields, order_by=order_by, first=first, count=count, active=active)


def staff_get(data={}):
    return app.data.models.get_first_single(Staff, data)


# data is a list, with:
# staff: the ORM-staff-object
# changed: a list of properties that are changed
# property#1: the first property changed
# property#2: ....
def staff_update_m(data = [], overwrite=False):
    try:
        for d in data:
            staff = d['staff']
            for property in d['changed']:
                v = d[property]
                if hasattr(staff, property):
                    if getattr(Staff, property).expression.type.python_type == type(v):
                        setattr(staff, property, v.strip() if isinstance(v, str) else v)
            # if the staff is new, do not set the changed flag in order not to confuse other modules that need to process the staffs (new has priority over changed)
            if staff.new:
                staff.changed = ''
            else:
                if overwrite:
                    staff.changed = json.dumps(d['changed'])
                else:
                    changed = json.loads(staff.changed) if staff.changed != '' else []
                    changed.extend(d['changed'])
                    changed = list(set(changed))
                    staff.changed = json.dumps(changed)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def staff_flag_m(data = []):
    try:
        for d in data:
            staff = d['staff']
            for k, v in d.items():
                if hasattr(staff, k):
                    setattr(staff, k, v)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def profiel_to_groepen(profiel):
    profile_settings = msettings.get_configuration_setting("ad-staff-profiles")
    groepen = set()
    for p in profile_settings:
        if p[0] in profiel:
            groepen |= set(p[2])
    return list(groepen)


# massage the incoming data
def massage_data(data):
    try:
        if "profiel" in data:
            data["profiel"] = json.dumps(data["profiel"])
        if "einddatum" in data:
            data['einddatum'] = iso_datestring_to_date(data['einddatum'])
        if "interim" in data and not data["interim"]:
            data["einddatum"] = None
        return data
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


############ staff overview list #########
def pre_sql_query():
    return db.session.query(Staff).filter(Staff.active == True)


def pre_sql_filter(query, filter):
    return query


def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Staff.naam.like(search_string))
    search_constraints.append(Staff.voornaam.like(search_string))
    search_constraints.append(Staff.code.like(search_string))
    return search_constraints


