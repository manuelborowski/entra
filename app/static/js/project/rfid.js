import { get_data_of_row, update_cell } from "../datatables/datatables.js"

const badge_raw2hex = code => {
    const decode_caps_lock = code => {
        let out = '';
        const dd = {
            '&': '1', 'É': '2', '"': '3', '\'': '4', '(': '5', '§': '6', 'È': '7', '!': '8', 'Ç': '9',
            'À': '0', 'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F'
        };
        for (let r of code) {
            out += dd[r.toUpperCase()];
        }
        return out
    }

    const process_int_code = code_int => {
        if (code_int < 100000 || code_int > parseInt('FFFFFFFF', 16)) {
            return {is_rfid_code: false, code: code_int}
        }
        //convert the int to a hex number, add leading 0's (if required) to get 8 characters
        //revert the order of the 4 tupples (big to little endian)
        let hex = code_int.toString(16).toUpperCase();
        hex = '0'.repeat(8 - hex.length) + hex;
        hex = hex.split('');
        let out = []
        for (let i = 6; i >= 0; i -= 2) {
            out = out.concat(hex.slice(i, i + 2))
        }
        out = out.join('');
        return {is_rfid_code: true, code: out}
    }

    let is_rfid_code = true
    let is_valid_code = true
    code = code.toUpperCase();

    if (code.length === 8) {
        // Asume a hex code of 8 chars
        if (code.includes('Q')) {
            // the badgereader is a qwerty HID device
            code = code.replace(/Q/g, 'A');
        }
        if (!/^[0-9a-fA-F]+$/.test(code)) {
            // it is not a valid hex code :-(  Check if capslock was on
            code = decode_caps_lock(code);
            if (!/^[0-9a-fA-F]+$/.test(code)) {
                // it is not a valid code :-(
                is_valid_code = is_rfid_code = false;
            }
        }
    } else {
        // Assume it is an integer code, so test it
        if (/^[0-9]+$/.test(code)) {
            const res = process_int_code(parseInt(code));
            is_rfid_code = res.is_rfid_code;
            code = res.code;
        } else {
            code = decode_caps_lock(code);
            if (/^[0-9]+$/.test(code)) {
                const res = process_int_code(parseInt(code));
                is_rfid_code = res.is_rfid_code;
                code = res.code;
            } else {
                is_valid_code = is_rfid_code = false;
            }
        }
    }
    return {valid: is_rfid_code, code}
}

async function rfid_to_server(id, rfid, update_endpoint) {
    const ret = await fetch(Flask.url_for(update_endpoint), {headers: {'x-api-key': api_key,}, method: 'POST', body: JSON.stringify({id, rfid}),});
    const status = await ret.json();
    if (status.status) {
        update_cell(id, 'rfid', rfid);
    } else {
        bootbox.alert(`Kan de RFID code niet aanpassen: ${status.data}`)
    }
}

export async function check_rfid(ids, update_endpoint) {
    let person = get_data_of_row(ids[0]);
    bootbox.prompt({
        title: `Scan de badge van ${person.voornaam} ${person.naam} <br> Of laat leeg om te wissen`,
        callback: result => {
            if (result === '') {
                rfid_to_server(person.id, '', update_endpoint)
            } else if (result) {
                let res = badge_raw2hex(result);
                if (res.valid) {
                    bootbox.dialog({
                        title: 'Nieuwe RFID code?',
                        message: `De gescande code is ${res.code}<br> De huidige code is ${person.rfid}`,
                        // callback: result => {console.log(result)},
                        buttons: {
                            ok: {
                                label: 'Gebruik nieuwe code',
                                className: 'btn-success',
                                callback: () => { rfid_to_server(person.id, res.code, update_endpoint) }
                            },
                            cancel: {
                                label: 'Annuleren',
                                className: 'btn-warning',
                                callback: function () {

                                }
                            },
                        }
                    })
                } else {
                   bootbox.alert("Geen geldige RFID code");
                }
            }
        }
    })
}

