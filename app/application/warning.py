from app.application.socketio import broadcast_message
import app.data.settings as msettings


def warning_on(message):
    msettings.set_configuration_setting("generic-warning-message", message)
    broadcast_message("warning-on", {"data": message})


def warning_off():
    msettings.set_configuration_setting("generic-warning-message", "")
    broadcast_message("warning-off")


def warning_get_message():
    return msettings.get_configuration_setting("generic-warning-message")