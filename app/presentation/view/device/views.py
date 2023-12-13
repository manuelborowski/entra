from . import device
from app import log
from flask import redirect, url_for, request, render_template
from flask_login import login_required, current_user
from app.data.datatables import DatatableConfig
from app.presentation.view import datatables
from app.application import socketio as msocketio, settings as msettings
import json
import app.data
import app.application.device
from app.application.settings import get_configuration_setting


@device.route('/device/device', methods=['POST', 'GET'])
@login_required
def show():
    # start = datetime.datetime.now()
    ret = datatables.show(table_config)
    # print('device.show', datetime.datetime.now() - start)
    return ret


@device.route('/device/table_ajax', methods=['GET', 'POST'])
@login_required
def table_ajax():
    # start = datetime.datetime.now()
    ret =  datatables.ajax(table_config)
    # print('device.table_ajax', datetime.datetime.now() - start)
    return ret


@device.route('/device/table_action', methods=['GET', 'POST'])
@device.route('/device/table_action/<string:action>', methods=['GET', 'POST'])
@device.route('/device/table_action/<string:action>/<string:ids>', methods=['GET', 'POST'])
@login_required
def table_action(action, ids=None):
    return redirect(url_for('device.show'))



def get_filters():
    return [ ]


class Config(DatatableConfig):
    def pre_sql_query(self):
        return app.data.device.pre_sql_query()

    def pre_sql_filter(self, q, filter):
        return app.data.device.pre_sql_filter(q, filter)

    def pre_sql_search(self, search):
        return app.data.device.pre_sql_search(search)

    def pre_sql_order(self, q, on, direction):
        return self.pre_sql_standard_order(q, on, direction)

    def format_data(self, l, total_count, filtered_count):
        return app.application.device.format_data(l, total_count, filtered_count)

    def show_filter_elements(self):
        return get_filters()


table_config = Config("device", "Overzicht toestellen")


