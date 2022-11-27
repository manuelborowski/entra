from app import log
from app.application import formio as mformio
from app.data import user as muser, settings as msettings
import sys


class UserLevel(muser.User.LEVEL):
    pass


def add_user(data):
    try:
        user = muser.get_first_user({'username': data['username']})
        if user:
            log.error(f'Error, user {user.username} already exists')
            return {"status": False, "data": f'Fout, gebruiker {user.username} bestaat al'}
        user = muser.add_user(data)
        if 'confirm_password' in data:
            del data['confirm_password']
        if 'password' in data:
            del data['password']
        log.info(f"Add user: {data}")
        return {"status": True, "data": {'id': user.id}}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(data)
        return {"status": False, "data": f'generic error {e}'}


def update_user(data):
    try:
        user = muser.get_first_user({'id': data['id']})
        if user:
            del data['id']
            user = muser.update_user(user, data)
            if user:
                if 'confirm_password' in data:
                    del data['confirm_password']
                if 'password' in data:
                    del data['password']
                log.info(f"Update user: {data}")
                return {"status": True, "data": {'id': user.id}}
        return {"status": False, "data": "Er is iets fout gegaan"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(data)
        return {"status": False, "data": f'generic error {e}'}


def delete_user(data):
    try:
        muser.delete_users(data)
        return {"status": True, "data": "Gebruikers zijn verwijderd"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(data)
        return {"status": False, "data": f'generic error {e}'}


def get_user(data):
    try:
        user = muser.get_first_user({'id': data['id']})
        return {"status": True, "data": user.to_dict()}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(data)
        return {"status": False, "data": f'generic error {e}'}


def delete_users(ids):
    muser.delete_users(ids)


############## formio forms #############
def prepare_add_registration_form():
    try:
        template = msettings.get_configuration_setting('user-formio-template')
        return {'template': template,
                'defaults': {'new_password': True}}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def prepare_edit_registration_form(id):
    try:
        user = muser.get_first_user({"id": id})
        template = msettings.get_configuration_setting('user-formio-template')
        template = mformio.prepare_for_edit(template, user.to_dict())
        return {'template': template,
                'defaults': user.to_dict()}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


############ user overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for i in db_list:
        em = i.to_dict()
        em.update({"row_action": i.id, "DT_RowId": i.id})
        out.append(em)
    return  total_count, filtered_count, out

