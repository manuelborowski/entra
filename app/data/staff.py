import sys, json, datetime
from app import log, db
import app.data.models
from sqlalchemy import text, func, desc
from sqlalchemy_serializer import SerializerMixin


class Staff(db.Model, SerializerMixin):
    __tablename__ = 'staff'

    date_format = '%d/%m/%Y'
    datetime_format = '%d/%m/%Y %H:%M'
    serialize_rules = ("is_interim_text", "is_wisa_text",)

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
    profiel = db.Column(db.String(256), default="leerkracht")
    interim = db.Column(db.Boolean, default=False)
    extra = db.Column(db.TEXT, default='')
    einddatum = db.Column(db.Date)

    timestamp = db.Column(db.DateTime)

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term
    enable = db.Column(db.Boolean, default=True)    # short term
    changed = db.Column(db.TEXT, default='')

    def is_interim_text(self):
        return "JA" if self.interim else "NEE"

    def is_wisa_text(self):
        return "JA" if self.stamboeknummer !="" else "NEE"


def get_columns():
    return [p for p in dir(Staff) if not p.startswith('_')]


def commit():
    return app.data.models.commit()


def add_staff(data = {}, commit=True):
    data["timestamp"] = datetime.datetime.now()
    return app.data.models.add_single(Staff, data, commit)


def add_staffs(data = []):
    return app.data.models.add_multiple(Staff, data)


def update_staff(staff, data={}, commit=True):
    data["timestamp"] = datetime.datetime.now()
    return app.data.models.update_single(Staff, staff, data, commit)


def delete_staffs(ids=[], staffs=[]):
    return app.data.models.delete_multiple(ids, staffs)


def get_staffs(data={}, fields=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Staff, data=data, fields=fields, order_by=order_by, first=first, count=count, active=active)


def get_first_staff(data={}):
    return app.data.models.get_first_single(Staff, data)


# data is a list, with:
# staff: the ORM-staff-object
# changed: a list of properties that are changed
# property#1: the first property changed
# property#2: ....
def update_staffs(data = [], overwrite=False):
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


def flag_staffs(data = []):
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


############ staff overview list #########
def pre_sql_query():
    return db.session.query(Staff).filter(Staff.active == True)


def pre_sql_filter(query, filter):
    return query


def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Staff.naam.like(search_string))
    search_constraints.append(Staff.voornaam.like(search_string))
    return search_constraints

