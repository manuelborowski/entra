import sys, json
from app import log, db
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy import delete
import app.data.models

class Cardpresso(db.Model, SerializerMixin):
    __tablename__ = 'cardpresso'

    date_format = '%d/%m/%Y'
    datetime_format = '%d/%m/%Y %H:%M'
    serialize_rules = ('-photo',)

    id = db.Column(db.Integer(), primary_key=True)

    voornaam = db.Column(db.String(256), default='')
    naam = db.Column(db.String(256), default='')
    leerlingnummer = db.Column(db.String(256), default='')
    klascode = db.Column(db.String(256), default='')
    middag = db.Column(db.String(256), default='')
    vsknummer = db.Column(db.String(256), default='')
    rfid = db.Column(db.String(256), default = '')
    geboortedatum = db.Column(db.String(256), default='')
    straat = db.Column(db.String(256), default='')
    huisnummer = db.Column(db.String(256), default='')
    busnummer = db.Column(db.String(256), default='')
    gemeente = db.Column(db.String(256), default='')
    photo = db.Column(MEDIUMBLOB)
    schoolnaam = db.Column(db.String(256), default='')
    schooljaar = db.Column(db.String(256), default='')

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    enable = db.Column(db.Boolean, default=True)
    changed = db.Column(db.TEXT, default='')


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')

def badge_add(data={}, commit=True):
    return app.data.models.add_single(Cardpresso, data, commit)


def badge_add_m(data=[]):
    return app.data.models.add_multiple(Cardpresso, data)


def badge_delete(ids=[], badges=[]):
    return app.data.models.delete_multiple(Cardpresso, ids, badges)


def badge_get_m(filters=[], fields=[], ids=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Cardpresso, filters=filters, fields=fields, ids=ids, order_by=order_by, first=first, count=count, active=active)


def badge_get(filters=[]):
    return app.data.models.get_first_single(Cardpresso, filters)



############ student overview list #########
def pre_filter():
    return db.session.query(Cardpresso)


def filter_data(query, filter):
    for f in filter:
        if f['name'] == 'filter-klas':
            if f['value'] != 'default':
                query = query.filter(Cardpresso.klascode == f['value'])
        if f['name'] == 'filter-klasgroep':
            if f['value'] != 'default':
                query = query.filter(Cardpresso.klascode.in_(f['value'].split(",")))
    return query


def search_data(search_string):
    search_constraints = []
    search_constraints.append(Cardpresso.naam.like(search_string))
    search_constraints.append(Cardpresso.voornaam.like(search_string))
    search_constraints.append(Cardpresso.leerlingnummer.like(search_string))
    search_constraints.append(Cardpresso.klascode.like(search_string))
    search_constraints.append(Cardpresso.middag.like(search_string))
    return search_constraints

