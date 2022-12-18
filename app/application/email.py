from app import email, flask_app
from app.data import settings as msettings
from flask_mail import Message
import datetime

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())



def send_email(to_list, subject, content):
    log.info(f'send_email to: {to_list}, subject: {subject}')
    enable = msettings.get_configuration_setting('email-enable-send-email')
    if enable:
        sender = flask_app.config['MAIL_USERNAME']
        msg = Message(sender=sender, recipients=to_list, subject=subject, html=content)
        try:
            email.send(msg)
            return True
        except Exception as e:
            log.error(f'send_email: ERROR, could not send email: {e}')
            if 'Temporary server error. Please try again later' in str(e):
                try:
                    email.send(msg)
                    return True
                except Exception as e:
                    log.error(f'send_email: ERROR, could not send email: {e}')
        return False
    else:
        log.info('email server is not enabled')
        return False


def compose_message(receipients_template, subject, message):
    email_to = msettings.get_list(receipients_template)
    if email_to:
        body = f'{datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}<br>' \
               f'{message}<br><br>' \
               f'School Data Hub'

        send_email(email_to, subject, body)


def get_email_recipients(template):
    recipients = msettings.get_configuration_setting(template).split('\n')
    out = [r.strip() for r in recipients if '#' not in r]
    return out
