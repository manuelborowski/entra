import sys, json, datetime
from app import log, db
from sqlalchemy import func
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy_serializer import SerializerMixin


class Photo(db.Model, SerializerMixin):
    __tablename__ = 'photos'

    date_format = '%d/%m/%Y'
    datetime_format = '%d/%m/%Y %H:%M'

    id = db.Column(db.Integer(), primary_key=True)
    code = db.Column(db.String(256), default='')
    photo = db.Column(MEDIUMBLOB)
    timestamp = db.Column(db.DateTime)

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    enable = db.Column(db.Boolean, default=True)
    update = db.Column(db.Boolean, default=False)


def add_photo(data = {}, commit=True):
    try:
        photo = Photo()
        photo.code = data['code']
        photo.photo = data['photo']
        photo.timestamp = datetime.datetime.now()
        db.session.add(photo)
        if commit:
            db.session.commit()
        return photo
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def add_photos(data = []):
    try:
        for d in data:
            add_photo(d, commit=False)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def update_photo(code, data, commit=True):
    try:
        q = db.session.query(Photo)
        q = q.filter(Photo.code == code)
        data.update({'timestamp': datetime.datetime.now()})
        q.update(data)
        if commit:
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def update_wisa_photos(data = []):
    try:
        for d in data:
            photo = d['photo']
            for property in d['update']:
                v = d[property]
                if hasattr(photo, property):
                    if getattr(Photo, property).expression.type.python_type == type(v):
                        setattr(photo, property, v.strip() if isinstance(v, str) else v)
            photo.update = json.dumps(d['update'])
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def flag_wisa_photos(data = []):
    try:
        for d in data:
            photo = d['photo']
            photo.new = d['new']
            photo.update = d['update']
            photo.delete = d['delete']
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


# def get_photos_size():



def delete_photos(ids=None):
    try:
        for id in ids:
            photo = get_first_photo({"id": id})
            db.session.delete(photo)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_photos(data={}, special={}, order_by=None, first=False, count=False):
    try:
        q = Photo.query
        for k, v in data.items():
            if hasattr(Photo, k):
                q = q.filter(getattr(Photo, k) == v)
        if order_by:
            q = q.order_by(getattr(Photo, order_by))
        if first:
            guest = q.first()
            return guest
        if count:
            return q.count()
        guests = q.all()
        return guests
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_first_photo(data={}):
    try:
        user = get_photos(data, first=True)
        return user
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def get_photos_size():
    try:
        q = db.session.query(Photo.id, Photo.code, Photo.new, Photo.update, Photo.delete, func.octet_length(Photo.photo))
        q = q.all()
        return q
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


############ photo overview list #########
def pre_filter():
    return db.session.query(Photo)


def filter_data(query, filter):
    return query


def search_data(search_string):
    search_constraints = []
    search_constraints.append(Photo.naam.like(search_string))
    search_constraints.append(Photo.voornaam.like(search_string))
    return search_constraints

