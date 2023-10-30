from flask import Flask, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_jsglue import JSGlue
from werkzeug.routing import IntegerConverter as OrigIntegerConvertor
import logging, logging.handlers, os, sys
from functools import wraps
from flask_socketio import SocketIO
from flask_apscheduler import APScheduler
from flask_mail import Mail

flask_app = Flask(__name__, instance_relative_config=True, template_folder='presentation/templates/')

# Configuration files...
from config import app_config
config_name = os.getenv('FLASK_CONFIG')
config_name = config_name if config_name else 'production'
flask_app.config.from_object(app_config[config_name])
flask_app.config.from_pyfile('config.py')

# V0.1: copy from sum-zorg V0.109
# 0.2: removed intake and care.  Added functionality to read database and photos from wisa
# 0.3: added functionality to print badges.  Added right-click
# 0.4: added cron tasks: import photo's, assign vsk numbers, create badges.  Send email when something changed related to cardpresso.
# 0.5: updated cron badges task.  Added tests for wisa-cron-task and rfid-cron-task
# 0.6: AD interface is OK.  added testing
# 0.7: new and resurrected students: empty password and password must be changed at first logon
# 0.8: minor updates
# 0.9: update python-package, use configurable IP address
# 0.10: small bugfix
# 0.11: update frontend (css), bugfix right-click
# 0.12: update api-key, added endpoint to get student info
# 0.13: commit: add rollback in case of exception
# 0.14: added import staff from wisa. AD, add new class to 'leerlingen'
# 0.15: update in settings
# 0.16: add school email to database.  API, add filters
# 0.17: api keys are stored as a setting
# 0.18: extend api, always return status and data.  sqlalchemy, bugfix when querying for field 'delete'
# 0.19: bugfix api when fields of type datetime are requested.  Refactored model-api
# 0.20: update api/fields
# 0.21: clear selectionboxes after action.  Students from WISA, use leerlingnummer as unique id
# 0.22: put new studens in the ad-group leerlingen, ad: add switch to reset password of respawned students, add verbose logging, api get students/staff: pass non-ascii as is
# 0.23: bugfix in ad, added a default password, deleted students can be deactivated or not in AD,
# 0.24: logger, more and longer logfiles.  Added functionality to remove students from a klas they do not belong to
# 0.25: bugfixed typo
# 0.26: enable smartschool-login.  rfid-fro-cardpresso: replace q with a
# 0.27: extended student search
# 0.28: students with name that is already present: add sufix (last 2 digits of leerlingnummer)
# 0.29: add logging.  From wisa, email is added for new students only (can change when address already exists in AD)
# 0.30: bugfixed user-levels.
# 0.31: bugfix and make email searchable
# 0.32: AD: existing student in AD, new in SDH -> get e-mailaddress from AD in case it is different from template-address
# 0.33: cardpresso table: search in additional fields
# 0.34: cardpresso table: small bugfix
# 0.35: speed up deleting of badges.  Use API key.  Added filter (klassen)
# 0.36: switch to allow new users via smartschool or not
# 0.37: smartschool login: ignore case
# 0.38: bugfix delete badges
# 0.39: reworked photo
# 0.40: when trying to find a photo, use the leerlingnummer as well
# 0.41: add functionality to change the RFID code with a badgereader and forward the new code to AD
# 0.42: when updating RFID code, show name of student
# 0.43: students: get all usernames from ad (once) and store in SDH.  Added functionality to store new RFID directly to papercut
# 0.44: set the RFID of staff as well
# 0.45: added feature to udpate password.  Use formio in popup
# 0.46: add file to git
# 0.47: bugfix: update of RFID to sdh takes into account that the student is not present anymore
# 0.48: bugfix, change spaces in field 'middag' to hashes to prevent stripping
# 0.49: refactored ad.py.  Added functionality to test database integrity
# 0.50: update database integrity check.  Introduced column roepnaam
# 0.51: AD, displayname should be first-name last-name.  Added code to update already existing entries in AD
# 0.52: reworked ad.py.  Take roepnaam into account when adding/changing student names
# 0.53: reworked cron module
# 0.54: small bugfix and added ' to not allowed characters in email
# 0.55: database integerity check: bugfix roepnaam check
# 0.56: small bugifx
# 0.57: dabase integrity check: remove issues. Small bugfixes
# 0.58: bugfix settings of type json.  Added code to get the computer name from AD
# 0.59: update get computers from AD and bugfix json settings
# 0.60: small update
# 0.61: wisa changed its epxort encoding
# 0.62: datatables update: use objects. Users: use popups to add/delete/update users
# 0.63: students: moved from js-script to module. Moved js to static folder.  User: add/delete/update handled via popups.
# 0.64: moved remaining views to modules
# 0.65: small updates.  Implemented cardpresso-delete as users-delete.  Datatables: introduced context (ctx).  Api-key: introduced levels
# 0.66: add staff-prive-email
# 0.67: moved popups to settings so that they can be changed dynamically
# 0.68: first steps with azure
# 0.69: staff: added extra field.  Adding functionality to edit field inline.
# 0.70: staff: add/update/delete staffs from webinterface
# 0.71: add staff: send email to new staff.  Bugfix wisa-import: exception when a field is present in the import which is not present in the Staff/Student class
# 0.72: error logs can be mailed.  Small bugfix in student-computers.  Import students: protect from student being present twice
# 0.73: import staff from wisa AND adding staff manually is ok.
# 1.0: version 1.0
# 1.1: if student already in AD, get username from AD.  Update in search
# 1.2: bugfix filters
# 1.3: bugfix clear-filter-setting
# 1.4: updated API to get photos.  Bugfix manually-added-staff; if not present in WISA then do not delete from database when stamboeknummer is empty
# 1.5: bugfix paging/slicing
# 1.6: app_context required in cron-task.  api-get-students: added start/stop for pagination
# 1.7: bugfix AD, handle errors. Bugfix logging and sql.
# 1.8: API update, getting size of photos
# 1.10: papercut, store current rfid code in secondary-card-number.
# 1.11: api, update required level to add staff and update staff/student
# 1.12: papercut, when a badge is re-used, delete the old entry.  Bugfix api, get-staff.  Set default dates in database
# 1.13: update email of already imported, new staff: resend the invitation if email changed and password not updated yet
# 1.14: update staff expire date: did not ripple through to AD
# 1.15: small update
# 1.16: import students from informat.  Added testmode.  Simplify current_schoolyear
# 1.17: update model::get and model::get_m, upgrade of filtering.  Update API keys, each key has a tag now
# 1.18: added api-info-html.  Bugfixed API logging
# 1.19 Bugfixed API logging
# 1.20 Bugfixed API logging
# 1.21: moved api info page to settings
# 1.21-informat_student_smartschool-1: cleanup. Reworked "current schoolyear".  Reworked cron (not active during summer).  Sync per deelschool.  Added "like" to model::get_multiple
# 1.21-informat_student_smartschool-2: added db-table klas.  Do not delete students during summerholiday.  Added button to sync test-klassen.  Reworked db-table students
# 1.21-informat_student_smartschool-3: debugged informat import.  Added smartschool sync
# 1.21-informat_student_smartschool-4: added student-status, export and send info-email.  Get multiple, added ids-field
# 1.21-informat_student_smartschool-5: update import from informat.  Update export to smartschool
# 1.21-informat_student_smartschool-6: classroom.cloud specific: use user-login as email
# 1.21-informat_student_smartschool-7: merged import-staff-from-informat.
# 1.22: merged from 1.21-informat_student_smartschool-7
# 1.23: badges: added functionality to manually transfer the rfid to the students.  Small updates and small bugfixes
# 1.24: bugfix use of cron-opaque-parameter.  Bugfix import staff from informat.
# 1.25: bugfix staff-popup.  Small bugfixes
# 1.26: bugfix informat import: ignore None-values
# 1.27: added students-to-smartschool
# 1.28: small bugfix
# 1.29: infomail smartschool, chose parents or student
# 1.30: smartschool, teacher-code bugfix
# 1.31: smartschool, bugfix
# 1.31: smartschool, bugfix teachers without internal number
# 1.32: update version number
# 1.33: cardpresso, add klas filter
# 1.34: smartschool, detect teachers without internnummer
# 1.35: smartschool export, add emailaddress
# 1.36: student, cardpresso overview, filter on klasgroep iso klas
# 1.37: photo, changed photos were not picked up
# 1.38: added script to check if lln/klassen are correct over informat, sdh and smartschool
# 1.39: added deelscholen to klasgroepen filter
# 1.40: small bugfix, OKAN iso OK
# 1.41: cardpresso, use badge to update rfid
# 1.42: address of student: use Domicilie-adres
# 1.43: bugfix inactive students, remove from klas.  AD bugfix, delete pager if empty rfid.  Bugfix cardpresso rfid to main database, could be overwritten when other parameters were changed.
# Informat bugfix, do not crash when teacher has no smartschool internal code
# 1.44: new students get automatically smartschool info via email
# 1.45: bugfix send email with smartschool info, take into account that ids can be empty
# 1.46: bugfix, do not reset changed flag at informat import
# 1.47: bugfix AD, remove empty rfid code
# 1.48: small update
# 1.49: new student, send smartschool info also to parents
# 1.50: send smartschool info: show confirmation window
# 1.51: added Logging, to log/display user actions/results.  Bugfix datatables.html, do not include right_click.js if not needed.  Reworked send-ss-info to students/parents.
# 1.52: improved user-logging.  Updated ss-send-info via api
# 1.53: user-logging, add owner-filtering
# 1.54: backup and bugfix
# 1.55: small bugfix
# 1.56: small bugfix
# 1.57: print smartschool info, ok for students and coaccounts.  Multiple students in one document
# 1.58: enable send-smartschool-info
# 1.59: cron-cycle, do not stop when exception occurs.  smartschool, optimized code.
# 1.60: pdfkit, set path to executable
# 1.61: bugfix send email
# 1.62: merge from leerid
# 1.63: reworked navbar. Student-detail, added dropdown menu.
# 1.64: when mailing/printo smartschool info, a checkbox can be ticked to indicate if the smartschool password needs to reset.
# 1.65: small bugfix
# 1.66: informat import, key-replace, take empty fields into account
# 1.67: bugfix cardpresso, when quering the database, filters needed to be a list.  Added a test in multiple_get
# 1.68: version fix
# 1.69: students, email fix, use proxyAddresses to hold emailaddress
# 1.70: AD, add klascode to displayname
# 1.71: bugfix cron AD staff, check opaque parameters
# 1.72: bugfix socketio, increase timeouts
# 1.73: version bugfix
# 1.74: AD, if new student exists, copy username to db.   Update pop-ups. Students, implement data upload (xlsx) with flexible columnnaming and keys.
# 1.75: added dropdown menu on Students page for not-student-related functionality
# 1.75-offload_sync-1: add broadcast warning to inform every user when something is ongoing

