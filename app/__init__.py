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

# 0.1: copy of school-data-hub V1.80

version = "V0.1"


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

    from app.presentation.view import auth, user, settings,  api, logging, student, staff, group
    flask_app.register_blueprint(api.api)
    flask_app.register_blueprint(auth.auth)
    flask_app.register_blueprint(user.user)
    flask_app.register_blueprint(settings.settings)
    flask_app.register_blueprint(student.student)
    flask_app.register_blueprint(group.group)
    flask_app.register_blueprint(staff.staff)
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


