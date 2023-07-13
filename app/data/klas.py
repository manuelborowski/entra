import sys, json, datetime

import app.data.models
from app import log, db
from sqlalchemy import text, func, desc
from sqlalchemy_serializer import SerializerMixin


class Klas(db.Model, SerializerMixin):
    __tablename__ = 'klassen'

    date_format = '%d/%m/%Y'
    datetime_format = '%d/%m/%Y %H:%M'

    id = db.Column(db.Integer(), primary_key=True)

    instellingsnummer = db.Column(db.String(256), default='')
    klascode = db.Column(db.String(256), default='')
    klasgroepcode = db.Column(db.String(256), default='')
    administratievecode = db.Column(db.String(256), default='')
    klastitularis = db.Column(db.String(256), default='')
    schooljaar = db.Column(db.Integer(), default=-1)

    timestamp = db.Column(db.DateTime, default=datetime.datetime.now())

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term
    enable = db.Column(db.Boolean, default=True)    # short term
    changed = db.Column(db.TEXT, default='')


def commit():
    return app.data.models.commit()


def klas_add(data=None, commit=True):
    return app.data.models.add_single(Klas, data, commit)


def klas_add_m(data = []):
    return app.data.models.add_multiple(Klas, data)


def klas_update(student, data={}, commit=True):
    return app.data.models.update_single(Klas, student, data, commit)


def klas_delete_m(ids=[], students=[]):
    return app.data.models.delete_multiple(ids, students)


def klas_get_m(filters=[], fields=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Klas, filters=filters, fields=fields, order_by=order_by, first=first, count=count, active=active)


def klas_get(filters=[]):
    return app.data.models.get_first_single(Klas, filters)


# data is a list, with:
# klas: the ORM-student-object
# changed: a list of properties that are changed
# property#1: the first property changed
# property#2: ....
# overwrite: if True, overwrite the changed field, else extend the changed field
def klas_change_m(data=[], overwrite=False):
    try:
        for d in data:
            klas = d['klas']
            for property in d['changed']:
                v = d[property]
                if hasattr(klas, property):
                    if getattr(Klas, property).expression.type.python_type == type(v):
                        setattr(klas, property, v.strip() if isinstance(v, str) else v)
            # if the klas is new, do not set the changed flag in order not to confuse other modules that need to process the students (new has priority over changed)
            if klas.new:
                klas.changed = ''
            else:
                if overwrite:
                    klas.changed = json.dumps(d['changed'])
                else:
                    changed = json.loads(klas.changed) if klas.changed != '' else []
                    changed.extend(d['changed'])
                    changed = list(set(changed))
                    klas.changed = json.dumps(changed)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None

def klas_flag_m(data=[]):
    try:
        for d in data:
            klas = d['klas']
            for k, v in d.items():
                if hasattr(klas, k):
                    setattr(klas, k, v)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None




############ student overview list #########
def pre_sql_query():
    return db.session.query(Klas).filter(Klas.active == True)


def pre_sql_filter(query, filter):
    return query


def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Klas.klascode.like(search_string))
    search_constraints.append(Klas.klasgroepcode.like(search_string))
    search_constraints.append(Klas.administratievecode.like(search_string))
    search_constraints.append(Klas.instellingsnummer.like(search_string))
    search_constraints.append(Klas.klastitularis.like(search_string))
    return search_constraints
