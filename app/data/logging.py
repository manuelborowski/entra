from app import log, db
import app.data.models
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import TEXT
from flask_login import current_user
import datetime


class Logging(db.Model, SerializerMixin):
    __tablename__ = 'logging'

    info = 0
    warning = 1
    error = 2

    levels = [
        [info, "INFO"],
        [warning, "WRSCH"],
        [error, "FOUT"]
    ]

    date_format = '%Y/%m/%d'
    datetime_format = '%Y/%m/%d %H:%M'

    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.String(256), default='')
    severity = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime())
    message = db.Column(TEXT, default='')
    visible = db.Column(db.Boolean, default=True)


class ULog:

    info = Logging.info
    warning = Logging.warning
    error = Logging.error

    def __init__(self, severity, line):
        self.__severity = severity
        self.__owner = current_user.username if current_user else "NONE"
        self.__timestamp = datetime.datetime.now()
        self.message = line
        self.__used = False

    def add(self, line):
        self.message += "<br>" + line
        self.__used = True

    def finish(self):
        if self.__used:
            warning = add({'message': self.message, "owner": self.__owner, "severity": self.__severity, 'timestamp': self.__timestamp})
            return warning
        return None


def add(data = {}, commit=True):
    return app.data.models.add_single(Logging, data, commit)


def update(warning, data={}, commit=True):
    return app.data.models.update_single(Logging, warning, data, commit)


def get_m(filters=[], fields=[], ids=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Logging, filters=filters, fields=fields, ids=ids, order_by=order_by, first=first, count=count, active=active)


def pre_sql_query():
    return db.session.query(Logging)


def pre_sql_filter(query, filter):
    for f in filter:
        if f['name'] == 'log-level':
            if f['value'] != 'default':
                query = query.filter(Logging.severity == int(f["value"]))
    return query


def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Logging.message.like(search_string))
    return search_constraints


def filter_data(query, filter):
    if 'visible' in filter and filter['visible'] != 'default':
        query = query.filter(Logging.visible == (filter['visible'] == 'True'))
    return query


def format_data(db_list):
    out = []
    for warning in db_list:
        em = warning.flat()
        em.update({
            'row_action': warning.id,
            'id': warning.id,
            'DT_RowId': warning.id
        })
        out.append(em)
    return out