@flask_app.context_processor
def inject_defaults():
    return dict(version='@ 2022 MB. V1.75-offload_sync-1', title=flask_app.config['HTML_TITLE'], site_name=flask_app.config['SITE_NAME'], testmode = flask_app.testmode)


db = SQLAlchemy()
login_manager = LoginManager()


#  The original werkzeug-url-converter cannot handle negative integers (e.g. asset/add/-1/1)
class IntegerConverter(OrigIntegerConvertor):
    regex = r'-?\d+'
    num_convert = int


# set up logging
log_werkzeug = logging.getLogger('werkzeug')
log_werkzeug.setLevel(flask_app.config['WERKZEUG_LOG_LEVEL'])
# log_werkzeug.setLevel(logging.ERROR)

#  enable logging
top_log_handle = flask_app.config['LOG_HANDLE']
log = logging.getLogger(top_log_handle)
# support custom filtering while logging
class MyLogFilter(logging.Filter):
    def filter(self, record):
        record.username = current_user.username if current_user and current_user.is_active else 'NONE'
        return True

LOG_FILENAME = os.path.join(sys.path[0], app_config[config_name].STATIC_PATH, f'log/{flask_app.config["LOG_FILE"]}.txt')
try:
    log_level = getattr(logging, app_config[config_name].LOG_LEVEL)
