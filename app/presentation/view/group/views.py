from . import group
from flask import redirect, url_for
from flask_login import login_required
from app.data.datatables import DatatableConfig
from app.presentation.view import datatables
from app.application import socketio as msocketio, group as mgroup
import json
import app.data
import app.application.group
from app.application.settings import get_configuration_setting


@group.route('/group/group', methods=['POST', 'GET'])
@login_required
def show():
    ret = datatables.show(table_config, template='datatables.html')
    return ret


@group.route('/group/table_ajax', methods=['GET', 'POST'])
@login_required
def table_ajax():
    ret =  datatables.ajax(table_config)
    return ret


def get_filters():
    types = mgroup.get_types()
    types = [["default", "Alles"]] + [[t, t] for t in types]
    archived = [["default", "Alles"], [True, "Ja"], [False, "Nee"]]
    return [
        {
            'type': 'select',
            'name': 'type',
            'label': 'Types',
            'choices': types,
            'default': 'default',
        },
        {
            'type': 'select',
            'name': 'archived',
            'label': 'Gearchiveerd',
            'choices': archived,
            'default': 'default',
        },
    ]


@group.route('/group/table_action', methods=['GET', 'POST'])
@group.route('/group/table_action/<string:action>', methods=['GET', 'POST'])
@group.route('/group/table_action/<string:action>/<string:ids>', methods=['GET', 'POST'])
@login_required
def table_action(action, ids=None):
    return redirect(url_for('group.show'))


class Config(DatatableConfig):
    def pre_sql_query(self):
        return app.data.group.pre_sql_query()

    def pre_sql_filter(self, q, filter):
        return app.data.group.pre_sql_filter(q, filter)

    def pre_sql_search(self, search):
        return app.data.group.pre_sql_search(search)

    def pre_sql_order(self, q, on, direction):
        return self.pre_sql_standard_order(q, on, direction)

    def format_data(self, l, total_count, filtered_count):
        return app.application.group.format_data(l, total_count, filtered_count)

    def show_filter_elements(self):
        return get_filters()


table_config = Config("group", "Overzicht groepen")
