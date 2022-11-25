subscribe_right_click('check-rfid', (item, ids) => check_rfid(ids, 'api.update_staff'));
subscribe_right_click('update-password', (item, ids) => update_password(ids, 'api.update_staff', popups['update-password']));
