from app.data import settings as msettings, utils as mutils


def get_configuration_settings(convert_to_string=False):
    return msettings.get_configuration_settings(convert_to_string=convert_to_string)


def get_configuration_setting(setting):
    return msettings.get_configuration_setting(setting)


def set_configuration_setting(setting, value):
    msettings.set_configuration_setting(setting, value)


def get_list(list_name):
    return msettings.get_list(list_name)


def set_setting_topic(settings):
    try:
        for _, container in settings.items():
            if 'submit' in container and container['submit']:
                for k, v in container.items():
                    if k in update_setting_cbs:
                        if update_setting_cbs[k]['cb'](k, v, update_setting_cbs[k]['opaque']):
                            msettings.set_configuration_setting(k, v)
                    else:
                        msettings.set_configuration_setting(k, v)
            for k, v in button_clicked_cbs.items():
                if k in container and container[k]:
                    v['cb'](k, v['opaque'])
    except Exception as e:
        mutils.raise_error('Could not set settings topic', e)


update_setting_cbs = {}
def subscribe_handle_update_setting(topic, cb, opaque):
    update_setting_cbs[topic] = {'cb': cb, 'opaque': opaque}


button_clicked_cbs = {}
def subscribe_handle_button_clicked(topic, cb, opaque):
    button_clicked_cbs[topic] = {'cb': cb, 'opaque': opaque}
