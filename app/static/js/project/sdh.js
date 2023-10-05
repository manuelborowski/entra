
export async function smartschool_print_info(ids, account, api_key) {
    let target = "coaccounts";
    switch (account) {
        case 0: target = "leerling"; break;
        case 1: target = "coaacount 1"; break;
        case 2: target = "coaacount 2"; break;
        default: target = "coaacounts"; break;
    }
    bootbox.confirm(`Smartschool info voor ${target} afdrukken?`,
        async result => {
            if (result) {
                const ret = await fetch(Flask.url_for('api.smartschool_print_info'), {
                    headers: {'x-api-key': api_key,},
                    method: 'POST', body: JSON.stringify({ids, account}),
                });
                const status = await ret.json();
                if (status.status) {
                    const info_file = status.data;
                    var link = document.createElement("a");
                    //Add a rendom parameter to make sure that not a cached version is returned (filename is always te same)
                    link.href = `${document.location.origin}/${info_file}?${new Date().getTime()}`;
                    link.click();
                    link.remove();
                } else {
                    bootbox.alert(status.data);
                }
            }
        });
}


export async function smartschool_mail_info(ids, account, api_key) {
    let target = "coaccounts";
    switch (account) {
        case 0: target = "leerling"; break;
        case 1: target = "coaacount 1"; break;
        case 2: target = "coaacount 2"; break;
        default: target = "coaacounts"; break;
    }
    bootbox.confirm(`Smartschool info naar ${target} sturen?`,
        async result => {
            if (result) {
                const ret = await fetch(Flask.url_for('api.smartschool_send_info'), {
                    headers: {'x-api-key': api_key,},
                    method: 'POST', body: JSON.stringify({ids, account}),
                });
                const status = await ret.json();
                bootbox.alert(status.data);
            }
        });
}

