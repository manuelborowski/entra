import { subscribe_right_click } from "../base/right_click.js";
import { check_rfid } from "./rfid.js";
import { update_password } from "./password.js";
import { ctx } from "../datatables/datatables.js"
import {formio_popup_create} from "../base/popup.js";
import { busy_indication_off, busy_indication_on} from "../base/base.js";

subscribe_right_click('check-rfid', (item, ids) => check_rfid(ids, 'api.staff_update'));
subscribe_right_click('update-password', (item, ids) => update_password(ids, 'api.staff_update', ctx.popups['update-password']));


const staff_add = async () => {
    formio_popup_create(ctx.popups.new_update_staff, async (action, opaque, data = null) => {
        if (action === 'submit') {
            busy_indication_on();
            const ret = await fetch(Flask.url_for('api.staff_add'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(data),});
            const status = await ret.json();
            bootbox.alert(status.data)
            ctx.reload_table();
            busy_indication_off();
        }
    })
}

const staff_update = async (item, ids) => {
    const ret = await fetch(Flask.url_for('api.staff_get', {filters: `id=${ids[0]}`}), {headers: {'x-api-key': ctx.api_key,}});
    const status = await ret.json();
    if (status.status) {
        formio_popup_create(ctx.popups.new_update_staff, async (action, opaque, data = null) => {
            if (action === 'submit') {
                busy_indication_on();
                const ret = await fetch(Flask.url_for('api.staff_update'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(data),});
                const status = await ret.json();
                bootbox.alert(status.data)
                ctx.reload_table();
                busy_indication_off();
            }
        }, status.data[0])
    } else {
        bootbox.alert(status.data)
    }
}


const staff_delete_m = async (item, ids) => {
    bootbox.confirm("Wilt u dit personeelslid/deze personeelsleden verwijderen?<br>Opgelet, het is niet mogelijk om WISA-personeelsleden te verwijderen.", async result => {
        if (result) {
            busy_indication_on();
            const ret = await fetch(Flask.url_for('api.staff_delete'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(ids),});
            const status = await ret.json();
            bootbox.alert(status.data)
            ctx.reload_table();
            busy_indication_off();
        }
    });


}

subscribe_right_click('add', (item, ids) => staff_add());
subscribe_right_click('edit', (item, ids) => staff_update(item, ids));
subscribe_right_click('delete', (item, ids) => staff_delete_m(item, ids));
