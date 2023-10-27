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


var menu = [
    ["student.show", "Studenten", 1],
    ["staff.show", "Personeel", 1],
    ["cardpresso.show", "Cardpresso", 3],
    ["logging.show", "Logging", 3],
    ["user.show", "Gebruikers", 5],
    ["settings.show", "Instellingen", 5],
]

var buttons = [

]

export const inject_menu = new_menu => {
    menu = new_menu;
}

$(document).ready(() => {
    const navbar_element = document.querySelector("#navbar");
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
});

