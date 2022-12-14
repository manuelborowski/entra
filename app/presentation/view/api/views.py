from flask import request
from . import api
from app.application import  student as mstudent, user as muser, photo as mphoto, staff as mstaff, settings as msettings, cardpresso as mcardpresso
from app import log
import json, sys, html, itertools
from functools import wraps


def api_core(level, func, *args, **kwargs):
    try:
        all_keys = msettings.get_configuration_setting('api-keys')
        keys = list(itertools.chain.from_iterable(all_keys[(level-1)::]))
        if request.headers.get('x-api-key') in keys:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.error(f'{func.__name__}: {e}')
                return json.dumps({"status": False, "data": f'API-EXCEPTION {func.__name__}: {html.escape(str(e))}'})
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return json.dumps({"status": False, "data": html.escape(str(e))})
    return json.dumps({"status": False, "data": f'API key not valid'})


def user_key_required(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return api_core(muser.UserLevel.USER, func, *args, **kwargs)
        return wrapper


def supervisor_key_required(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return api_core(muser.UserLevel.SUPERVISOR, func, *args, **kwargs)
        return wrapper


def admin_key_required(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return api_core(muser.UserLevel.ADMIN, func, *args, **kwargs)
        return wrapper


@api.route('/api/user/add', methods=['POST'])
@admin_key_required
def user_add():
    data = json.loads(request.data)
    ret = muser.add_user(data)
    return(json.dumps(ret))


@api.route('/api/user/update', methods=['POST'])
@admin_key_required
def user_update():
    data = json.loads(request.data)
    ret = muser.update_user(data)
    return(json.dumps(ret))


@api.route('/api/user/delete', methods=['POST'])
@admin_key_required
def user_delete():
    data = json.loads(request.data)
    ret = muser.delete_user(data)
    return(json.dumps(ret))


@api.route('/api/user/get', methods=['GET'])
@admin_key_required
def user_get():
    options = request.args
    ret = muser.get_user(options)
    return(json.dumps(ret))


@api.route('/api/photo/get/<int:id>', methods=['GET'])
@user_key_required
def photo_get(id):
    ret = mphoto.get_photo(id)
    return ret


@api.route('/api/vsknumber/get', methods=['GET'])
@user_key_required
def get_last_vsk_number():
    ret = mstudent.get_next_vsk_number()
    return json.dumps(ret)


@api.route('/api/vsknumber/update', methods=['POST'])
@admin_key_required
def update_vsk_number():
    data = json.loads(request.data)
    ret = mstudent.update_vsk_numbers(int(data['start']))
    return json.dumps(ret)


@api.route('/api/vsknumber/clear', methods=['POST'])
@admin_key_required
def clear_vsk_numbers():
    ret = mstudent.clear_vsk_numbers()
    return json.dumps(ret)


@api.route('/api/fields/', methods=['GET'])
@api.route('/api/fields/<string:table>', methods=['GET'])
@user_key_required
def get_fields(table=''):
    ret = {"status": True, "data": "Command not understood"}
    if table == '':
        ret = {"status": True, "data": ['students', 'staffs']}
    elif table == 'students':
        ret = {"status": True, "data": mstudent.get_fields()}
    elif table == 'staffs':
        ret = {"status": True, "data": mstaff.api_fields_get()}
    return json.dumps(ret)


@api.route('/api/student/get', methods=['GET'])
@user_key_required
def student_get():
    a= 1 / 0
    options = request.args
    ret = mstudent.api_get_students(options)
    return json.dumps(ret, ensure_ascii=False)


@api.route('/api/student/update', methods=['POST'])
@admin_key_required
def student_update():
    data = json.loads(request.data)
    mstudent.update_student(data)
    return json.dumps({"status": True, "data": 'ok'})


@api.route('/api/staff/get', methods=['GET'])
@user_key_required
def staff_get():
    options = request.args
    ret = mstaff.api_staff_get(options)
    return json.dumps(ret, ensure_ascii=False)


@api.route('/api/staff/add', methods=['POST'])
@admin_key_required
def staff_add():
    data = json.loads(request.data)
    ret = mstaff.api_staff_add(data)
    return(json.dumps(ret))


@api.route('/api/staff/update', methods=['POST'])
@admin_key_required
def staff_update():
    data = json.loads(request.data)
    ret = mstaff.api_staff_update(data)
    return(json.dumps(ret))


@api.route('/api/staff/delete', methods=['POST'])
@admin_key_required
def staff_delete():
    data = json.loads(request.data)
    ret = mstaff.api_staff_delete(data)
    return(json.dumps(ret))


@api.route('/api/admin/dic', methods=['POST'])
@admin_key_required
def database_integrity_check():
    data = json.loads(request.data)
    ret = mstudent.database_integrity_check(data)
    return json.dumps(ret)


@api.route('/api/cardpresso/delete', methods=['POST'])
@supervisor_key_required
def carpresso_delete():
    data = json.loads(request.data)
    ret = mcardpresso.delete_badges(data)
    return(json.dumps(ret))




# ?fields=klasgroep,schooljaar
# sort=-gemeente
# gemeente=nijlen   filter on gemeente equals nijlen

