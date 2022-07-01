import re
import sys

from flask_login import current_user
from app import log, db
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
import json


class Settings(db.Model):
    __tablename__ = 'settings'

    class SETTING_TYPE:
        E_INT = 'INT'
        E_STRING = 'STRING'
        E_FLOAT = 'FLOAT'
        E_BOOL = 'BOOL'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    value = db.Column(MEDIUMTEXT)
    type = db.Column(db.String(256))
    user_id = db.Column(db.Integer)

    UniqueConstraint('name', 'user_id')

    def log(self):
        return '<Setting: {}/{}/{}/{}>'.format(self.id, self.name, self.value, self.type)



# return: found, value
# found: if True, setting was found else not
# value ; if setting was found, returns the value
def get_setting(name, id=-1):
    try:
        setting = Settings.query.filter_by(name=name, user_id=id if id > -1 else current_user.id).first()
        if setting.type == Settings.SETTING_TYPE.E_INT:
            value = int(setting.value)
        elif setting.type == Settings.SETTING_TYPE.E_FLOAT:
            value = float(setting.value)
        elif setting.type == Settings.SETTING_TYPE.E_BOOL:
            value = True if setting.value == 'True' else False
        else:
            value = setting.value
    except:
        db.session.rollback()
        return False, ''
    return True, value


def add_setting(name, value, type, id=-1):
    try:
        setting = Settings(name=name, value=str(value), type=type, user_id=id if id > -1 else current_user.id)
        db.session.add(setting)
        db.session.commit()
        log.info('add: {}'.format(setting.log()))
        return True
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {setting.log}, {e}')
        raise e


def set_setting(name, value, id=-1):
    try:
        setting = Settings.query.filter_by(name=name, user_id=id if id > -1 else current_user.id).first()
        if setting:
            if setting.type == Settings.SETTING_TYPE.E_BOOL:
                value = 'True' if value else 'False'
            setting.value = value
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: could not set setting {name}: {e}')
        return False
    return True


def get_test_server():
    found, value = get_setting('test_server', 1)
    if found: return value
    add_setting('test_server', False, Settings.SETTING_TYPE.E_BOOL, 1)
    return False


default_configuration_settings = {
    'generic-default-student-code': ('t1', Settings.SETTING_TYPE.E_STRING),

    'sdh-inform-emails': ('t1', Settings.SETTING_TYPE.E_STRING),
    'sdh-prev-schoolyear': ('', Settings.SETTING_TYPE.E_STRING),
    'sdh-current-schoolyear': ('', Settings.SETTING_TYPE.E_STRING),
    'sdh-schoolyear-changed': (False, Settings.SETTING_TYPE.E_BOOL),

    'user-formio-template': ('', Settings.SETTING_TYPE.E_STRING),
    'user-datatables-template': ('{}', Settings.SETTING_TYPE.E_STRING),

    'student-formio-template': ('', Settings.SETTING_TYPE.E_STRING),
    'student-datatables-template': ('{}', Settings.SETTING_TYPE.E_STRING),
    'student-max-students-to-view-with-one-click': (5, Settings.SETTING_TYPE.E_INT),

    'staff-formio-template': ('', Settings.SETTING_TYPE.E_STRING),
    'staff-datatables-template': ('{}', Settings.SETTING_TYPE.E_STRING),

    'cardpresso-formio-template': ('', Settings.SETTING_TYPE.E_STRING),
    'cardpresso-datatables-template': ('{}', Settings.SETTING_TYPE.E_STRING),

    'cron-scheduler-template': ('', Settings.SETTING_TYPE.E_STRING),
    'cron-enable-update-student-from-wisa': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-enable-update-staff-from-wisa': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-enable-update-student-photo': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-enable-update-vsk-numbers': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-enable-update-student-badge': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-enable-update-student-rfid': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-enable-update-student-ad': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-enable-update-student-smartschool': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-deactivate-deleted-students': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-deactivate-deleted-staff': (False, Settings.SETTING_TYPE.E_BOOL),
    'cron-clear-changed-year-flag': (False, Settings.SETTING_TYPE.E_BOOL),

    'smartschool-scheduler-cron': ('', Settings.SETTING_TYPE.E_STRING),
    'smartschool-teacher-group': ('', Settings.SETTING_TYPE.E_STRING),
    'smartschool-api-url': ('', Settings.SETTING_TYPE.E_STRING),
    'smartschool-api-key': ('', Settings.SETTING_TYPE.E_STRING),
    'smartschool-update-teachers': (False, Settings.SETTING_TYPE.E_BOOL),
    'smartschool-update-students': (False, Settings.SETTING_TYPE.E_BOOL),

    'cardpresso-scheduler-cron': ('', Settings.SETTING_TYPE.E_STRING),
    'cardpresso-url': ('', Settings.SETTING_TYPE.E_STRING),
    'cardpresso-file': ('', Settings.SETTING_TYPE.E_STRING),
    'cardpresso-login': ('', Settings.SETTING_TYPE.E_STRING),
    'cardpresso-password': ('', Settings.SETTING_TYPE.E_STRING),
    'cardpresso-inform-emails': ('', Settings.SETTING_TYPE.E_STRING),
    'cardpresso-vsk-startnumber': (-1, Settings.SETTING_TYPE.E_INT),
    'cardpresso-update-students': (False, Settings.SETTING_TYPE.E_BOOL),

    'ad-url': ('', Settings.SETTING_TYPE.E_STRING),
    'ad-login': ('', Settings.SETTING_TYPE.E_STRING),
    'ad-password': ('', Settings.SETTING_TYPE.E_STRING),
    'ad-update-accounts': (False, Settings.SETTING_TYPE.E_BOOL),
    'ad-schoolyear-changed': (False, Settings.SETTING_TYPE.E_BOOL),

    'papercut-url': ('', Settings.SETTING_TYPE.E_STRING),
    'papercut-login': ('', Settings.SETTING_TYPE.E_STRING),
    'papercut-password': ('', Settings.SETTING_TYPE.E_STRING),
    'papercutscript-update-accounts': (False, Settings.SETTING_TYPE.E_BOOL),
    'papercut-script-path': ('', Settings.SETTING_TYPE.E_STRING),
    'papercut-script-pc_get_user_property-ps1': ('', Settings.SETTING_TYPE.E_STRING),
    'papercut-scripts': ('', Settings.SETTING_TYPE.E_STRING),

    'papercut-server-url': ('', Settings.SETTING_TYPE.E_STRING),
    'papercut-server-port': ('', Settings.SETTING_TYPE.E_STRING),
    'papercut-auth-token': ('', Settings.SETTING_TYPE.E_STRING),

    'wisa-url': ('', Settings.SETTING_TYPE.E_STRING),
    'wisa-login': ('', Settings.SETTING_TYPE.E_STRING),
    'wisa-password': ('', Settings.SETTING_TYPE.E_STRING),
    'wisa-student-query': ('', Settings.SETTING_TYPE.E_STRING),
    'wisa-staff-query': ('', Settings.SETTING_TYPE.E_STRING),
    'wisa-photo-dir': ('', Settings.SETTING_TYPE.E_STRING),
    'wisa-schoolyear': ('', Settings.SETTING_TYPE.E_STRING),
    'wisa-student-use-previous-schoolyear': (False, Settings.SETTING_TYPE.E_BOOL),
    'wisa-update-teachers': (False, Settings.SETTING_TYPE.E_BOOL),
    'wisa-update-students': (False, Settings.SETTING_TYPE.E_BOOL),

    'email-task-interval': (10, Settings.SETTING_TYPE.E_INT),
    'emails-per-minute': (30, Settings.SETTING_TYPE.E_INT),
    'email-send-max-retries': (2, Settings.SETTING_TYPE.E_INT),
    'email-base-url': ('localhost:5000', Settings.SETTING_TYPE.E_STRING),
    'email-enable-send-email': (False, Settings.SETTING_TYPE.E_BOOL),

    'test-prepare': (False, Settings.SETTING_TYPE.E_BOOL),
    'test-wisa-json-list': ('', Settings.SETTING_TYPE.E_STRING),
    'test-wisa-current-json': ('', Settings.SETTING_TYPE.E_STRING),
    'test-rfid-start-code': ('', Settings.SETTING_TYPE.E_STRING),
}


