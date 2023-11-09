import {socketio} from "./socketio.js";
import {add_to_popup_body, create_p_element, hide_popup, init_popup, show_popup, subscribe_btn_ok} from "./popup.js";

const navbar_element = document.querySelector("#navbar");
const logo_div = document.querySelector("#warning-logo");

export function flash_messages(list) {
    for (var i = 0; i < list.length; i++) {
        var message = list[i];
        bootbox.alert(message);
    }
}

export function busy_indication_on() {
    document.getElementsByClassName("busy-indicator")[0].style.display = "block";
}

export function busy_indication_off() {
    document.getElementsByClassName("busy-indicator")[0].style.display = "none";
}

const show_messsage = (type, data) => {
    logo_div.style.visibility = "visible";
    logo_div.querySelector("span").innerHTML = data.data;
}

const hide_messsage = () => {
    logo_div.style.visibility = "hidden";
}

socketio.subscribe_on_receive("warning-on", show_messsage);
socketio.subscribe_on_receive("warning-off", hide_messsage);


var menu = [
    ["student.show", "Studenten", 1],
    ["staff.show", "Personeel", 1],
    ["cardpresso.show", "Cardpresso", 3],
    ["logging.show", "Logging", 3],
    ["user.show", "Gebruikers", 5],
    ["settings.show", "Instellingen", 5],
    ["divider", "", 0],
    [[
        [() => new_vsk_numbers(), "Vsk nummers", 5],
        [() => upload_leerid(), "Upload LeerID bestand", 5],
        [() => upload_student_data(), "Upload leerling gegevens", 5],
        [() => sync_informat(), "Synchroniseer Informat", 3],
    ], "Extra", 3],
]


var buttons = [
]

export const new_menu = new_menu => {
    menu = new_menu;
}

$(document).ready(async () => {
    let dd_ctr = 0;
    for (const item of menu) {
        if (current_user_level >= item[2]) {
            const li = document.createElement("li");
            if (Array.isArray(item[0])) {
                // dropdown menu-item
                li.classList.add("nav-item", "dropdown");
                const a = document.createElement("a");
                li.appendChild(a)
                a.classList.add("nav-link", "dropdown-toggle");
                a.style.color = "white";
                a.href = "#";
                a.id = `dd${dd_ctr}`
                a.setAttribute("role", "button");
                a.setAttribute("data-toggle", "dropdown");
                a.setAttribute("aria-haspopup", true);
                a.setAttribute("aria-expanded", true);
                a.innerHTML = item[1];
                const div = document.createElement("div");
                li.appendChild(div)
                div.classList.add("dropdown-menu");
                div.setAttribute("aria-labelledby", `dd${dd_ctr}`)
                for (const sitem of item[0]) {
                    if (sitem[0] === "divider") {
                        const divd = document.createElement("div");
                        divd.classList.add("dropdown-divider");
                        div.appendChild(divd)
                    } else {
                        if (current_user_level >= sitem[2]) {
                            const a = document.createElement("a");
                            div.appendChild(a)
                            a.classList.add("dropdown-item");
                            if (typeof sitem[0] === "function") {
                                a.onclick = sitem[0];
                            } else {
                                a.href = Flask.url_for(sitem[0]);
                            }
                            a.innerHTML = sitem[1]
                        }
                    }
                }
                dd_ctr++;
            } else if (item[0]==="divider") {
                // regular menu-item
                li.classList.add("nav-item");
                const a = document.createElement("a");
                a.classList.add("nav-link");
                a.style.color = "white";
                a.style.backgroundColor = "white";
                a.style.paddingLeft = 0;
                a.style.paddingRight = 0;
                a.href = "#";
                a.innerHTML = "i";
                li.appendChild(a);
            } else {
                // regular menu-item
                const url_path = Flask.url_for(item[0]);
                li.classList.add("nav-item");
                const a = document.createElement("a");
                a.classList.add("nav-link");
                if (window.location.href.includes(url_path)) {
                    a.classList.add("active");
                }
                a.href = url_path;
                a.innerHTML = item[1];
                li.appendChild(a);
            }
            navbar_element.appendChild(li);
        }
    }
    logo_div.style.visibility="hidden";
    logo_div.classList.add("tooltip");
    const logo = new Image(30);
    logo.classList.add("blink");
    logo.src = "/static/img/warning.png";
    logo_div.appendChild(logo);
    const tt_text = document.createElement("span");
    tt_text.classList.add("tooltiptext");
    logo_div.appendChild(tt_text);

    if (testmode) {
        const li = document.createElement("li");
        li.classList.add("nav-item");
        const a = document.createElement("a");
        a.classList.add("navbar-brand");
        a.href = "#";
        a.innerHTML = "TEST SITE"
        li.appendChild(a);
        navbar_element.appendChild(li);
    }

    //Check if there is an ongoing warning
    const ret = await fetch(Flask.url_for('api.get_warning'));
    const resp = await ret.json();
    if (resp.message !=="") {
        show_messsage(null, {data: resp.message});
    }

});

async function new_vsk_numbers() {
    const ret = await fetch(Flask.url_for('api.get_last_vsk_number'), {headers: {'x-api-key': api_key,}})
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
            headers: {'x-api-key': api_key,},
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
            headers: {'x-api-key': api_key,},
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
                const ret = await fetch(Flask.url_for('api.student_data_update'), {headers: {'x-api-key': api_key,}, method: 'POST', body: JSON.stringify(data)});
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



async function sync_informat() {
    bootbox.confirm(`Syncen met Informat?<br>Dit kan tot 20 seconden duren`,
        async result => {
            if (result) {
                const ret = await fetch(Flask.url_for('api.informat_sync'), {headers: {'x-api-key': api_key,}, method: 'POST', body: JSON.stringify({"sync-school": "csu"})});
                const status = await ret.json();
                bootbox.alert(status.data);
            }
        });
}

