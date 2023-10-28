import {subscribe_right_click} from "../base/right_click.js";
import {check_rfid} from "./rfid.js";
import {update_password} from "./password.js";
import {database_integrity_check} from "./database.js";
import {ctx} from "../datatables/datatables.js"
import {smartschool_print_info, smartschool_mail_info} from "./sdh.js";
import {init_popup, hide_popup, show_popup, add_to_popup_body, create_p_element, subscribe_btn_ok, create_checkbox_element} from "../base/popup.js";
import {append_menu} from "../base/base.js";

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
            method: 'POST', body: form_data
        });
    }
    input.click();
}

async function upload_student_data() {
    const form = document.createElement("form")
    const input = document.createElement('input');
    form.appendChild(input)
    init_popup({title: "Upload studenten data", width: "75%"})
    const info = create_p_element(
        "Upload een xlsx bestand met relevante data.  De relevante kolomnaam moet telkens overeenkomen met de databasekolom.  Indien niet, dan moeten er instructies worden opgenomen in de tabel<br>" +
        "Bovenste lijn: kolomnaam (vb. naam, voornaam, klas, maandag, dinsdag, donderdag, vrijdag)<br>" +
        "Eventuele extra instructies (sleutelwoord steed in kolom A, eerste parameter in B, tweede in C, enz...):<br>" +
        "$alias$ klas klascode (pas de naam van een kolom aan van klas naar klascode)<br>" +
        "$key$ voornaam-naam-klascode (standaard sleutel is 'leerlingnummer', maar is hier aangepast door de kolom naam, voornaam en klascode achter elkaar te plakken)<br>" +
        "$concat$ soep maandag-dinsdag-donderdag-vrijdag (maak een nieuw kolom 'soep' door de kolommen maandag..vrijdag achter elkaar te plakken)<br>" +
        "$fields$ soep (lijst met kolommen, gescheiden door een ',' die moeten worden aangepast in de database) "
    )
    add_to_popup_body(info)
    add_to_popup_body(form)
    input.type = 'file';
    input.name = "student_data_file";
    input.multiple = false;
    input.accept = ".xlsx,.xls"
    input.onchange = async e => {
        var file = e.target.files[0];
        const form_data = new FormData(form);
        const ret = await fetch(Flask.url_for('api.student_data_upload'), {
            headers: {'x-api-key': ctx.api_key,},
            method: 'POST', body: form_data
        });
        const status = await ret.json();
        if (status.status) {
            init_popup({title: "Upload studenten data", width: "65%", save_button: false, ok_button: true})
            const info = create_p_element(
                `Aantal gevonden studenten: ${status.data.nbr_found}<br>` +
                `Aantal niet gevonden studenten: ${status.data.nbr_not_found}<br>` +
                `Aantal studenten die meerdere keren voorkomen: ${status.data.nbr_double}<br>` +
                `Aantal ongeldige lijnen in invoerbestand: ${status.data.nbr_invalid}<br>` +
                "Als dit oké is, druk op Ok, anders Annuleer<br>" +
                "Hieronder is een voorbeeld te zien van de data:"
            )
            add_to_popup_body(info);
            const table = document.createElement("table");
            const nbr_rows =  status.data.students.length >= 5 ? 5 : status.data.students.length;
            for(let i=0; i < nbr_rows; i++) {
                const row = table.insertRow(i);
                row.insertCell(0).innerHTML = status.data.students[i].key;
                status.data.fields.forEach((item, j) => row.insertCell(j+1).innerHTML = status.data.students[i].data[item]);
            }
            const header = table.createTHead();
            const header_row = header.insertRow(0);
            header_row.insertCell(0).innerHTML = "sleutel";
            status.data.fields.forEach((item, i) => header_row.insertCell(i+1).innerHTML = item);
            add_to_popup_body(table);
            subscribe_btn_ok(async (data) => {
                const ret = await fetch(Flask.url_for('api.student_data_update'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(data)});
                const status = await ret.json();
                hide_popup()
                if (status.status) {
                    bootbox.alert("Studenten zijn aangepast")
                } else {
                    bootbox.alert(`Fout bij het uploaden van de data: ${status.data}`)
                }
            }, status.data);
            show_popup();
        } else {
            bootbox.alert(`Fout bij het uploaden van de data: ${status.data}`)
        }
    }
    show_popup()

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
subscribe_right_click('student-data-upload', (item, ids) => upload_student_data());

var menu = [
    [[
        [() => new_vsk_numbers(), "Vsk nummers", 5],
        [() => database_integrity_check('api.database_integrity_check', ctx.popups['database-integrity-check']), "Database Integriteitscontrole", 5],
        [() => upload_leerid(), "Upload LeerID bestand", 5],
        [() => upload_student_data(), "Upload leerling gegevens", 5],
    ], "Extra", 5],
]

append_menu(menu)
