from flask import request, render_template
from app.application import  user as muser, settings as msettings
from app import log
import json, sys, html, itertools
from functools import wraps
from . import api
from app.application.warning import warning_get_message


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
                log.info(f"API access by '{keys_per_level[header_key]}', keylevel {key_level}, from {remote_ip}, URI {request.url[:150]}")
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


@api.route('/api/warning/get', methods=['GET'])
def get_warning():
    warning = warning_get_message()
    return json.dumps({"message": warning})

