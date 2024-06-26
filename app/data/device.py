import sys, json, datetime

import app.data.models
from app import log, db
from sqlalchemy_serializer import SerializerMixin


class Device(db.Model, SerializerMixin):
    __tablename__ = 'devices'

    date_format = '%d/%m/%Y'
    datetime_format = '%d/%m/%Y %H:%M'


    id = db.Column(db.Integer(), primary_key=True)
    intune_id = db.Column(db.String(256), default='')
    entra_id = db.Column(db.String(256), default='')

    device_name = db.Column(db.String(256), default='')
    serial_number = db.Column(db.String(256), default='')
    enrolled_date = db.Column(db.DateTime)
    lastsync_date = db.Column(db.DateTime)

    user_entra_id = db.Column(db.String(256), default='')
    user_voornaam = db.Column(db.String(256), default='')
    user_naam = db.Column(db.String(256), default='')
    user_klascode = db.Column(db.String(256), default='')
    user_username = db.Column(db.String(256), default='')

    active = db.Column(db.Boolean, default=True)    # long term


def get_columns():
    return [p for p in dir(Device) if not p.startswith('_')]


def commit():
    return app.data.models.commit()


def device_add(data = {}, commit=True):
    return app.data.models.add_single(Device, data, commit)


def device_add_m(data=[]):
    return app.data.models.add_multiple(Device, data)


def device_update(student, data={}, commit=True):
    return app.data.models.update_single(Device, student, data, commit)


def device_delete_m(ids=[], devices=[]):
    return app.data.models.delete_multiple(Device, ids, devices)


def device_get_m(filters=[], fields=[], ids=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Device, filters=filters, fields=fields, ids=ids, order_by=order_by, first=first, count=count, active=active)


def device_get(filters=[]):
    return app.data.models.get_first_single(Device, filters)


############ student overview list #########
def pre_sql_query():
    return db.session.query(Device)


def pre_sql_filter(query, filter):
    return query


def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Device.device_name.like(search_string))
    search_constraints.append(Device.user_voornaam.like(search_string))
    search_constraints.append(Device.user_naam.like(search_string))
    search_constraints.append(Device.user_username.like(search_string))
    return search_constraints
