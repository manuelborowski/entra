from . import cardpresso
from flask import redirect, url_for
from flask_login import login_required
from app.data.datatables import DatatableConfig
from app.presentation.view import datatables
from app.application import socketio as msocketio
import app.data
import app.application.cardpresso


@cardpresso.route('/cardpresso/cardpresso', methods=['POST', 'GET'])
@login_required
def show():
    # start = datetime.datetime.now()
    ret = datatables.show(table_config, template="cardpresso/cardpresso.html")
    # print('cardpresso.show', datetime.datetime.now() - start)
    return ret


@cardpresso.route('/cardpresso/table_ajax', methods=['GET', 'POST'])
@login_required
def table_ajax():
    # start = datetime.datetime.now()
    ret = datatables.ajax(table_config)
    # print('cardpresso.table_ajax', datetime.datetime.now() - start)
    return ret


@cardpresso.route('/cardpresso/table_action', methods=['GET', 'POST'])
@cardpresso.route('/cardpresso/table_action/<string:action>', methods=['GET', 'POST'])
@cardpresso.route('/cardpresso/table_action/<string:action>/<string:ids>', methods=['GET', 'POST'])
@login_required
def table_action(action, ids=None):
    return redirect(url_for('cardpresso.show'))


def get_filters():
    klassen = app.application.student.klassen_get_unique()
    klassen = [[k, k] for k in klassen]
    klas_choices = [['default', 'Alles']] + klassen
    klasgroepen = app.application.klas.get_klassen_klasgroepen()
    klasgroep_choices = []
    for klasgroep, klas_list in klasgroepen.items():
        klasgroep_choices.append([",".join(klas_list), klasgroep ])
    klasgroep_choices =  sorted(klasgroep_choices, key = lambda x: x[0])
    deelscholen = app.application.klas.get_klassen_deelscholen()
    deelschool_choices = []
    for deelschool, klas_list in deelscholen.items():
        deelschool_choices.append([",".join(klas_list), deelschool])
    deelschool_choices = sorted(deelschool_choices, key=lambda x: x[0])
    klasgroep_choices = [["default", "Alles"]] + deelschool_choices + klasgroep_choices
    return [
        # {
        #     'type': 'select',
        #     'name': 'filter-klas',
        #     'label': 'Klassen',
        #     'choices': klas_choices,
        #     'default': 'default',
        # },
        {
            'type': 'select',
            'name': 'filter-klasgroep',
            'label': 'Klasgroepen',
            'choices': klasgroep_choices,
            'default': 'default',
        },
    ]


def get_right_click_settings():
    return {
        'menu': [
            {'label': 'Update RFID van studenten', 'item': 'update-rfid', 'iconscout': 'corner-left-down'},
            {'label': 'Verwijder', 'item': 'delete', 'iconscout': 'trash-alt'},
        ]
    }

class Config(DatatableConfig):
    def pre_sql_query(self):
        return app.data.cardpresso.pre_filter()

    def pre_sql_filter(self, q, filter):
        return app.data.cardpresso.filter_data(q, filter)

    def pre_sql_search(self, search):
        return app.data.cardpresso.search_data(search)

    def pre_sql_order(self, q, on, direction):
        return self.pre_sql_standard_order(q, on, direction)

    def format_data(self, l, total_count, filtered_count):
        return app.application.cardpresso.format_data(l, total_count, filtered_count)

    def get_right_click(self):
        return get_right_click_settings()

    def show_filter_elements(self):
        return get_filters()




table_config = Config("cardpresso", "Overzicht Studentenbadges")
