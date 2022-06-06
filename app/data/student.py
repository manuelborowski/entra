import sys, json
from app import log, db
from sqlalchemy import text, func, desc
from sqlalchemy_serializer import SerializerMixin


class Student(db.Model, SerializerMixin):
    __tablename__ = 'students'

    date_format = '%d/%m/%Y'
    datetime_format = '%d/%m/%Y %H:%M'

    id = db.Column(db.Integer(), primary_key=True)

    voornaam = db.Column(db.String(256), default='')
    naam = db.Column(db.String(256), default='')
    rijksregisternummer = db.Column(db.String(256), default='')
    stamboeknummer = db.Column(db.String(256), default='')
    leerlingnummer = db.Column(db.String(256), default='')
    middag = db.Column(db.String(256), default='')
    vsknummer = db.Column(db.String(256), default='')
    rfid = db.Column(db.String(256))
    foto = db.Column(db.String(256), default='')

    geboortedatum = db.Column(db.Date)
    geboorteplaats = db.Column(db.String(256), default='')
    geboorteland = db.Column(db.String(256), default='')
    geslacht = db.Column(db.String(256), default='')
    nationaliteit = db.Column(db.String(256), default='')
    straat = db.Column(db.String(256), default='')
    huisnummer = db.Column(db.String(256), default='')
    busnummer = db.Column(db.String(256), default='')
    postnummer = db.Column(db.String(256), default='')
    gemeente = db.Column(db.String(256), default='')
    telefoonnummer = db.Column(db.String(256), default='')
    gsm = db.Column(db.String(256), default='')
    email = db.Column(db.String(256), default='')


    inschrijvingsdatum = db.Column(db.Date)

    schooljaar = db.Column(db.String(256), default='')
    instellingsnummer = db.Column(db.String(256), default='')
    schoolnaam = db.Column(db.String(256), default='')
    klascode = db.Column(db.String(256), default='')
    klasgroep = db.Column(db.String(256), default='')
    adminstratievecode = db.Column(db.String(256), default='')
    klastitularis = db.Column(db.String(256), default='')
    klasnummer = db.Column(db.Integer(), default=0)

    naamcorrespondentieadres = db.Column(db.String(256), default='')
    aansprekingcorrespondentieadres = db.Column(db.String(256), default='')
    straatcorrespondentieadres = db.Column(db.String(256), default='')
    huisnummercorrespondentieadres = db.Column(db.String(256), default='')
    busnummercorrespondentieadres = db.Column(db.String(256), default='')
    postnummercorrespondentieadres = db.Column(db.String(256), default='')
    woonplaatscorrespondentieadres = db.Column(db.String(256), default='')
    landwoonplaats = db.Column(db.String(256), default='')

    mo_naam = db.Column(db.String(256), default='')
    mo_voornaam = db.Column(db.String(256), default='')
    mo_gsm = db.Column(db.String(256), default='')
    mo_email = db.Column(db.String(256), default='')
    mo_straat = db.Column(db.String(256), default='')
    mo_straat_nr = db.Column(db.String(256), default='')
    mo_straat_bus = db.Column(db.String(256), default='')
    mo_postcode = db.Column(db.String(256), default='')
    mo_gemeente = db.Column(db.String(256), default='')

    va_naam = db.Column(db.String(256), default='')
    va_voornaam = db.Column(db.String(256), default='')
    va_gsm = db.Column(db.String(256), default='')
    va_email = db.Column(db.String(256), default='')
    va_straat = db.Column(db.String(256), default='')
    va_straat_nr = db.Column(db.String(256), default='')
    va_straat_bus = db.Column(db.String(256), default='')
    va_postcode = db.Column(db.String(256), default='')
    va_gemeente = db.Column(db.String(256), default='')

    vo_naam = db.Column(db.String(256), default='')
    vo_voornaam = db.Column(db.String(256), default='')
    vo_straat = db.Column(db.String(256), default='')
    vo_straat_nr = db.Column(db.String(256), default='')
    vo_straat_bus = db.Column(db.String(256), default='')
    vo_postcode = db.Column(db.String(256), default='')
    vo_gemeente = db.Column(db.String(256), default='')

    timestamp = db.Column(db.DateTime)

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term
    enable = db.Column(db.Boolean, default=True)    # short term
    changed = db.Column(db.TEXT, default='')

def get_columns():
    return [p for p in dir(Student) if not p.startswith('_')]


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def add_student(data = {}, commit=True):
    try:
        student = Student()
        for k, v in data.items():
            if hasattr(student, k):
                if getattr(Student, k).expression.type.python_type == type(v):
                    setattr(student, k, v.strip() if isinstance(v, str) else v)
        db.session.add(student)
        if commit:
            db.session.commit()
        return student
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def add_students(data = []):
    try:
        for d in data:
            add_student(d, commit=False)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def update_student(student, data={}):
    try:
        for k, v in data.items():
            if hasattr(student, k):
                if getattr(Student, k).expression.type.python_type == type(v):
                    setattr(student, k, v.strip() if isinstance(v, str) else v)
        db.session.commit()
        return student
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None

# data is a list, with:
# student: the ORM-student-object
# changed: a list of properties that are changed
# property#1: the first property changed
# property#2: ....
def update_students(data = [], overwrite=False):
    try:
        for d in data:
            student = d['student']
            for property in d['changed']:
                v = d[property]
                if hasattr(student, property):
                    if getattr(Student, property).expression.type.python_type == type(v):
                        setattr(student, property, v.strip() if isinstance(v, str) else v)
            if overwrite:
                student.changed = json.dumps(d['changed'])
            else:
                changed = json.loads(student.changed) if student.changed != '' else []
                changed.extend(d['changed'])
                changed = list(set(changed))
                student.changed = json.dumps(changed)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def flag_wisa_students(data = []):
    try:
        for d in data:
            student = d['student']
            for k, v in d.items():
                if hasattr(student, k):
                    setattr(student, k, v)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def delete_students(ids=None):
    try:
        for id in ids:
            student = get_first_student({"id": id})
            db.session.delete(student)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_students(data={}, order_by=None, first=False, count=False, active=True):
    try:
        q = Student.query
        for k, v in data.items():
            if k[0] == '-':
                if hasattr(Student, k[1::]):
                    q = q.filter(getattr(Student, k[1::]) != v)
            else:
                if hasattr(Student, k):
                    q = q.filter(getattr(Student, k) == v)
        if order_by:
            if order_by[0] == '-':
                q = q.order_by(desc(getattr(Student, order_by[1::])))
            else:
                q = q.order_by(getattr(Student, order_by))
        q = q.filter(Student.active == active)
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


def get_first_student(data={}):
    try:
        user = get_students(data, first=True)
        return user
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None



############ student overview list #########
def pre_filter():
    return db.session.query(Student).filter(Student.active == True)


def filter_data(query, filter):
    return query


def search_data(search_string):
    search_constraints = []
    search_constraints.append(Student.naam.like(search_string))
    search_constraints.append(Student.voornaam.like(search_string))
    return search_constraints

