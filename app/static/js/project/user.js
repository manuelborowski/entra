import { formio_popup_create } from "../base/popup.js"
import { subscribe_right_click } from "../base/right_click.js";

const user_add = async () => {
    formio_popup_create(popups.user_password_form, {"new_password": true}, async (action, opaque, data = null) => {
        if (action === 'submit') {
            const ret = await fetch(Flask.url_for('api.user_add'), {headers: {'x-api-key': api_key,}, method: 'POST', body: JSON.stringify(data),});
            const status = await ret.json();
            if (status.status) {
                bootbox.alert(`Gebruiker ${data.username} is toegevoegd`)
                reload_table();
            } else {
                bootbox.alert(status.data)
            }
        }
    })
}

const user_update = async (item, ids) => {
    const ret = await fetch(Flask.url_for('api.user_get', {id: ids[0]}), {headers: {'x-api-key': api_key,}});
    const status = await ret.json();
    if (status.status) {
        formio_popup_create(popups.user_password_form, status.data, async (action, opaque, data = null) => {
            if (action === 'submit') {
                const ret = await fetch(Flask.url_for('api.user_update'), {headers: {'x-api-key': api_key,}, method: 'POST', body: JSON.stringify(data),});
                const status = await ret.json();
                if (status.status) {
                    bootbox.alert(`Gebruiker ${data.username} is aangepast`)
                    reload_table();
                } else {
                    bootbox.alert(status.data)
                }
            }
        })
    } else {
        bootbox.alert(status.data)
    }
}


const users_delete = async (item, ids) => {
    bootbox.confirm("Wilt u deze gebruiker(s) verwijderen?", async result => {
        if (result) {
                const ret = await fetch(Flask.url_for('api.user_delete'), {headers: {'x-api-key': api_key,}, method: 'POST', body: JSON.stringify(ids),});
                const status = await ret.json();
                if (status.status) {
                    bootbox.alert(`Gebruiker(s) is/zijn verwijderd.`)
                    reload_table();
                } else {
                    bootbox.alert(status.data)
                }
        }
    });


}

subscribe_right_click('add', (item, ids) => user_add());
subscribe_right_click('edit', (item, ids) => user_update(item, ids));
subscribe_right_click('delete', (item, ids) => users_delete(item, ids));
