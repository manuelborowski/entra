from . import logging
from flask import redirect, url_for
from flask_login import login_required, current_user
from app.data.datatables import DatatableConfig
from app.presentation.view import datatables
from app.application import socketio as msocketio, logging as mlogging
import app.data
import app.application.student


@logging.route('/logging/logging', methods=['POST', 'GET'])
@login_required
def show():
    ret = datatables.show(table_config)
    return ret


@logging.route('/logging/table_ajax', methods=['GET', 'POST'])
@login_required
def table_ajax():
    ret = datatables.ajax(table_config)
    return ret


@logging.route('/logging/table_action', methods=['GET', 'POST'])
@logging.route('/logging/table_action/<string:action>', methods=['GET', 'POST'])
@logging.route('/logging/table_action/<string:action>/<string:ids>', methods=['GET', 'POST'])
@login_required
def table_action(action, ids=None):
    return redirect(url_for('logging.show'))


def get_filters():
    levels = mlogging.get_log_levels()
    levels = [["default", "Alles"]] + levels
    if current_user.is_at_least_admin:
        owners = mlogging.get_owners()
        owners = [["default", "Alles"]] + [[o, o] for o in owners]
        default_owner = "default"
    else:
        owners = [[current_user.username, current_user.username]]
        default_owner = current_user.username

    return [
        {
            'type': 'select',
            'name': 'log-level',
            'label': 'Graad',
            'choices': levels,
            'default': 'default',
        },
        {
            'type': 'select',
            'name': 'owner',
            'label': 'Code',
            'choices': owners,
            'default': default_owner,
        },
    ]


class Config(DatatableConfig):
    def pre_sql_query(self):
        return app.data.logging.pre_sql_query()

    def pre_sql_filter(self, q, filter):
        return app.data.logging.pre_sql_filter(q, filter)

    def pre_sql_search(self, search):
        return app.data.logging.pre_sql_search(search)

    def pre_sql_order(self, q, on, direction):
        return self.pre_sql_standard_order(q, on, direction)

    def format_data(self, l, total_count, filtered_count):
        return app.application.logging.format_data(l, total_count, filtered_count)

    def show_filter_elements(self):
        return get_filters()


table_config = Config("logging", "Overzicht Logging")
