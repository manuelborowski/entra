from app.data import device as mdevice, student as mstudent
from app.data.entra import entra
import app.application.api
import sys, pandas as pd

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


# if a student is marked as deleted, get all associated devices.
# For all devices, remove from autopilot, intune and entra (if applicable).
def cron_remove_devices(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        students = mstudent.student_get_m(("delete", "=", True))
        for student in students:
            log.info(f'{sys._getframe().f_code.co_name}: Deleting student {student.leerlingnummer}, {student.naam} {student.voornaam}')
            devices = mdevice.device_get_m(("user_entra_id", "=", student.entra_id))
            for device in devices:
                if device.do_not_delete:
                    log.info(f'{sys._getframe().f_code.co_name}: Device NOT deleted, belongs to do-not-delete-group {device.device_name}, {device.serial_number}')
                else:
                    entra.delete_device(device)
                    log.info(f'{sys._getframe().f_code.co_name}: Deleting device {device.device_name}, {device.serial_number}')
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def api_upload_m4s(files):
    try:
        m4s_devices = []
        for file in files:
            if file.content_type == "text/csv":
                m4s = pd.read_csv(file)
            else:
                m4s = pd.read_excel(file)
            m4s_devices += m4s.to_dict("records")

        if m4s_devices:
            db_devices = mdevice.device_get_m()
            db_device_cache = {d.serial_number: d for d in db_devices}
            not_found = []
            for device in m4s_devices:
                if device["SerialNumber"] in db_device_cache:
                    db_device = db_device_cache[device["SerialNumber"]]
                    db_device.m4s_csu_label = device["InstitutionLabel"]
                    db_device.m4s_signpost_label = device["SignpostLabel"]
                    del db_device_cache[device["SerialNumber"]]
                else:
                    not_found.append(device["InstitutionLabel"])
                    if len(not_found) > 6:
                        log.info(f'{sys._getframe().f_code.co_name}: NOT in DB {", ".join(not_found)}')
                        not_found = []
            if len(not_found) > 0:
                log.info(f'{sys._getframe().f_code.co_name}: NOT in DB {", ".join(not_found)}')

            not_found = []
            for (serial, device) in db_device_cache.items():
                not_found.append(f"({device.serial_number}, {device.device_name})")
                if len(not_found) > 2:
                    log.info(f'{sys._getframe().f_code.co_name}: NOT in M4S {", ".join(not_found)}')
                    not_found = []
            if len(not_found) > 0:
                log.info(f'{sys._getframe().f_code.co_name}: NOT in M4S {", ".join(not_found)}')

            mdevice.commit()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error("FLUSH-TO-EMAIL")  # this will trigger an email with ERROR-logs (if present)
        return {"status": False, "data": f"Fout, {e}"}




################# API ######################
def api_device_get(options=None):
    try:
        return app.application.api.api_get_model_data(mdevice.Device, options)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}



############ datatables: student overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for device in db_list:
        em = device.to_dict()
        em.update({
            'row_action': device.id,
            'DT_RowId': device.id,
            "intune_id": f'<a href="https://intune.microsoft.com/#view/Microsoft_Intune_Devices/DeviceSettingsMenuBlade/~/overview/mdmDeviceId/{device.intune_id}" target=_blank">{device.intune_id}</a>',
        })
        out.append(em)
    return total_count, filtered_count, out



