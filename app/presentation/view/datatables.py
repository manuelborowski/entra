from app import flask_app
from app.application import settings as msettings
from app.presentation.layout.utils import flash_plus
from app.application.datatables import prepare_data_for_ajax
from flask import render_template, request, get_flashed_messages, jsonify
from flask_login import current_user


def ajax(table_configuration):
    try:
        data_list, total_count, filtered_count = prepare_data_for_ajax(table_configuration)
        datatable = add_datatable_headers(table_configuration, data_list, total_count, filtered_count)
    except Exception as e:
        flash_plus(f'Tabel kan niet getoond worden (ajax)', e)
        datatable = add_datatable_headers(table_configuration, [], 0, 0)
    return datatable


def show(table_config, template=None, popups={}):
    api_key = config = None
    try:
        config = table_config.create_table_config()
        api_keys = msettings.get_configuration_setting('api-keys')[current_user.level-1]
        api_key = [k for k, v in api_keys.items() if v == "local"][0]
    except Exception as e:
        flash_plus(f'Tabel kan niet getoond worden (show)', e)
    if not template:
        template = 'datatables.html'
    return render_template(template, table_config=config, api_key=api_key, popups=popups)


def add_datatable_headers(table_configuration, data_list, total_count, filtered_count):
    #prepare for json/ajax
    output = {'draw': str(int(request.values['draw'])), 'recordsTotal': str(total_count),
              'recordsFiltered': str(filtered_count), 'data': data_list}
    # add the (non-standard) flash-tag to display flash-messages via ajax
    fml = get_flashed_messages()
    if not not fml:
        output['flash'] = fml
    output['show_info'] = table_configuration.show_info()
    return jsonify(output)