except:
    log_level = getattr(logging, 'INFO')
log.setLevel(log_level)
log.addFilter(MyLogFilter())
log_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=1024 * 1024, backupCount=20)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(username)s - %(name)s - %(message)s')
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)


email_log_handler = None
def subscribe_email_log_handler_cb(cb):
    global email_log_handler
    email_log_handler = cb


# if the log-error-message is FLUSH-TO-EMAIL, all error logs are emailed and the buffer is cleared.
class MyBufferingHandler(logging.handlers.BufferingHandler):
    def flush(self):
        if len(self.buffer) > 1:
            message_body = ""
            for b in self.buffer:
                message_body += self.format(b) + "<br>"
            with flask_app.app_context():
                if email_log_handler:
                    email_log_handler(message_body)
        self.buffer = []

    def shouldFlush(self, record):
        return record.msg == "FLUSH-TO-EMAIL"


buf_handler = MyBufferingHandler(2)
buf_handler.setLevel("ERROR")
log.addHandler(buf_handler)
buf_handler.setFormatter(log_formatter)


log.info(f"start {flask_app.config['SITE_NAME']}")


jsglue = JSGlue(flask_app)
db.app = flask_app  #  hack:-(
db.init_app(flask_app)


socketio = SocketIO(flask_app, async_mode=flask_app.config['SOCKETIO_ASYNC_MODE'], cors_allowed_origins=flask_app.config['SOCKETIO_CORS_ALLOWED_ORIGIN'])


