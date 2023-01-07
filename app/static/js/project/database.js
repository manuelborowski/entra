import { formio_popup_create, formio_popup_subscribe_event, formio_popup_set_value } from "../base/popup.js"
import { ctx } from "../datatables/datatables.js"
import { busy_indication_off, busy_indication_on} from "../base/base.js";


async function server_database_integrity_check(endpoint, event, databases) {
    busy_indication_on();
    const ret = await fetch(Flask.url_for(endpoint), {
        headers: {'x-api-key': ctx.api_key,},
        method: 'POST',
        body: JSON.stringify({event, databases}),
    });
    const status = await ret.json();
    busy_indication_off();
    formio_popup_set_value('log-check-integrity', status.data);
}


const database_popup_callback = (action, opaque, data=null) => {
    if (action === 'event-start-integrity-check') {
        var databases = []
        if (data['check-ad']) databases.push('ad');
        server_database_integrity_check(opaque, 'event-start-integrity-check', databases)
    }
    if (action === 'event-update-database') {
        var databases = []
        if (data['check-ad']) databases.push('ad');
        server_database_integrity_check(opaque, 'event-update-database', databases)
    }
}


export async function database_integrity_check(endpoint, popup) {
    await formio_popup_create(popup, database_popup_callback, {}, endpoint, '1500px');
    await formio_popup_subscribe_event('event-start-integrity-check', database_popup_callback, endpoint);
    await formio_popup_subscribe_event('event-update-database', database_popup_callback, endpoint);

}

