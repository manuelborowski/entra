import { inject_menu} from "../base/base.js";
import { smartschool_print_info, smartschool_mail_info} from "./sdh.js";

const smartschool_print_account_info = (account) => {
    const id_match = window.location.href.match(/\[(.*?)\]/);
    if (id_match) {
        const id = id_match[1];
        smartschool_print_info([id], account, api_key);
    }
}

const smartschool_mail_account_info = (account) => {
    const id_match = window.location.href.match(/\[(.*?)\]/);
    if (id_match) {
        const id = id_match[1];
        smartschool_mail_info([id], account, api_key);
    }
}

var menu = [
    [[
        [() => smartschool_mail_account_info(0), "Mail leerling info", 3],
        [() => smartschool_mail_account_info(1), "Mail coaccount 1", 3],
        [() => smartschool_mail_account_info(2), "Mail coaccount 2", 3],
        [() => smartschool_mail_account_info(3), "Mail beide coaccounts", 3],
        ["divider"],
        [() => smartschool_print_account_info(0), "Print leerling info", 3],
        [() => smartschool_print_account_info(1), "Print coaccount 1", 3],
        [() => smartschool_print_account_info(2), "Print coaccount 2", 3],
        [() => smartschool_print_account_info(3), "Print beide coaccounts", 3],
    ], "Smartschool", 3],
]

inject_menu(menu)

