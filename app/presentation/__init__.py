from app import flask_app, version
from app.application.util import get_keys
from flask_login import current_user

@flask_app.context_processor
def inject_defaults():
    api_key = get_keys(current_user.level)[0] if current_user.is_active else ""
    return dict(version=f'@ 2023 MB. {version}', title=flask_app.config['HTML_TITLE'], site_name=flask_app.config['SITE_NAME'], testmode = flask_app.testmode, api_key=api_key)


#called each time a request is received from the client.
# @flask_app.context_processor
# def inject_academic_year():
#     test_server = mutils.return_common_info()
#     return dict(test_server=test_server)
#
