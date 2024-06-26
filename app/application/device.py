from app.data import device as mdevice
import app.application.api
import sys

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


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



