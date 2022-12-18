from . import student
from app import log
from flask import redirect, url_for, request, render_template
from flask_login import login_required, current_user
from app.data.datatables import DatatableConfig
from app.presentation.view import datatables
from app.application import socketio as msocketio, settings as msettings, cardpresso as mcardpresso
import json
import app.data
import app.application.student
from app.application.settings import get_configuration_setting


@student.route('/student/student', methods=['POST', 'GET'])
@login_required
def show():
    # start = datetime.datetime.now()
    popups = {'update-password': get_configuration_setting("popup-student-teacher-update-password"),
              'database-integrity-check': get_configuration_setting("popup-database-integrity-check")}
    ret = datatables.show(table_config, template='student/student.html', popups=popups)
    # print('student.show', datetime.datetime.now() - start)
    return ret


@student.route('/student/table_ajax', methods=['GET', 'POST'])
@login_required
def table_ajax():
    # start = datetime.datetime.now()
    ret =  datatables.ajax(table_config)
    # print('student.table_ajax', datetime.datetime.now() - start)
    return ret


@student.route('/student/table_action', methods=['GET', 'POST'])
@student.route('/student/table_action/<string:action>', methods=['GET', 'POST'])
@student.route('/student/table_action/<string:action>/<string:ids>', methods=['GET', 'POST'])
@login_required
def table_action(action, ids=None):
    if ids:
        ids = json.loads(ids)
    if action == 'view':
        return item_view(ids)
    return redirect(url_for('student.show'))


def item_view(ids=None):
    try:
        if ids == None:
            chbx_id_list = request.form.getlist('chbx')
            if chbx_id_list:
                ids = chbx_id_list[0]  # only the first one can be edited
            if ids == '':
                return redirect(url_for('student.show'))
        else:
            id = ids[0]
            data = app.application.student.form_prepare_for_view(id)
            data.update({'title': f"{data['defaults']['naam']} {data['defaults']['voornaam']}"})
            return render_template('formio.html', data=data)
    except Exception as e:
        log.error(f'Could not view student {e}')
    return redirect(url_for('student.show'))


@student.route('/student/right_click/', methods=['POST', 'GET'])
@login_required
def right_click():
    try:
        if 'jds' in request.values:
            data = json.loads(request.values['jds'])
            if 'item' in data:
                if data['item'] == "new-badge":
                    ret = mcardpresso.badge_add(data['item_ids'])
                    return {"message": ret['data']}
                if data['item'] == "view":
                    max_ids = msettings.get_configuration_setting('student-max-students-to-view-with-one-click')
                    ids = data['item_ids'][:max_ids]
                    return {"redirect": {"url": f"/student/table_action/view", "ids": ids, "new_tab": True}}
    except Exception as e:
        log.error(f"Error in get_form: {e}")
        return {"message": f"get_form: {e}"}
    return {"message": "iets is fout gelopen"}


def get_filters():
    klassen = app.application.student.klassen_get_unique()
    klassen = [[k, k] for k in klassen]
    klas_choices = [['default', 'Alles']] + klassen
    return [
        {
            'type': 'select',
            'name': 'photo-not-found',
            'label': 'Foto\'s',
            'choices': [
                ['default', 'Alles'],
                ['not-found', 'Geen foto'],
            ],
            'default': 'default',
        },
        {
            'type': 'select',
            'name': 'filter-klas',
            'label': 'Klassen',
            'choices': klas_choices,
            'default': 'default',
        },
    ]



def get_right_click_settings():
    settings = {
        'endpoint': 'student.right_click',
        'menu': [
            {'label': 'Details', 'item': 'view', 'iconscout': 'eye'},
        ]
    }
    if current_user.is_at_least_supervisor:
        settings['menu'].extend([
            {'label': 'Nieuwe badge', 'item': 'new-badge', 'iconscout': 'credit-card'},
            {'label': 'RFID code aanpassen', 'item': 'check-rfid', 'iconscout': 'wifi'},
            {'label': 'Paswoord aanpassen', 'item': 'update-password', 'iconscout': 'key-skeleton'},
            {'label': '', 'item': 'horizontal-line', 'iconscout': ''},
            {'label': 'Vsk nummers', 'item': 'new-vsk-numbers', 'iconscout': 'abacus'},
        ])
    if current_user.is_at_least_admin:
        settings['menu'].extend([
            {'label': 'Database Integriteitscontrole', 'item': 'database-integrity-check', 'iconscout': 'database'},
        ])
    return settings



class Config(DatatableConfig):
    def pre_sql_query(self):
        return app.data.student.pre_sql_query()

    def pre_sql_filter(self, q, filter):
        return app.data.student.pre_sql_filter(q, filter)

    def pre_sql_search(self, search):
        return app.data.student.pre_sql_search(search)

    def pre_sql_order(self, q, on, direction):
        return self.pre_sql_standard_order(q, on, direction)

    def format_data(self, l, total_count, filtered_count):
        return app.application.student.format_data(l, total_count, filtered_count)

    def show_filter_elements(self):
        return get_filters()

    def show_info(self):
        return [f'Niet gevonden foto\'s: {app.application.student.photo_get_nbr_not_found()}']

    def get_right_click(self):
        return get_right_click_settings()


table_config = Config("student", "Overzicht Studenten")