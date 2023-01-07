from app.data import settings as msettings, student as mstudent, staff as mstaff

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def test_cron_task(opaque=None):
    if msettings.get_configuration_setting('test-prepare'):
        log.info('TEST: prepare for testing students...')
        msettings.set_configuration_setting('test-prepare', False)
        all_students = mstudent.student_get_m()
        all_students.extend(mstudent.student_get_m(active=False))
        mstudent.student_delete_m(students=all_students)
        msettings.set_configuration_setting('sdh-prev-schoolyear', '')
        msettings.set_configuration_setting('sdh-current-schoolyear', '')
        msettings.set_configuration_setting('sdh-schoolyear-changed', False)
        msettings.set_configuration_setting('test-wisa-current-json', '')

    if msettings.get_configuration_setting('test-staff-prepare'):
        log.info('TEST: prepare for testing staff...')
        msettings.set_configuration_setting('test-staff-prepare', False)
        all_staff = mstaff.staff_get_m()
        all_staff.extend(mstaff.staff_get_m(active=False))
        mstaff.staff_delete_m(staffs=all_staff)
        msettings.set_configuration_setting('test-staff-wisa-current-json', '')

