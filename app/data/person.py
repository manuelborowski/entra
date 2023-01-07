from app.data.student import student_get
from app.data.staff import staff_get
import sys

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def check_if_rfid_already_exists(rfid):
    if rfid != "":
        staff = staff_get(data={"rfid": rfid})
        if staff:
            log.error(f'{sys._getframe(1).f_code.co_name}: RFID {rfid} already exists for {staff.person_id}')
            return staff
        student = student_get(data={"rfid": rfid})
        if student:
            log.error(f'{sys._getframe(1).f_code.co_name}: RFID {rfid} already exists for {student.person_id}')
            return student
    return None


