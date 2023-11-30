import {subscribe_right_click} from "../base/right_click.js";
import {ctx, get_data_of_row} from "../datatables/datatables.js"
import {formio_popup_create} from "../base/popup.js";


const new_cc_team_cb = async (action, opaque, data=null) => {
    if (action === 'submit') {
        const ret = await fetch(Flask.url_for('api.team_add'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(data),});
        const status = await ret.json();
        bootbox.alert(status.data);
        ctx.reload_table();
    }
}

async function new_cc_team(ids) {
    let person = get_data_of_row(ids[0]);
    formio_popup_create(ctx.popups['classroomcloud-group'], new_cc_team_cb)
}

subscribe_right_click('new-cc-team', (item, ids) => new_cc_team(ids));

