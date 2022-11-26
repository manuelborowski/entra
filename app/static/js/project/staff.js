import { subscribe_right_click } from "../base/right_click.js";
import { check_rfid } from "./rfid.js";
import { update_password } from "./password.js";

subscribe_right_click('check-rfid', (item, ids) => check_rfid(ids, 'api.update_staff'));
subscribe_right_click('update-password', (item, ids) => update_password(ids, 'api.update_staff', popups['update-password']));
