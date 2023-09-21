import {subscribe_right_click} from "../base/right_click.js";
import {check_rfid} from "./rfid.js";
import {update_password} from "./password.js";
import {database_integrity_check} from "./database.js";
import {ctx, get_data_of_row} from "../datatables/datatables.js"

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

async function smartschoolinfo_to_student(ids, to_student) {
    const target = to_student ? "leerling(en)" : "ouders";
    bootbox.confirm(`Smartschool info naar ${target} sturen?`,
        async result => {
            if (result) {
                const ret = await fetch(Flask.url_for('api.smartschool_send_info'), {headers: {'x-api-key': ctx.api_key,},
                    method: 'POST', body: JSON.stringify({ids, to_student}),});
                const status = await ret.json();
                if (status.status) {
                    if (to_student)
                        bootbox.alert(`Smartschool info is naar ${status.data} leerling(en) gestuurd`)
                    else
                        bootbox.alert(`Smartschool info is naar de ouders van ${status.data} leerlingen gestuurd`)
                } else {
                    bootbox.alert(`Fout: ${status.data}`)
                }
            }

        });
}


subscribe_right_click('new-vsk-numbers', (item, ids) => new_vsk_numbers());
subscribe_right_click('check-rfid', (item, ids) => check_rfid(ids, 'api.student_update'));
subscribe_right_click('update-password', (item, ids) => update_password(ids, 'api.student_update', ctx.popups['update-password']));
subscribe_right_click('database-integrity-check', (item, ids) => database_integrity_check('api.database_integrity_check', ctx.popups['database-integrity-check']));
subscribe_right_click('export-smartschool', (item, ids) => export_smartschool_info(ids));
subscribe_right_click('info-email', (item, ids) => smartschoolinfo_to_student(ids, true));
subscribe_right_click('info-email-ouders', (item, ids) => smartschoolinfo_to_student(ids, false));
