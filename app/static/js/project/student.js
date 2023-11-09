import {subscribe_right_click} from "../base/right_click.js";
import {check_rfid} from "./rfid.js";
import {update_password} from "./password.js";
import {ctx} from "../datatables/datatables.js"
import {smartschool_print_info, smartschool_mail_info} from "./sdh.js";
import {init_popup, hide_popup, show_popup, add_to_popup_body, create_p_element, subscribe_btn_ok} from "../base/popup.js";

async function update_vsk_numbers(start) {
    const ret = await fetch(Flask.url_for('api.update_vsk_number'), {headers: {'x-api-key': api_key,}, method: 'POST', body: JSON.stringify({start}),});
    const status = await ret.json();
    if (status.status) {
        bootbox.alert(`Er zijn ${status.data} nieuwe nummers toegekend`)
    } else {
        bootbox.alert(`Fout bij het toekennen van de nieuwe nummers: ${status.data}`)
    }
    ctx.reload_table();
}

async function clear_vsk_numbers() {
    const ret = await fetch(Flask.url_for('api.clear_vsk_numbers'), {headers: {'x-api-key': api_key,}, method: 'POST'});
    const status = await ret.json();
    if (status.status) {
        bootbox.alert(`Alle nummers (${status.data}) zijn gewist`)
    } else {
        bootbox.alert(`Fout bij het wissen van de nummers: ${status.data}`)
    }
    ctx.reload_table();
}


async function export_smartschool_info(ids) {
    var hiddenElement = document.createElement('a');
    hiddenElement.href = Flask.url_for('student.export_smartschool', {ids: JSON.stringify(ids)});
    hiddenElement.target = '_blank';
    hiddenElement.click();
}



async function send_leerid(ids) {
    bootbox.confirm(`LeerID naar leerlingen sturen?`,
        async result => {
            if (result) {
                const ret = await fetch(Flask.url_for('api.leerid_send'), {
                    headers: {'x-api-key': api_key,},
                    method: 'POST', body: JSON.stringify({ids}),
                });
                const status = await ret.json();
                bootbox.alert(status.data);
            }
        });
}


subscribe_right_click('check-rfid', (item, ids) => check_rfid(ids, 'api.student_update'));
subscribe_right_click('update-password', (item, ids) => update_password(ids, 'api.student_update', ctx.popups['update-password']));
subscribe_right_click('export-smartschool', (item, ids) => export_smartschool_info(ids));
subscribe_right_click('info-email', (item, ids) => smartschool_mail_info(ids, 0, api_key));
subscribe_right_click('info-print', (item, ids) => smartschool_print_info(ids, 0, api_key));
subscribe_right_click('info-email-ouders', (item, ids) => smartschool_mail_info(ids, 3, api_key));
subscribe_right_click('info-print-ouders', (item, ids) => smartschool_print_info(ids, 3, api_key));
subscribe_right_click('leerid-send', (item, ids) => send_leerid(ids));

