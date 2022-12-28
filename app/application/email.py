from app import email, flask_app, subscribe_email_log_handler_cb
from app.data import settings as msettings
from app.application import util as mutil
from flask_mail import Message
import datetime, sys


#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def send_email(to_list, subject, content):
    log.info(f'{sys._getframe().f_code.co_name}: send_email to: {to_list}, subject: {subject}')
    enable = msettings.get_configuration_setting('email-enable-send-email')
    if enable:
        sender = flask_app.config['MAIL_USERNAME']
        msg = Message(sender=sender, recipients=to_list, subject=subject, html=content)
        try:
            email.send(msg)
            return True
        except Exception as e:
            log.error(f'{sys._getframe().f_code.co_name}: send_email: ERROR, could not send email: {e}')
            if 'Temporary server error. Please try again later' in str(e):
                try:
                    email.send(msg)
                    return True
                except Exception as e:
                    log.error(f'{sys._getframe().f_code.co_name}: send_email: ERROR, could not send email: {e}')
        return False
    else:
        log.info('{sys._getframe().f_code.co_name}: email server is not enabled')
        return False


def send_inform_message(email_to, subject, message):
    if email_to:
        body = f'{datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}<br>' \
               f'{message}<br><br>' \
               f'School Data Hub'
        send_email(email_to, subject, body)


# from app import email_log_handler
def email_log_handler(message_body):
    to_list = msettings.get_list("logging-inform-emails")
    if to_list:
        send_inform_message(to_list, "SDH ERROR LOG", message_body)


subscribe_email_log_handler_cb(email_log_handler)


#send message to new staff
def send_new_staff_message(staff, default_password):
        template = msettings.get_configuration_setting("email-new-staff-html")
        template = mutil.find_and_replace(template, {"%%VOORNAAM%%": staff.voornaam, "%%WACHTWOORD%%": default_password, "%%GEBRUIKERSNAAM%%": staff.code})
        send_email([staff.prive_email], "Je nieuwe schoolaccount", template)
