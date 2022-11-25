from . import staff
from app import log
from flask import redirect, url_for, request
from flask_login import login_required, current_user
from app.data.datatables import DatatableConfig, pre_sql_standard_order
from app.presentation.view import datatables
from app.application import socketio as msocketio
from app.presentation.view.formio_popups import update_password
import json
import app.application.staff


@staff.route('/staff/staff', methods=['POST', 'GET'])
@login_required
def show():
    # start = datetime.datetime.now()
    popups = {
        'update-password': update_password
    }
    ret = datatables.show(table_config, template='staff/staff.html', popups=popups)
    # print('staff.show', datetime.datetime.now() - start)
    return ret


@staff.route('/staff/table_ajax', methods=['GET', 'POST'])
@login_required
def table_ajax():
    # start = datetime.datetime.now()
    ret =  datatables.ajax(table_config)
    # print('staff.table_ajax', datetime.datetime.now() - start)
    return ret


@staff.route('/staff/table_action', methods=['GET', 'POST'])
@staff.route('/staff/table_action/<string:action>', methods=['GET', 'POST'])
@staff.route('/staff/table_action/<string:action>/<string:ids>', methods=['GET', 'POST'])
@login_required
def table_action(action, ids=None):
    if ids:
        ids = json.loads(ids)
    return redirect(url_for('staff.show'))


@staff.route('/staff/right_click/', methods=['POST', 'GET'])
@login_required
def right_click():
    try:
        if 'jds' in request.values:
            data = json.loads(request.values['jds'])
    except Exception as e:
        log.error(f"Error in get_form: {e}")
        return {"message": f"get_form: {e}"}
    return {"message": "iets is fout gelopen"}


def get_right_click_settings():
    settings = {
        'endpoint': 'staff.right_click',
        'menu': []
    }
    if current_user.is_at_least_supervisor:
        settings['menu'].extend([
            {'label': 'RFID code aanpassen', 'item': 'check-rfid', 'iconscout': 'wifi'},
        ])
    if current_user.is_at_least_admin:
        settings['menu'].extend([
            {'label': 'Paswoord aanpassen', 'item': 'update-password', 'iconscout': 'key-skeleton'},
        ])
    return settings

class Config(DatatableConfig):
    def pre_sql_query(self):
        return app.data.staff.pre_sql_query()

    def pre_sql_filter(self, q, filter):
        return app.data.staff.pre_sql_filter(q, filter)

    def pre_sql_search(self, search):
        return app.data.staff.pre_sql_search(search)

    def pre_sql_order(self, q, on, direction):
        return pre_sql_standard_order(q, on, direction)

    def format_data(self, l, total_count, filtered_count):
        return app.application.staff.format_data(l, total_count, filtered_count)

    def get_right_click(self):
        return get_right_click_settings()


table_config = Config("staff", "Overzicht Leerkrachten")
