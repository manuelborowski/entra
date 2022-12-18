import app.application.student
from app.data import user as muser, settings as msettings
import sys

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


class UserLevel(muser.User.LEVEL):
    pass


def api_user_add(data):
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
        raise Exception(f'USER-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


def api_user_update(data):
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
        raise Exception(f'USER-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


def api_user_delete(data):
    try:
        muser.delete_users(data)
        return {"status": True, "data": "Gebruikers zijn verwijderd"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise Exception(f'USER-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


def api_user_get(data):
    try:
        user = muser.get_first_user({'id': data['id']})
        return {"status": True, "data": user.to_dict()}
    except Exception as e:
        log.error(data)
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise Exception(f'USER-EXCEPTION {sys._getframe().f_code.co_name}: {e}')


def user_delete(ids):
    muser.delete_users(ids)


############## formio forms #############
def prepare_add_registration_form():
    try:
        template = msettings.get_configuration_setting('popup-new-update-user')
        return {'template': template,
                'defaults': {'new_password': True}}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def prepare_edit_registration_form(id):
    try:
        user = muser.get_first_user({"id": id})
        template = msettings.get_configuration_setting('popup-new-update-user')
        template = app.application.student.form_prepare_for_edit(template, user.to_dict())
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

