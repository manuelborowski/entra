from app import email, flask_app, subscribe_email_log_handler_cb
from app.data import settings as msettings
from app.application import util as mutil
import datetime, sys
from app.data.entra import entra

#logging on file level
import logging
from app import MyLogFilter, top_log_handle

log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def send_email(to_list, subject, content):
    log.info(f'{sys._getframe().f_code.co_name}: send_email to: {to_list}, subject: {subject}')
    enable = msettings.get_configuration_setting('email-enable-send-email')
    if enable:
        try:
            return entra.send_mail(to_list, subject, content)
        except Exception as e:
            log.error(f'{sys._getframe().f_code.co_name}: send_email: ERROR, could not send email: {e}')
        return False
    else:
        log.info(f'{sys._getframe().f_code.co_name}: email server is not enabled')
        return False


def api_email_send(data):
    if not isinstance(data, dict):
        return {"status": False, "data": "Expected a JSON object."}

    recipients = data.get("recipients")
    if isinstance(recipients, str):
        recipients = [recipients]
    if not isinstance(recipients, list) or not recipients or any(not isinstance(address, str) or not address.strip() or "\r" in address or "\n" in address for address in recipients):
        return {"status": False, "data": "recipients must be an email address or a non-empty list of email addresses."}

    subject = data.get("subject")
    if not isinstance(subject, str) or not subject.strip() or "\r" in subject or "\n" in subject:
        return {"status": False, "data": "subject must be a non-empty single-line string."}

    content = data.get("content")
    if not isinstance(content, str) or not content.strip():
        return {"status": False, "data": "content must be a non-empty string."}

    if send_email([address.strip() for address in recipients], subject, content):
        return {"status": True, "data": "Email accepted for sending."}
    return {"status": False, "data": "Email could not be sent."}


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
        send_inform_message(to_list, "ENTRA ERROR LOG", message_body)

subscribe_email_log_handler_cb(email_log_handler)

#send message to new staff
def send_new_staff_message(staff, default_password):
        template = msettings.get_configuration_setting("email-new-staff-html")
        template = mutil.find_and_replace(template, {"%%VOORNAAM%%": staff.voornaam, "%%WACHTWOORD%%": default_password, "%%GEBRUIKERSNAAM%%": staff.code})
        send_email([staff.prive_email], "Je nieuwe schoolaccount", template)
