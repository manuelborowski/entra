import { socketio } from "../base/socketio.js";
import { busy_indication_on, busy_indication_off } from "../base/base.js";

var _form = null;
$(document).ready(function () {
    socketio.start(null, null);
    socketio.subscribe_on_receive("settings", socketio_settings_ack);
    socketio.subscribe_on_receive("event", socketio_event_ack);
    load_formio_form();
});


function load_formio_form() {
    Formio.createForm(document.getElementById('configuration-settings'), data.template).then((form) => {
        _form = form
        var button_id; // hack to set the value of the button, which was just clicked, to false again.
        $.each(data.default, function (k, v) {
            try {
                form.getComponent(k).setValue(v);
            } catch (error) {
                return;
            }
        });
        form.on('submit', function(submission) {
            socketio_transmit_setting('data', JSON.stringify((submission.data)))
            _form.getComponentById(button_id).setValue(false);
        })
        form.on('submitButton', button => {
            button_id = button.instance.id;
        });
    });
}


function socketio_settings_ack(type, data) {
    _form.emit('submitDone')
    // setTimeout(function() {$("#configuration-settings .alert").css("display", "none");}, 1000);
    setTimeout(function() {
        document.querySelectorAll("[ref=buttonMessageContainer]").forEach(b => b.style.display="none");
        document.querySelectorAll("[ref=button]").forEach(b => {
            b.classList.remove('btn-success');
            b.classList.remove('submit-success');
        });
    }, 1000);
    if (!data.status) {
        bootbox.alert("Warning, following error appeared:<br>" + data.message);
    }
    busy_indication_off();
}

function socketio_event_ack(type, data) {
    busy_indication_off();
    if (data.status) {
        bootbox.alert(data.message);
    } else {
        bootbox.alert("Warning, following error appeared:<br>" + data.message);
    }
}

function socketio_transmit_setting(setting, value) {
    busy_indication_on();
    socketio.send_to_server('settings', {setting: setting, value: value});
    return false;
}

function socketio_transmit_event(event) {
    socketio.send_to_server('event', {event: event});
    return false;
}
