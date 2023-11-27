import {socketio} from "./socketio.js";
import {add_to_popup_body, create_p_element, hide_popup, init_popup, show_popup, subscribe_btn_ok} from "./popup.js";

const navbar_element = document.querySelector("#navbar");
const logo_div = document.querySelector("#warning-logo");

export function flash_messages(list) {
    for (var i = 0; i < list.length; i++) {
        var message = list[i];
        bootbox.alert(message);
    }
}

export function busy_indication_on() {
    document.getElementsByClassName("busy-indicator")[0].style.display = "block";
}

export function busy_indication_off() {
    document.getElementsByClassName("busy-indicator")[0].style.display = "none";
}

const show_messsage = (type, data) => {
    logo_div.style.visibility = "visible";
    logo_div.querySelector("span").innerHTML = data.data;
}

const hide_messsage = () => {
    logo_div.style.visibility = "hidden";
}

socketio.subscribe_on_receive("warning-on", show_messsage);
socketio.subscribe_on_receive("warning-off", hide_messsage);


var menu = [
    ["student.show", "Studenten", 1],
    ["staff.show", "Personeel", 1],
    ["group.show", "Groepen", 1],
    ["logging.show", "Logging", 3],
    ["user.show", "Gebruikers", 5],
    ["settings.show", "Instellingen", 5],
]


var buttons = [
]

export const new_menu = new_menu => {
    menu = new_menu;
}

$(document).ready(async () => {
    let dd_ctr = 0;
    for (const item of menu) {
        if (current_user_level >= item[2]) {
            const li = document.createElement("li");
            if (Array.isArray(item[0])) {
                // dropdown menu-item
                li.classList.add("nav-item", "dropdown");
                const a = document.createElement("a");
                li.appendChild(a)
                a.classList.add("nav-link", "dropdown-toggle");
                a.style.color = "white";
                a.href = "#";
                a.id = `dd${dd_ctr}`
                a.setAttribute("role", "button");
                a.setAttribute("data-toggle", "dropdown");
                a.setAttribute("aria-haspopup", true);
                a.setAttribute("aria-expanded", true);
                a.innerHTML = item[1];
                const div = document.createElement("div");
                li.appendChild(div)
                div.classList.add("dropdown-menu");
                div.setAttribute("aria-labelledby", `dd${dd_ctr}`)
                for (const sitem of item[0]) {
                    if (sitem[0] === "divider") {
                        const divd = document.createElement("div");
                        divd.classList.add("dropdown-divider");
                        div.appendChild(divd)
                    } else {
                        if (current_user_level >= sitem[2]) {
                            const a = document.createElement("a");
                            div.appendChild(a)
                            a.classList.add("dropdown-item");
                            if (typeof sitem[0] === "function") {
                                a.onclick = sitem[0];
                            } else {
                                a.href = Flask.url_for(sitem[0]);
                            }
                            a.innerHTML = sitem[1]
                        }
                    }
                }
                dd_ctr++;
            } else if (item[0]==="divider") {
                // regular menu-item
                li.classList.add("nav-item");
                const a = document.createElement("a");
                a.classList.add("nav-link");
                a.style.color = "white";
                a.style.backgroundColor = "white";
                a.style.paddingLeft = 0;
                a.style.paddingRight = 0;
                a.href = "#";
                a.innerHTML = "i";
                li.appendChild(a);
            } else {
                // regular menu-item
                const url_path = Flask.url_for(item[0]);
                li.classList.add("nav-item");
                const a = document.createElement("a");
                a.classList.add("nav-link");
                if (window.location.href.includes(url_path)) {
                    a.classList.add("active");
                }
                a.href = url_path;
                a.innerHTML = item[1];
                li.appendChild(a);
            }
            navbar_element.appendChild(li);
        }
    }
    logo_div.style.visibility="hidden";
    logo_div.classList.add("tooltip");
    const logo = new Image(30);
    logo.classList.add("blink");
    logo.src = "/static/img/warning.png";
    logo_div.appendChild(logo);
    const tt_text = document.createElement("span");
    tt_text.classList.add("tooltiptext");
    logo_div.appendChild(tt_text);

    if (testmode) {
        const li = document.createElement("li");
        li.classList.add("nav-item");
        const a = document.createElement("a");
        a.classList.add("navbar-brand");
        a.href = "#";
        a.innerHTML = "TEST SITE"
        li.appendChild(a);
        navbar_element.appendChild(li);
    }

    //Check if there is an ongoing warning
    const ret = await fetch(Flask.url_for('api.get_warning'));
    const resp = await ret.json();
    if (resp.message !=="") {
        show_messsage(null, {data: resp.message});
    }

});
