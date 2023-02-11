from . import staff
from app import log
from flask import redirect, url_for, request
from flask_login import login_required, current_user
from app.data.datatables import DatatableConfig
from app.presentation.view import datatables
from app.application import socketio as msocketio, staff as mstaff
from app.application.settings import get_configuration_setting

import json
import app.application.staff


@staff.route('/staff/staff', methods=['POST', 'GET'])
@login_required
def show():
    # start = datetime.datetime.now()

    popups = {
        'update-password': get_configuration_setting("popup-student-teacher-update-password"),
        'new_update_staff': mstaff.form_prepare_new_update_staff(get_configuration_setting("popup-new-update-staff"))
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



def update_cell_changed(msg, client_sid=None):
  try:
    data = msg['data']
    mstaff.api_staff_update({"id": data["id"], data["column"]: data["value"]})
    msocketio.broadcast_message({'type': 'settings', 'data': {'status': True}})
  except Exception as e:
    msocketio.broadcast_message({'type': 'settings', 'data': {'status': False, 'message': str(e)}})


msocketio.subscribe_on_type('staff_socketio_cell_changed', update_cell_changed)


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
            {'label': '', 'item': 'horizontal-line', 'iconscout': ''},
            {'label': 'Nieuw personeelslid', 'item': 'add', 'iconscout': 'plus-circle'},
            {'label': 'Personeelslid aanpassen', 'item': 'edit', 'iconscout': 'pen'},
        ])
    if current_user.is_at_least_admin:
        settings['menu'].extend([
            {'label': 'Personeelslid(eden) verwijderen', 'item': 'delete', 'iconscout': 'trash-alt', 'ack': 'Bent u zeker dat u dit personeelslid/deze personeelsleden wilt verwijderen?'},
            {'label': '', 'item': 'horizontal-line', 'iconscout': ''},
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
        return self.pre_sql_standard_order(q, on, direction)

    def format_data(self, l, total_count, filtered_count):
        return app.application.staff.format_data(l, total_count, filtered_count)

    def post_sql_order(self, l, on, direction):
        return app.application.staff.post_sql_order(l, on, direction)

    def get_right_click(self):
        return get_right_click_settings()

    socketio_endpoint = "staff_socketio_cell_changed"


table_config = Config("staff", "Overzicht Leerkrachten")
