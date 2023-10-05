import {subscribe_right_click} from "../base/right_click.js";
import {check_rfid} from "./rfid.js";
import {update_password} from "./password.js";
import {database_integrity_check} from "./database.js";
import {ctx, get_data_of_row} from "../datatables/datatables.js"
import { smartschool_print_info, smartschool_mail_info} from "./sdh.js";

async function update_vsk_numbers(start) {
    const ret = await fetch(Flask.url_for('api.update_vsk_number'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify({start}),});
    const status = await ret.json();
    if (status.status) {
        bootbox.alert(`Er zijn ${status.data} nieuwe nummers toegekend`)
    } else {
        bootbox.alert(`Fout bij het toekennen van de nieuwe nummers: ${status.data}`)
    }
    ctx.reload_table();
}

async function clear_vsk_numbers() {
    const ret = await fetch(Flask.url_for('api.clear_vsk_numbers'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST'});
    const status = await ret.json();
    if (status.status) {
        bootbox.alert(`Alle nummers (${status.data}) zijn gewist`)
    } else {
        bootbox.alert(`Fout bij het wissen van de nummers: ${status.data}`)
    }
    ctx.reload_table();
}

async function new_vsk_numbers() {
    const ret = await fetch(Flask.url_for('api.get_last_vsk_number'), {headers: {'x-api-key': ctx.api_key,}})
    const data = await ret.json();
    if (data.status) {
        if (data.data === -1) { // no numbers yet
            bootbox.prompt({
                title: "Er zijn nog geen nummers toegekend. Geef het startnummer in",
                inputType: "number",
                callback: result => {
                    if (result) update_vsk_numbers(result)
                }
            })
        } else {
            const start = parseInt(data.data);
            bootbox.dialog({
                title: 'Vsk nummers toekennen',
                message: `<p>Het eerstvolgende nummer is ${start}</p>`,
                buttons: {
                    ok: {
                        label: 'Ok',
                        className: 'btn-success',
                        callback: function () {
                            update_vsk_numbers(start)
                        }
                    },
                    cancel: {
                        label: 'Annuleren',
                        className: 'btn-warning',
                        callback: function () {

                        }
                    },
                    clear_all: {
                        label: 'Alle Vsk nummers wissen',
                        className: 'btn-danger',
                        callback: function () {
                            clear_vsk_numbers()
                        }
                    },
                }
            })
        }
    } else {
        bootbox.alert(`Sorry, er is iets fout gegaan: ${data.data}`)
    }
}

async function export_smartschool_info(ids) {
    var hiddenElement = document.createElement('a');
    hiddenElement.href = Flask.url_for('student.export_smartschool', {ids: JSON.stringify(ids)});
    hiddenElement.target = '_blank';
    hiddenElement.click();
}

async function upload_leerid() {
    const form = document.createElement("form")
    const input = document.createElement('input');
    form.appendChild(input)
    input.type = 'file';
    input.name = "leerid_file";
    input.multiple = true;
    input.accept = ".xlsx,.xls"
    input.onchange = e => {
        var file = e.target.files[0];
        const form_data = new FormData(form);
        const ret = fetch(Flask.url_for('api.leerid_upload'), {
            headers: {'x-api-key': ctx.api_key,},
            method: 'POST', body: form_data});
        console.log(file);
    }
    input.click();
}

async function send_leerid(ids) {
    bootbox.confirm(`LeerID naar leerlingen sturen?`,
        async result => {
            if (result) {
                const ret = await fetch(Flask.url_for('api.leerid_send'), {
                    headers: {'x-api-key': ctx.api_key,},
                    method: 'POST', body: JSON.stringify({ids}),
                });
                const status = await ret.json();
                bootbox.alert(status.data);
            }
        });
}


subscribe_right_click('new-vsk-numbers', (item, ids) => new_vsk_numbers());
subscribe_right_click('check-rfid', (item, ids) => check_rfid(ids, 'api.student_update'));
subscribe_right_click('update-password', (item, ids) => update_password(ids, 'api.student_update', ctx.popups['update-password']));
subscribe_right_click('database-integrity-check', (item, ids) => database_integrity_check('api.database_integrity_check', ctx.popups['database-integrity-check']));
subscribe_right_click('export-smartschool', (item, ids) => export_smartschool_info(ids));
subscribe_right_click('info-email', (item, ids) => smartschool_mail_info(ids, 0, ctx.api_key));
subscribe_right_click('info-print', (item, ids) => smartschool_print_info(ids, 0, ctx.api_key));
subscribe_right_click('info-email-ouders', (item, ids) => smartschool_mail_info(ids, 3, ctx.api_key));
subscribe_right_click('info-print-ouders', (item, ids) => smartschool_print_info(ids, 3, ctx.api_key));
subscribe_right_click('leerid-upload', (item, ids) => upload_leerid());
subscribe_right_click('leerid-send', (item, ids) => send_leerid(ids));
