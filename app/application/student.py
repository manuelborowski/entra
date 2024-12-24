from app.data import student as mstudent, settings as msettings, person as mperson
import app.application.api
import sys
#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def api_student_get(options):
    try:
        return app.application.api.api_get_model_data(mstudent.Student, options)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}

def student_delete(ids):
    mstudent.student_delete_m(ids)

def klassen_get_unique():
    klassen = mstudent.student_get_m(fields=['klascode'])
    klassen = list(set([k[0] for k in klassen]))
    klassen.sort()
    return klassen


############ datatables: student overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for student in db_list:
        em = student.to_dict()
        em.update({
            'row_action': student.id,
            'DT_RowId': student.id,
            "naam": f'<a href="https://entra.microsoft.com/#view/Microsoft_AAD_UsersAndTenants/UserProfileMenuBlade/~/overview/userId/{student.entra_id}/hidePreviewBanner~/true" target="_blank">{student.naam}</a>',
            "computer_name": f'<a href="https://intune.microsoft.com/#view/Microsoft_Intune_Devices/DeviceSettingsMenuBlade/~/overview/mdmDeviceId/{student.computer_intune_id}" target="_blank">{student.computer_name}</a>',
        })
        out.append(em)
    return total_count, filtered_count, out


def photo_get_nbr_not_found():
    nbr_students_no_photo = mstudent.student_get_m([('foto_id', "=", -1)], count=True)
    return nbr_students_no_photo


