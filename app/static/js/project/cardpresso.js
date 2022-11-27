import { subscribe_right_click } from "../base/right_click.js";
import { ctx } from "../datatables/datatables.js"


const student_delete = async (item, ids) => {
    bootbox.confirm("Wilt u deze student(en) verwijderen?", async result => {
        if (result) {
                const ret = await fetch(Flask.url_for('api.carpresso_delete'), {headers: {'x-api-key': ctx.api_key,}, method: 'POST', body: JSON.stringify(ids),});
                const status = await ret.json();
                if (status.status) {
                    bootbox.alert(`Student(en) is/zijn verwijderd.`)
                    ctx.reload_table();
                } else {
                    bootbox.alert(status.data)
                }
        }
    });
}

subscribe_right_click('delete', (item, ids) => student_delete(item, ids));
