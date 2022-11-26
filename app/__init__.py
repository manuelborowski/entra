from flask import Flask, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_jsglue import JSGlue
from werkzeug.routing import IntegerConverter as OrigIntegerConvertor
import logging.handlers, os, sys
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


@flask_app.context_processor
def inject_defaults():
    return dict(version='@ 2022 MB. V0.63', title=flask_app.config['HTML_TITLE'], site_name=flask_app.config['SITE_NAME'])


#  enable logging
log = logging.getLogger(flask_app.config['LOG_HANDLE'])


db = SQLAlchemy()
login_manager = LoginManager()


#  The original werkzeug-url-converter cannot handle negative integers (e.g. asset/add/-1/1)
class IntegerConverter(OrigIntegerConvertor):
    regex = r'-?\d+'
    num_convert = int


# support custom filtering while logging
class MyLogFilter(logging.Filter):
    def filter(self, record):
        record.username = current_user.username if current_user and current_user.is_active else 'NONE'
        return True


# set up logging
log_werkzeug = logging.getLogger('werkzeug')
log_werkzeug.setLevel(flask_app.config['WERKZEUG_LOG_LEVEL'])
# log_werkzeug.setLevel(logging.ERROR)

LOG_FILENAME = os.path.join(sys.path[0], app_config[config_name].STATIC_PATH, f'log/{flask_app.config["LOG_FILE"]}.txt')
try:
    log_level = getattr(logging, app_config[config_name].LOG_LEVEL)
except:
    log_level = getattr(logging, 'INFO')
log.setLevel(log_level)
log.addFilter(MyLogFilter())
log_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=1024 * 1024, backupCount=20)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(username)s - %(message)s')
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)

log.info(f"start {flask_app.config['SITE_NAME']}")

jsglue = JSGlue(flask_app)
db.app = flask_app  #  hack:-(
db.init_app(flask_app)

socketio = SocketIO(flask_app, async_mode=flask_app.config['SOCKETIO_ASYNC_MODE'], ping_timeout=10, ping_interval=5, cors_allowed_origins=flask_app.config['SOCKETIO_CORS_ALLOWED_ORIGIN'])


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

# configure e-mailclient
email = Mail(flask_app)
send_emails = False
flask_app.extensions['mail'].debug = 0

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

    from app.presentation.view import auth, user, settings,  api, warning, student, staff, cardpresso
    flask_app.register_blueprint(api.api)
    flask_app.register_blueprint(auth.auth)
    flask_app.register_blueprint(user.user)
    flask_app.register_blueprint(settings.settings)
    flask_app.register_blueprint(student.student)
    flask_app.register_blueprint(staff.staff)
    flask_app.register_blueprint(cardpresso.cardpresso)
    flask_app.register_blueprint(warning.warning)

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


