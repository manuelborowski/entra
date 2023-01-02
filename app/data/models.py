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


class Warning(db.Model):
    __tablename__ = 'warnings'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime())
    message = db.Column(db.String(4096), default='')
    visible = db.Column(db.Boolean, default=True)

    def flat(self):
        return {
            'id': self.id,
            'visible': self.visible,
            'timestamp_dutch': datetime_to_dutch_datetime_string(self.timestamp),
            'message': self.message
        }


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def add_single(model, data = {}, commit=True):
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


def add_multiple(model, data = []):
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


def delete_multiple(ids=[], objs=[]):
    try:
        for id in ids:
            obj = get_first_single({"id": id})
            db.session.delete(obj)
        for obj in objs:
            db.session.delete(obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_multiple(model, data={}, fields=[], order_by=None, first=False, count=False, active=True):
    try:
        tablename = model.__tablename__
        entities = [text(f'{tablename}.{f}') for f in fields]
        if entities:
            q = model.query.with_entities(*entities)
        else:
            q = model.query
        for k, v in data.items():
            if k[0] == '-':
                if hasattr(model, k[1::]):
                    q = q.filter(getattr(model, k[1::]) != v)
            else:
                if hasattr(model, k):
                    q = q.filter(getattr(model, k) == v)
        if order_by:
            if order_by[0] == '-':
                q = q.order_by(desc(getattr(model, order_by[1::])))
            else:
                q = q.order_by(getattr(model, order_by))
        q = q.filter(model.active == active)
        if first:
            obj = q.first()
            return obj
        if count:
            return q.count()
        objs = q.all()
        return objs
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_first_single(model, data={}, order_by=None):
    try:
        obj = get_multiple(model, data, order_by=order_by, first=True)
        return obj
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None



