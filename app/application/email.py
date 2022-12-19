from app import email, flask_app
from app.data import settings as msettings
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


def send_standard_message(email_to, subject, message):
    if email_to:
        body = f'{datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}<br>' \
               f'{message}<br><br>' \
               f'School Data Hub'
        send_email(email_to, subject, body)
