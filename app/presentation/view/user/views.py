from flask import redirect, url_for
from flask_login import login_required
from app import admin_required, data
from . import user
from app.application import user as muser
from app.presentation.view import datatables
from app.data.datatables import DatatableConfig
import app.data.user
import app.application.user
from app.application.settings import get_configuration_setting

@user.route('/user', methods=['GET', 'POST'])
@admin_required
@login_required
def show():
    # start = datetime.datetime.now()
    popups = {"user_password_form": get_configuration_setting("popup-new-update-user")}
    ret = datatables.show(table_configuration, template="user/user.html", popups=popups)
    # print('student.show', datetime.datetime.now() - start)
    return ret


@user.route('/user/table_ajax', methods=['GET', 'POST'])
@login_required
def table_ajax():
    # start = datetime.datetime.now()
    ret =  datatables.ajax(table_configuration)
    # print('student.table_ajax', datetime.datetime.now() - start)
    return ret

# Legacy, not used anymore
@user.route('/user/table_action', methods=['GET', 'POST'])
@user.route('/user/table_action/<string:action>', methods=['GET', 'POST'])
@user.route('/user/table_action/<string:action>/<string:ids>', methods=['GET', 'POST'])
@login_required
@admin_required
def table_action(action, ids=None):
    return redirect(url_for('user.show'))


class UserConfig(DatatableConfig):
    def pre_sql_query(self):
        return app.data.user.pre_sql_query()

    def pre_sql_search(self, search):
        return data.user.pre_sql_search(search)

    def pre_sql_order(self, q, on, direction):
        return self.pre_sql_standard_order(q, on, direction)

    def format_data(self, l, total_count, filtered_count):
        return app.application.user.format_data(l, total_count, filtered_count)

    def get_right_click(self):
        return {
            'endpoint': 'user.right_click',
            'menu': [
                {'label': 'Nieuwe gebruiker', 'item': 'add', 'iconscout': 'plus-circle'},
                {'label': 'Gebruiker aanpassen', 'item': 'edit', 'iconscout': 'pen'},
                {'label': 'Gebruiker(s) verwijderen', 'item': 'delete', 'iconscout': 'trash-alt', 'ack': 'Bent u zeker dat u deze gebruiker(s) wilt verwijderen?'},
            ]
        }


table_configuration = UserConfig("user", "Gebruikers")

