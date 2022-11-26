let formio
let extra = 'extra' in data ? data.extra : {};
let cancel_endpoint = 'cancel_endpoint' in data ? data.cancel_endpoint : "";
let formio_local_storage = {}
let backup_timer_id;

function button_pushed(action) {
    switch (action) {
        case 'save':
            formio.submit()
            break
        case 'cancel-ack':
            if ('cancel_endpoint' in data) {
                if (confirm('Opgelet, de inhoud van dit formulier gaat verloren.  Bent u zeker?')) {
                    clearInterval(backup_timer_id);
                    formio.resetValue();
                    localStorage.removeItem('formio-cache')
                    document.location.href = Flask.url_for(data['cancel_endpoint'])
                }
            }
            break
        case 'clear-ack':
            if (confirm('Opgelet, alle velden in dit formulier worden gewist.  Bent u zeker?')) {
                formio.resetValue();
            }
            break
        case 'cancel':
            if ('cancel_endpoint' in data) {
                clearInterval(backup_timer_id);
                formio.resetValue();
                localStorage.removeItem('formio-cache')
                document.location.href = Flask.url_for(data['cancel_endpoint'])
            }
            break
        case 'clear':
            formio.resetValue();
            break
    }
}

$(document).ready(async function () {
    const form_options = {sanitizeConfig: {addTags: ['iframe'], addAttr: ['allow'], ALLOWED_TAGS: ['iframe'], ALLOWED_ATTR: ['allow']},/* noAlerts: true,*/}
    //Render and display form
    formio = await Formio.createForm(document.getElementById('formio-form'), data.template, form_options)
    if ('defaults' in data) {
        Object.entries(data.defaults).forEach(([k, v]) => {
            try {
                formio.getComponent(k).setValue(v);
            } catch (error) {
                console.log("skipped ", k, v);
            }
        });
    }
    // update window title, if required
    if ('title' in data) {
        document.title = data.title;
    }
    // Clear cache when the page is loaded for the first time.  Do NOT clear when page is reloaded...
    if (performance.getEntriesByType('navigation')[0].type === 'navigate') {
        localStorage.removeItem('formio-cache')
    }
    // check if form data is present in the local browser
    formio_local_storage = JSON.parse(localStorage.getItem('formio-cache')) || {};
    if (formio_local_storage) {
        Object.entries(formio_local_storage).forEach(([k, v]) => {
            try {
                formio.getComponent(k).setValue(v);
            } catch (error) {
                console.log("skipped ", k, v);
            }
        });
    }
    //store the data in the local browser on regular intervals
    backup_timer_id = setInterval(() => {
        const data = formio.submission.data;
        localStorage.setItem('formio-cache', JSON.stringify(data));
    }, 5000);
    formio.on('submit', async submitted => {
        let extra = null;
        if ('post_data_endpoint' in data) {
            const api_key = data.api_key || '';
            const ret = await fetch(Flask.url_for(data.post_data_endpoint), {
                headers: {'x-api-key':  api_key,},
                method: 'POST',
                body: JSON.stringify(submitted.data),
            });
            const status = await ret.json();
            if (status.status) {
                extra = status.data;
            } else {
                alert(`Fout bij het opslaan:\n ${status.data}`)
                document.location.reload();
            }
        }
        //On submit, fetch a new form
        if ('form_on_submit' in data) {
            load_new_form(data.form_on_submit, extra);
        }
        //On submit, go to new page
        if ('submit_endpoint' in data) {
            document.location.href = Flask.url_for(data['submit_endpoint'])
        }
        //delete local storage
        clearInterval(backup_timer_id);
        formio.resetValue();
        localStorage.removeItem('formio-cache')
    });
    // On cancel (button) go to new page
    formio.on('cancel', () => {
        button_pushed('cancel')
    });
    formio.on('clear', () => {
        button_pushed('clear');
    });
});