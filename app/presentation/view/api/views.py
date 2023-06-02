from flask import request, render_template
from . import api
from app.application import  student as mstudent, user as muser, photo as mphoto, staff as mstaff, settings as msettings, cardpresso as mcardpresso
from app import log
import json, sys, html, itertools
from functools import wraps


def api_core(api_level, func, *args, **kwargs):
    try:
        all_keys = msettings.get_configuration_setting('api-keys')
        header_key = request.headers.get('x-api-key')
        if request.headers.get("X-Forwarded-For"):
            remote_ip = request.headers.get("X-Forwarded-For")
        else:
            remote_ip = request.remote_addr
        for i, keys_per_level in  enumerate(all_keys[(api_level - 1)::]):
            if header_key in keys_per_level:
                key_level = api_level + i
                log.info(f"API access by '{keys_per_level[header_key]}', keylevel {key_level}, from {remote_ip}, URI {request.url}")
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    log.error(f'{func.__name__}: {e}')
                    return json.dumps({"status": False, "data": f'API-EXCEPTION {func.__name__}: {html.escape(str(e))}'})
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return json.dumps({"status": False, "data": html.escape(str(e))})
    log.error(f"API, API key not valid, {header_key}, from {remote_ip} , URI {request.url}")
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
    ret = muser.api_user_add(data)
    return(json.dumps(ret))


@api.route('/api/user/update', methods=['POST'])
@admin_key_required
def user_update():
    data = json.loads(request.data)
    ret = muser.api_user_update(data)
    return(json.dumps(ret))


@api.route('/api/user/delete', methods=['POST'])
@admin_key_required
def user_delete():
    data = json.loads(request.data)
    ret = muser.api_user_delete(data)
    return(json.dumps(ret))


@api.route('/api/user/get', methods=['GET'])
@admin_key_required
def user_get():
    options = request.args
    ret = muser.api_user_get(options)
    return(json.dumps(ret))


@api.route('/api/photo/get', methods=['GET'])
@user_key_required
def photo_get():
    ids = []
    if "ids" in request.args:
        ids = request.args["ids"].split(",")
    ret = mphoto.api_photo_get_m(ids)
    return (json.dumps(ret))


@api.route('/api/photo/sizes', methods=['GET'])
@user_key_required
def photo_sizes_get():
    ids = []
    if "ids" in request.args:
        ids = request.args["ids"].split(",")
    ret = mphoto.api_photo_get_size_m(ids)
    return (json.dumps(ret))


@api.route('/api/vsknumber/get', methods=['GET'])
@user_key_required
def get_last_vsk_number():
    ret = mstudent.vsk_get_next_number()
    return json.dumps(ret)


@api.route('/api/vsknumber/update', methods=['POST'])
@admin_key_required
def update_vsk_number():
    data = json.loads(request.data)
    ret = mstudent.vsk_update_numbers(int(data['start']))
    return json.dumps(ret)


@api.route('/api/vsknumber/clear', methods=['POST'])
@admin_key_required
def clear_vsk_numbers():
    ret = mstudent.vsk_clear_numbers()
    return json.dumps(ret)


@api.route('/api/fields/', methods=['GET'])
@api.route('/api/fields/<string:table>', methods=['GET'])
@user_key_required
def get_fields(table=''):
    ret = {"status": True, "data": "Command not understood"}
    if table == '':
        ret = {"status": True, "data": ['student', 'staff']}
    elif table == 'student':
        ret = {"status": True, "data": mstudent.api_student_get_fields()}
    elif table == 'staff':
        ret = {"status": True, "data": mstaff.api_staff_get_fields()}
    return json.dumps(ret)


@api.route('/api/student/get', methods=['GET'])
@user_key_required
def student_get():
    options = request.args
    ret = mstudent.api_student_get(options)
    return json.dumps(ret, ensure_ascii=False)


@api.route('/api/student/fields', methods=['GET'])
@user_key_required
def student_fields():
    ret = {"status": True, "data": mstudent.api_student_get_fields()}
    return json.dumps(ret, ensure_ascii=False)


@api.route('/api/student/update', methods=['POST'])
@supervisor_key_required
def student_update():
    data = json.loads(request.data)
    ret = mstudent.api_student_update(data)
    return json.dumps(ret, ensure_ascii=False)


@api.route('/api/staff/get', methods=['GET'])
@user_key_required
def staff_get():
    options = request.args
    ret = mstaff.api_staff_get(options)
    return json.dumps(ret, ensure_ascii=False)


@api.route('/api/staff/fields', methods=['GET'])
@user_key_required
def staff_fields():
    ret = {"status": True, "data": mstaff.api_staff_get_fields()}
    return json.dumps(ret, ensure_ascii=False)


@api.route('/api/staff/add', methods=['POST'])
@supervisor_key_required
def staff_add():
    data = json.loads(request.data)
    ret = mstaff.api_staff_add(data)
    return(json.dumps(ret))


@api.route('/api/staff/update', methods=['POST'])
@supervisor_key_required
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
    ret = mstudent.api_database_integrity_check(data)
    return json.dumps(ret)


@api.route('/api/cardpresso/delete', methods=['POST'])
@supervisor_key_required
def carpresso_delete():
    data = json.loads(request.data)
    ret = mcardpresso.badge_delete(data)
    return(json.dumps(ret))




# ?fields=klasgroep,schooljaar
# sort=-gemeente
# gemeente=nijlen   filter on gemeente equals nijlen

@api.route('/api/info/', methods=['GET'])
def get_info():
    info_page = msettings.get_configuration_setting("api-info-page")
    return info_page

