from app import log, db
import sys, datetime
from babel.dates import get_day_names, get_month_names
from sqlalchemy import text, desc
from app.data import settings as msettings


# woensdag 24 februari om 14 uur
def datetime_to_dutch_datetime_string(date, include_seconds=False):
    try:
        time_string = f"%H.%M{':%S' if include_seconds else ''}"
        date_string = f'{get_day_names(locale="nl")[date.weekday()]} {date.day} {get_month_names(locale="nl")[date.month]} om {date.strftime(time_string)}'
        return date_string
    except:
        return ''

#24/2/2022 22:12:23
def datetime_to_dutch_short(date, include_seconds=False, include_time=True):
    try:
        in_string = "%d/%m/%Y"
        if include_time:
            in_string = f"{in_string} %H.%M{':%S' if include_seconds else ''}"
        return date.strftime(in_string)
    except:
        return ''


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def add(object):
    try:
        db.session.add(object)
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def add_single(model, data={}, commit=True):
    try:
        obj = model()
        for k, v in data.items():
            if hasattr(obj, k):
                if getattr(model, k).expression.type.python_type == type(v):
                    setattr(obj, k, v.strip() if isinstance(v, str) else v)
        db.session.add(obj)
        if commit:
            db.session.commit()
        return obj
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def add_multiple(model, data=[]):
    try:
        for d in data:
            add_single(model, d, commit=False)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def update_single(model, obj, data={}, commit=True):
    try:
        for k, v in data.items():
            if hasattr(obj, k):
                if getattr(model, k).expression.type.python_type == type(v) or isinstance(getattr(model, k).expression.type, db.Date) and v == None:
                    setattr(obj, k, v.strip() if isinstance(v, str) else v)
        if commit:
            db.session.commit()
        return obj
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def delete_multiple(model, ids=[], objs=[]):
    try:
        if ids:
            objs = get_multiple(model, ids=ids)
        for obj in objs:
            db.session.delete(obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None

# filters is list of tupples: [(key, operator, value), ...]
def get_multiple(model, filters=[], fields=[], ids=[], order_by=None, first=False, count=False, active=True, start=None, stop=None):
    try:
        tablename = model.__tablename__
        entities = [text(f'{tablename}.{f}') for f in fields]
        if entities:
            q = model.query.with_entities(*entities)
        else:
            q = model.query
        if type(filters) is not list:
            filters = [filters]
        for k, o, v in filters:
            if o == '!':
                if hasattr(model, k):
                    q = q.filter(getattr(model, k) != v)
            elif o == '>':
                if hasattr(model, k):
                    q = q.filter(getattr(model, k) > v)
            elif o == '<':
                if hasattr(model, k):
                    q = q.filter(getattr(model, k) < v)
            elif o == '>=':
                if hasattr(model, k):
                    q = q.filter(getattr(model, k) >= v)
            elif o == '=<':
                if hasattr(model, k):
                    q = q.filter(getattr(model, k) <= v)
            elif o == 'like':
                if hasattr(model, k):
                    q = q.filter(getattr(model, k).like(v))
            else:
                if hasattr(model, k):
                    q = q.filter(getattr(model, k) == v)
        if ids:
            q = q.filter(getattr(model, "id").in_(ids))
        if order_by:
            if order_by[0] == '-':
                q = q.order_by(desc(getattr(model, order_by[1::])))
            else:
                q = q.order_by(getattr(model, order_by))
        else:
            q = q.order_by(getattr(model, "id"))
        q = q.filter(model.active == active)
        if start is not None and stop is not None:
            q = q.slice(start, stop)
        if first:
            obj = q.first()
            return obj
        if count:
            return q.count()
        objs = q.all()
        return objs if objs else []
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_first_single(model, filters=[], order_by=None):
    try:
        obj = get_multiple(model, filters, order_by=order_by, first=True)
        return obj
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None



