import { get_data_of_row } from "../datatables/datatables.js"
import { formio_popup_create } from "../base/popup.js"
import { ctx } from "../datatables/datatables.js"


async function password_to_server(id, password_data, update_endpoint) {
    const ret = await fetch(Flask.url_for(update_endpoint), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify({id, password_data}),});
    const status = await ret.json();
    if (status.status) {
        bootbox.alert(`Paswoord is aangepast`)
    } else {
        bootbox.alert(`Kan paswoord niet niet aanpassen: ${status.data}`)
    }
}


const password_popup_callback = (action, opaque, data=null) => {
    if (action === 'submit') {
        const pwd_data = {
            password: data['new-password'],
            must_update: data['user-must-update-password']
        }
        password_to_server(opaque.person.id, pwd_data, opaque.update_endpoint);
    }
}


export async function update_password(ids, update_endpoint, popup) {
    let person = get_data_of_row(ids[0]);
    formio_popup_create(popup, password_popup_callback, {'new-password-user-name': `${person.voornaam} ${person.naam}`}, {person, update_endpoint})
}

