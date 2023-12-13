from app.data import student as mstudent, settings as msettings, person as mperson


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
    for device in db_list:
        em = device.to_dict()
        em.update({
            'row_action': device.id,
            'DT_RowId': device.id,
            "entra_id": f'<a href="https://intune.microsoft.com/#view/Microsoft_Intune_Devices/DeviceSettingsMenuBlade/~/overview/mdmDeviceId/{device.entra_id}" target=_blank">{device.entra_id}</a>',
        })
        out.append(em)
    return total_count, filtered_count, out



