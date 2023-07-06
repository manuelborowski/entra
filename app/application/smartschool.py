import bdb, app
from app.data import student as mstudent, staff as mstaff, utils as mutils
from app.data import settings as msettings
from app.application.email import  send_new_staff_message
import ldap3, json, sys, datetime
from functools import wraps
from app.application.util import get_student_voornaam

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


###############################################################
############    Common specifications          ################
###############################################################


class PersonContext:
    def __init__(self):
        self.verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')


def ad_ctx_wrapper(ctx_class):
    def inner_ad_core(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                ctx = ctx_class()
                kwargs["ctx"] = ctx
                return func(*args, **kwargs)
            except Exception as e:
                log.error(f'AD-EXCEPTION: {func.__name__}: {e}')
                raise Exception(f'AD-EXCEPTION: {func.__name__}: {e}')
            finally:
                __ldap_deinit(ctx)
        return wrapper
    return inner_ad_core


def ad_exception_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.error(f'{func.__name__}: {e}')
            raise Exception(f'{func.__name__}: {e}')
    return wrapper




###############################################################
############    Student specific cron task     ################
###############################################################



class StudentContext(PersonContext):
    def __init__(self):
        super().__init__()
        self.student_ou_current_year = ''
        self.ad_active_students_leerlingnummer = {}  # cache active students, use leerlingnummer as key
        self.ad_active_students_dn = {}  # cache active students, use dn as key
        self.ad_active_students_mail = []   # a list of existing emails, needed to check for doubles
        self.leerlingnummer_to_klas = {}  # find a klas a student belongs to, use leerlingnummer as key
        self.ad_klassen = []
        self.add_student_to_klas = {}  # dict of klassen with list-of-students-to-add-to-the-klas
        self.delete_student_from_klas = {}  # dict of klassen with list-of-students-to-delete-from-the-klas
        self.new_students_to_add = []  # these students do not exist yet in AD, must be added
        self.students_to_leerlingen_group = []  # these students need to be placed in the group leerlingen
        self.students_move_to_current_year_ou = []
        self.students_change_cn = []
        self.students_must_update_password = []
        self.current_year = mutils.get_current_schoolyear(format=3)


@ad_ctx_wrapper(StudentContext)
def student_process_flagged(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    log.info(f"{sys._getframe().f_code.co_name}, STOP")
    return True


