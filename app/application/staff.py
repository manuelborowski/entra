from app.data import staff as mstaff

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def staff_delete_m(ids):
    mstaff.staff_delete_m(ids)


############ datatables: staff overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for staff in db_list:
        em = staff.to_dict()
        em.update({
            'row_action': staff.id,
            'DT_RowId': staff.id,
            "naam": f'<a href="https://entra.microsoft.com/#view/Microsoft_AAD_UsersAndTenants/UserProfileMenuBlade/~/overview/userId/{staff.entra_id}/hidePreviewBanner~/true" target="_blank">{staff.naam}</a>',
            "computer_name": f'<a href="https://intune.microsoft.com/#view/Microsoft_Intune_Devices/DeviceSettingsMenuBlade/~/overview/mdmDeviceId/{staff.computer_intune_id}" target="_blank">{staff.computer_name}</a>',
        })
        out.append(em)
    return total_count, filtered_count, out

def post_sql_order(l, on, direction):
    return sorted(l, key=lambda x: x[on], reverse=direction=="desc")
