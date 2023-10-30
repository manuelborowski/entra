from app import ap_scheduler, flask_app
import datetime, sys
from apscheduler.triggers.cron import CronTrigger
from app.application.settings import get_configuration_setting, subscribe_handle_button_clicked, subscribe_handle_update_setting, set_configuration_setting
from app.application.test import test_cron_task
from app.application.socketio import broadcast_message
from . import cron_table

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


CRON_TASK = 'school-data-hub-task'

#In July and August, cron is normally disabled and students and staff are not deleted from the dabase if not present in the import
def disable_features_in_july_august():
    now_month = datetime.datetime.now().month
    if now_month == 7 or now_month == 8:
        set_configuration_setting("cron-active-july-august", False)
        set_configuration_setting("cron-delete-july-august", False)


def check_cron_active_july_august():
    now_month = datetime.datetime.now().month
    if now_month == 7 or now_month == 8:
        return get_configuration_setting("cron-active-july-august")
    return True


def cron_task(opaque=None):
    try:
        with flask_app.app_context():
            broadcast_message("message-on", {"data": "Data wordt gesynchroniseerd"})
            if check_cron_active_july_august():
                settings = get_configuration_setting('cron-enable-modules')
                test_cron_task(opaque)
                for task in cron_table:
                    if task[0] in settings and settings[task[0]]:
                        task[1](opaque)
                log.error("FLUSH-TO-EMAIL") # this will trigger an email with ERROR-logs (if present)
                disable_features_in_july_august()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    finally:
        broadcast_message("message-off")


def init_job(cron_template):
    try:
        running_job = ap_scheduler.get_job(CRON_TASK)
        if running_job:
            ap_scheduler.remove_job(CRON_TASK)
        if cron_template == 'now':
            ap_scheduler.add_job(CRON_TASK, cron_task, next_run_time=datetime.datetime.now())
        elif cron_template != '':
            ap_scheduler.add_job(CRON_TASK, cron_task, trigger=CronTrigger.from_crontab(cron_template))
    except Exception as e:
        log.error(f'could not init {CRON_TASK} job: {e}')


def update_cron_template(setting, value, opaque):
    try:
        if setting == 'cron-scheduler-template':
            init_job(value)
    except Exception as e:
        log.error(f'could not update cron-scheduler-template: {e}')
    return True


def start_job():
    try:
        cron_template = get_configuration_setting('cron-scheduler-template')
        if cron_template != 'now':  # prevent to run the cronjob each time the server is rebooted
            init_job(cron_template)
        subscribe_handle_update_setting('cron-scheduler-template', update_cron_template, None)
    except Exception as e:
        log.error(f'could not start cron-scheduler: {e}')


start_job()


def emulate_cron_start(topic=None, opaque=None):
    cron_task(opaque)


subscribe_handle_button_clicked('button-start-cron-cycle', emulate_cron_start, {"sync-school": "csu"})
subscribe_handle_button_clicked('button-sync-sum', emulate_cron_start, {"sync-school": "sum"})
subscribe_handle_button_clicked('button-sync-sul', emulate_cron_start, {"sync-school": "sul"})
subscribe_handle_button_clicked('button-sync-sui', emulate_cron_start, {"sync-school": "sui"})
subscribe_handle_button_clicked('button-sync-testklassen', emulate_cron_start, {"sync-school": "testklassen"})


disable_features_in_july_august()