def get_configuration_settings():
    configuration_settings = {}
    for k in default_configuration_settings:
        configuration_settings[k] = get_configuration_setting(k)
    return configuration_settings


def set_configuration_setting(setting, value):
    if None == value:
        value = default_configuration_settings[setting][0]
    ret = set_setting(setting, value, 1)
    if setting in setting_changed_cb:
        for cb in setting_changed_cb[setting]:
            cb[0](value, cb[1])
    return ret


def get_configuration_setting(setting):
    found, value = get_setting(setting, 1)
    if found:
        return value
    else:
        default_setting = default_configuration_settings[setting]
        add_setting(setting, default_setting[0], default_setting[1], 1)
        return default_setting[0]


setting_changed_cb = {}
def subscribe_setting_changed(setting, cb, opaque):
    if setting in setting_changed_cb:
        setting_changed_cb[setting].append((cb, opaque))
    else:
        setting_changed_cb[setting] = [(cb, opaque)]
    return True


# save settings which are not in the database yet
# get_configuration_settings()

def get_json_template(key):
    template_string = get_configuration_setting(key)
    if template_string == '':
        template_string = '{}'
        log.error(f'{sys._getframe().f_code.co_name}: Empty template: {key}')
    try:
        settings = json.loads(template_string)
    except json.JSONDecodeError as e:
        raise Exception(f'Template has invalid JSON syntax: {key} {e}')
    return settings


def set_json_template(key, data):
    try:
        template_string = json.dumps(data)
        template_string = re.sub('},', '},\n', template_string)
        return set_configuration_setting(key, template_string)
    except json.JSONDecodeError as e:
        raise Exception(f'Template has invalid JSON syntax: {key}, {data}, {e}')

# subscribe_setting_changed('generic-view-config-template', lambda x, y: cache_settings(), None)
# subscribe_setting_changed('student-register-settings', lambda x, y: cache_settings(), None)
# subscribe_setting_changed('generic-translations', lambda x, y: cache_settings(), None)

def get_datatables_config(key):
    return get_json_template(f'{key}-datatables-template')


def get_and_increment_default_student_code():
    try:
        _, code = get_setting('generic-default-student-code', 1)
        new_code = f"t{(int(code[1::]) + 1)}"
        set_setting('generic-default-student-code', new_code, 1)
        return code
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# Read from formio text-area and format a list.
# Lines with # are ignored
def get_list(list_name):
    out = []
    recepients = get_configuration_setting(list_name)
    if recepients != '':
        recepients = recepients.split('\n')
        out = [r.strip() for r in recepients if '#' not in r]
    return out


def set_changed_schoolyear(prev, current):
    set_configuration_setting('sdh-schoolyear-changed', True)
    set_configuration_setting('sdh-prev-schoolyear', prev)
    set_configuration_setting('sdh-current-schoolyear', current)


def reset_changed_schoolyear():
    set_configuration_setting('sdh-schoolyear-changed', False)


def get_changed_schoolyear():
    changed = get_configuration_setting('sdh-schoolyear-changed')
    prev = get_configuration_setting('sdh-prev-schoolyear')
    current = get_configuration_setting('sdh-current-schoolyear')
    return changed, prev, current
