import { formio_popup_create } from "../base/popup.js"
import { subscribe_right_click } from "../base/right_click.js";
import { ctx } from "../datatables/datatables.js"

const user_add = async () => {
    formio_popup_create(ctx.popups.user_password_form, async (action, opaque, data = null) => {
        if (action === 'submit') {
            const ret = await fetch(Flask.url_for('api.user_add'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(data),});
            const status = await ret.json();
            if (status.status) {
                bootbox.alert(`Gebruiker ${data.username} is toegevoegd`)
            } else {
                bootbox.alert(status.data)
            }
            ctx.reload_table();
        }
    }, {"new_password": true})
}

const user_update = async (item, ids) => {
    const ret = await fetch(Flask.url_for('api.user_get', {id: ids[0]}), {headers: {'x-api-key': ctx.api_key,}});
    const status = await ret.json();
    if (status.status) {
        formio_popup_create(ctx.popups.user_password_form, async (action, opaque, data = null) => {
            if (action === 'submit') {
                const ret = await fetch(Flask.url_for('api.user_update'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(data),});
                const status = await ret.json();
                if (status.status) {
                    bootbox.alert(`Gebruiker ${data.username} is aangepast`)
                } else {
                    bootbox.alert(status.data)
                }
                ctx.reload_table();
            }
        }, status.data)
    } else {
        bootbox.alert(status.data)
    }
}


const users_delete = async (item, ids) => {
    bootbox.confirm("Wilt u deze gebruiker(s) verwijderen?", async result => {
        if (result) {
                const ret = await fetch(Flask.url_for('api.user_delete'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(ids),});
                const status = await ret.json();
                if (status.status) {
                    bootbox.alert(`Gebruiker(s) is/zijn verwijderd.`)
                } else {
                    bootbox.alert(status.data)
                }
                ctx.reload_table();
        }
    });


}

subscribe_right_click('add', (item, ids) => user_add());
subscribe_right_click('edit', (item, ids) => user_update(item, ids));
subscribe_right_click('delete', (item, ids) => users_delete(item, ids));
