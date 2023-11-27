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
    klascode = db.Column(db.String(256), default='')
    klasgroepcode = db.Column(db.String(256), default='')
    active = db.Column(db.Boolean, default=True)    # long term


def commit():
    return app.data.models.commit()


def klas_add(data=None, commit=True):
    return app.data.models.add_single(Klas, data, commit)


def klas_add_m(data = []):
    return app.data.models.add_multiple(Klas, data)


def klas_update(klas, data={}, commit=True):
    return app.data.models.update_single(Klas, klas, data, commit)


def klas_delete_m(ids=[], klassen=[]):
    return app.data.models.delete_multiple(Klas, ids, klassen)


def klas_get_m(filters=[], fields=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Klas, filters=filters, fields=fields, order_by=order_by, first=first, count=count, active=active)


def klas_get(filters=[]):
    return app.data.models.get_first_single(Klas, filters)
