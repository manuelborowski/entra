import sys, json
from app import log, db
from sqlalchemy import text, func, desc
from sqlalchemy_serializer import SerializerMixin


class Staff(db.Model, SerializerMixin):
    __tablename__ = 'staff'

    date_format = '%d/%m/%Y'
    datetime_format = '%d/%m/%Y %H:%M'

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
    rfid = db.Column(db.String(256))

    timestamp = db.Column(db.DateTime)

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term
    enable = db.Column(db.Boolean, default=True)    # short term
    changed = db.Column(db.TEXT, default='')


def get_columns():
    return [p for p in dir(Staff) if not p.startswith('_')]


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def add_staff(data = {}, commit=True):
    try:
        staff = Staff()
        for k, v in data.items():
            if hasattr(staff, k):
                if getattr(Staff, k).expression.type.python_type == type(v):
                    setattr(staff, k, v.strip() if isinstance(v, str) else v)
        db.session.add(staff)
        if commit:
            db.session.commit()
        return staff
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def add_staffs(data = []):
    try:
        for d in data:
            add_staff(d, commit=False)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


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


def delete_staffs(ids=[], staffs=[]):
    try:
        for id in ids:
            staff = get_first_staff({"id": id})
            db.session.delete(staff)
        for staff in staffs:
            db.session.delete(staff)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_staffs(data={}, fields=[], order_by=None, first=False, count=False, active=True):
    try:
        entities = [text(f'staff.{f}') for f in fields]
        if entities:
            q = Staff.query.with_entities(*entities)
        else:
            q = Staff.query
        for k, v in data.items():
            if k[0] == '-':
                if hasattr(Staff, k[1::]):
                    q = q.filter(getattr(Staff, k[1::]) != v)
            else:
                if hasattr(Staff, k):
                    q = q.filter(getattr(Staff, k) == v)
        if order_by:
            if order_by[0] == '-':
                q = q.order_by(desc(getattr(Staff, order_by[1::])))
            else:
                q = q.order_by(getattr(Staff, order_by))
        q = q.filter(Staff.active == active)
        if first:
            item = q.first()
            return item
        if count:
            return q.count()
        items = q.all()
        return items
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_first_staff(data={}):
    try:
        user = get_staffs(data, first=True)
        return user
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def update_staff(staff, data={}):
    try:
        for k, v in data.items():
            if hasattr(staff, k):
                if getattr(Staff, k).expression.type.python_type == type(v):
                    setattr(staff, k, v.strip() if isinstance(v, str) else v)
        db.session.commit()
        return staff
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