# configure e-mailclient
email = Mail(flask_app)
send_emails = False
flask_app.extensions['mail'].debug = 0


def create_admin():
    try:
        from app.data.user import User
        find_admin = User.query.filter(User.username == 'admin').first()
        if not find_admin:
            admin = User(username='admin', password='admin', level=User.LEVEL.ADMIN, user_type=User.USER_TYPE.LOCAL)
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


flask_app.url_map.converters['int'] = IntegerConverter
login_manager.init_app(flask_app)
login_manager.login_message = 'Je moet aangemeld zijn om deze pagina te zien!'
login_manager.login_view = 'auth.login'

migrate = Migrate(flask_app, db)

SCHEDULER_API_ENABLED = True
ap_scheduler = APScheduler()
ap_scheduler.init_app(flask_app)
ap_scheduler.start()

if 'db' in sys.argv:
    from app.data import models
else:
    create_admin()  #  Only once

    # decorator to grant access to admins only
    def admin_required(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_at_least_admin:
                abort(403)
            return func(*args, **kwargs)
        return decorated_view


    # decorator to grant access to at least supervisors
    def supervisor_required(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_at_least_supervisor:
                abort(403)
            return func(*args, **kwargs)
        return decorated_view

    from app.presentation.view import auth, user, settings,  api, logging, student, staff, cardpresso
    flask_app.register_blueprint(api.api)
    flask_app.register_blueprint(auth.auth)
    flask_app.register_blueprint(user.user)
    flask_app.register_blueprint(settings.settings)
    flask_app.register_blueprint(student.student)
    flask_app.register_blueprint(staff.staff)
    flask_app.register_blueprint(cardpresso.cardpresso)
    flask_app.register_blueprint(logging.logging)

    @flask_app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', title='Forbidden'), 403

    @flask_app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html', title='Page Not Found'), 404

    @flask_app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html', title='Server Error'), 500

    @flask_app.route('/500')
    def error_500():
        abort(500)


