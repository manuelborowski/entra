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
    ret = datatables.show(table_config, template='staff/staff.html')
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
    return redirect(url_for('staff.show'))



def update_cell_changed(msg, client_sid=None):
  try:
    data = msg['data']
    mstaff.api_staff_update({"id": data["id"], data["column"]: data["value"]})
    msocketio.broadcast_message('settings', {'status': True})
  except Exception as e:
    msocketio.broadcast_message('settings', {'status': False, 'message': str(e)})


msocketio.subscribe_on_type('staff_socketio_cell_changed', update_cell_changed)


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


table_config = Config("staff", "Overzicht Leerkrachten")
