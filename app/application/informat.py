from app import flask_app
from app.data import student as mstudent, photo as mphoto, settings as msettings, staff as mstaff, utils as mutils
from app.data.utils import belgische_gemeenten
from app.application import warning as mwarning
import datetime, xmltodict
import json, requests, sys

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


#used to translate diacretic letters into regular letters (username, emailaddress)
normalMap = {'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A','à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'ª': 'A',
             'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E', 'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
             'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I','í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
             'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O', 'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'º': 'O', '°': 'O',
             'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U','ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
             'Ñ': 'N', 'ñ': 'n',
             'Ç': 'C', 'ç': 'c',
             '§': 'S', '³': '3', '²': '2', '¹': '1', ' ': '', '\'': ''}
normalize_letters = str.maketrans(normalMap)


informat2sdh_student_keys = {
    "Voornaam": "voornaam",
    "Naam": "naam",
    "rijksregnr": "rijksregisternummer",
	"Stamnr_kort": "stamboeknummer",
	"p_persoon": "leerlingnummer",
	"Fietsnummer": "middag",
	"instelnr": "instellingsnummer",
	"school": "schoolnaam",
	"Klascode": "klascode",
	"afdelingsjaar": "klasgroep",
	"nr_admgr": "adminstratievecode",
	"Klasnr": "klasnummer",
    "nr": "huisnummer",
    "bus": "busnummer",
    "hfdpostnr": "postnummer",
    "hfdgem": "gemeente",
}

sdh_allowed_student_keys = [
    "voornaam",
    "naam",
    "roepnaam",
    "rijksregisternummer",
    "stamboeknummer",
    "leerlingnummer",
    "middag",
    "vsknummer",
    "rfid",
    "foto",
    "foto_id",
    "geboortedatum",
    "schooljaar",
    "instellingsnummer",
    "schoolnaam",
    "klascode",
    "klasgroep",
    "adminstratievecode",
    "klasnummer",
    "computer",
    "username",
    "straat",
    "huisnummer",
    "busnummer",
    "postnummer",
    "gemeente",
]


def get_from_url(url, item_name, replace_keys={}):
    try:
        out = []
        params = {"login": flask_app.config["INFORMAT_USERNAME"], "paswoord": flask_app.config["INFORMAT_PASSWORD"], "hoofdstructuur": ""}
        now = datetime.datetime.now()
        referentiedatum = now.strftime("%d-%m-%Y")
        reference_year = now.year - 1 if now.month < 8 else now.year
        schooljaar = f"{reference_year}-{reference_year-2000+1}"
        params["schooljaar"] = schooljaar
        params["referentiedatum"] = referentiedatum
        instellingen = ["30569", "30593"]
        for instelling in instellingen:
            params["instelnr"] = instelling
            xml_data = requests.get(url=url, params=params).content
            if replace_keys:
                for k,v in replace_keys.items():
                    xml_data = xml_data.replace(bytes(k, "utf-8"), bytes(v, "utf-8"))
            data = xmltodict.parse(xml_data)[f"ArrayOf{item_name[0].upper() + item_name[1::]}"][item_name]
            if not isinstance(data, list):
                data = [data]
            out += data
        return out
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return []



def student_from_informat_to_database(local_file=None, max=0):
    try:
        log.info('start student import from informat')
        if local_file:
            log.error(f'Reading from local file NOT IMPLEMENTED')
            return
            log.info(f'Reading from local file {local_file}')
        else:
            # prevent accidental import from informat
            # log.error("NO IMPORT FROM informat ALLOWED")
            # return

            informat_students = get_from_url(flask_app.config["INFORMAT_URL_LLN"], "wsInschrijving", informat2sdh_student_keys)
            informat_lln_extra = get_from_url(flask_app.config["INFORMAT_URL_LLN_EXTRA"], "wsLeerling", informat2sdh_student_keys)
            informat_lln_extra_cache = {l["pointer"]: l for l in informat_lln_extra}
            for l in informat_students:
                if l["leerlingnummer"] in informat_lln_extra_cache:
                    l.update(informat_lln_extra_cache[l["leerlingnummer"]])
        schooljaar = mutils.get_current_schoolyear()
        # (Photo.id, Photo.filename, Photo.new, Photo.changed, Photo.delete, func.octet_length(Photo.photo))
        saved_photos = {p[1]: p[0] for p in mphoto.photo_get_size_all()}
        db_students = {} # the current, active students in the database
        students = mstudent.student_get_m()
        if students:
            db_students = {s.leerlingnummer: s for s in students}
        new_list = []
        changed_list = []
        flag_list = []
        processed_list = [] # to detect double entries in the informat-import
        nbr_deleted = 0
        nbr_processed = 0
        # clean up, remove leading and trailing spaces, convert datetime-string to datetime
        for informat_student in informat_students:
            if informat_student["leerlingnummer"] in processed_list:
                log.error(f"Student already imported {informat_student['leerlingnummer']}, {informat_student['naam']} {informat_student['voornaam']}")
                continue
            informat_student["geboortedatum"] = datetime.datetime.strptime(informat_student["geboortedatum"], "%Y-%m-%d").date()
            informat_student["klasnummer"] = int(informat_student["klasnummer"])
            informat_student["schooljaar"] = schooljaar

            if f"{informat_student['leerlingnummer']}.jpg" in saved_photos:
                informat_student['foto_id'] = saved_photos[f"{informat_student['leerlingnummer']}.jpg"]
                informat_student['foto'] = f"{informat_student['leerlingnummer']}.jpg"

            # clean up some fields
            for k,v in informat_student.items():
                if k == "middag":
                    if not v:
                        v = ""
                    v = v.replace(" ", "-")
                    informat_student[k] = v
                if k == "roepnaam" and not v:
                    continue
                if k == "rijksregisternummer" and not v:
                    informat_student[k] = ""
                if k == "busnummer" and not v:
                    informat_student[k] = ""

            if informat_student['leerlingnummer'] in db_students:
                # student already exists in database
                # check if a student has updated properties
                changed_properties = []
                db_student = db_students[informat_student['leerlingnummer']]
                for k, v in informat_student.items():
                    if k in sdh_allowed_student_keys and hasattr(db_student, k) and v != getattr(db_student, k):
                        changed_properties.append(k)
                if changed_properties:
                    changed_properties.extend(['delete', 'new'])  # student already present, but has changed properties
                    informat_student.update({'changed': changed_properties, 'student': db_student, 'delete': False, 'new': False})
                    changed_list.append(informat_student)
                    log.info(f'{sys._getframe().f_code.co_name}: updated, {db_student.leerlingnummer}, {db_student.naam} {db_student.voornaam}, {changed_properties}')
                else:
                    flag_list.append({'changed': '', 'delete': False, 'new': False, 'student': db_student}) # student already present, no change
                del(db_students[informat_student['leerlingnummer']])
            else:
                # student not present in database, i.e. a new student
                informat_student['email'] = f"{informat_student['voornaam'].translate(normalize_letters).lower()}.{informat_student['naam'].translate(normalize_letters).lower()}@lln.campussintursula.be"
                informat_student['username'] = f's{informat_student["leerlingnummer"]}'
                new_list.append(informat_student)  # new student
                log.info(f'{sys._getframe().f_code.co_name}: new, {informat_student["leerlingnummer"]}, {informat_student["naam"]} {informat_student["voornaam"]}, {informat_student["username"]}, {informat_student["email"]}')
            processed_list.append(informat_student["leerlingnummer"])
            nbr_processed += 1
            if max > 0 and nbr_processed >= max:
                break
        # at this point, saved_students contains the students not present in the informat-import, i.e. the deleted students
        for k, v in db_students.items():
            if not v.delete:
                flag_list.append({'changed': '', 'delete': True, 'new': False, 'student': v})
                log.info(f'{sys._getframe().f_code.co_name}: delete, {v.leerlingnummer}, {v.naam} {v.voornaam}')
                nbr_deleted += 1
        # add the new students to the database
        mstudent.student_add_m(new_list)
        # update the changed properties of the students
        mstudent.student_change_m(changed_list, overwrite=True) # previous changes are lost
        # deleted students and students that are not changed, set the flags correctly
        mstudent.student_flag_m(flag_list)
        log.info(f'{sys._getframe().f_code.co_name}, processed {nbr_processed}, new {len(new_list)}, updated {len(changed_list)}, deleted {nbr_deleted}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def staff_from_wisa_to_database(local_file=None, max=0):
    try:
        log.info('start staff import from wisa')
        if local_file:
            log.info(f'Reading from local file {local_file}')
            response_text = open(local_file).read()
        else:
            # prevent accidental import from WISA
            # log.error("NO IMPORT FROM WISA ALLOWED")
            # return
            login = msettings.get_configuration_setting('wisa-login')
            password = msettings.get_configuration_setting('wisa-password')
            base_url = msettings.get_configuration_setting('wisa-url')
            query = msettings.get_configuration_setting('wisa-staff-query')
            werkdatum = str(datetime.date.today())
            url = f'{base_url}/{query}?werkdatum={werkdatum}&_username_={login}&_password_={password}&format=json'
            response = requests.get(url)
            response_text = response.text.encode("iso-8859-1").decode("utf-8")
        # The query returns with the keys in uppercase.  Convert to lowercase first
        keys = mstaff.get_columns()
        for key in keys:
            response_text = response_text.replace(f'"{key.upper()}"', f'"{key}"')
        wisa_data = json.loads(response_text)
        staff = mstaff.staff_get_m()
        staff_in_db = {s.code: s for s in staff}
        new_list = []
        changed_list = []
        flag_list = []
        already_processed = []
        nbr_deleted = 0
        nbr_processed = 0
        # clean up, remove leading and trailing spaces
        for wisa_item in wisa_data:
            for k, v in wisa_item.items():
                wisa_item[k] = v.strip()
        # massage the imported data so that it fits the database.
        # for each staff-member in the import, check if it's new or changed
        for wisa_item in wisa_data:
            #skip double items
            if wisa_item['code'] in already_processed:
                continue
            wisa_item['geboortedatum'] = datetime.datetime.strptime(wisa_item['geboortedatum'].split(' ')[0], '%Y-%m-%d').date()
            email = wisa_item['email'] if 'campussintursula.be' in wisa_item['email'] else wisa_item['prive_email'] if 'campussintursula.be' in wisa_item['prive_email'] else ""
            if 'campussintursula.be' not in wisa_item['email'] and wisa_item["email"] != "":
                prive_email = wisa_item['email']
            elif 'campussintursula.be' not in wisa_item['prive_email'] and wisa_item["prive_email"] != "":
                prive_email = wisa_item['prive_email']
            else:
                prive_email = ''
            if email != "":
                wisa_item['email'] = email
            else:
                wisa_item['email'] = f"{wisa_item['voornaam'].translate(normalize_letters).lower()}.{wisa_item['naam'].translate(normalize_letters).lower()}@campussintursula.be"
            wisa_item["prive_email"] = prive_email
            if wisa_item['code'] in staff_in_db:
                # staff-member already exists in database, check if a staff-member has updated properties
                changed_properties = []
                staff = staff_in_db[wisa_item['code']]
                for k, v in wisa_item.items():
                    if hasattr(staff, k) and v != getattr(staff, k):
                        changed_properties.append(k)
                # if the naam or voornaam changes AND the email is already set in the database THEN ignore the new email (will cause confusion)
                if "email" in changed_properties and staff.email != "":
                    changed_properties.remove("email")
                if changed_properties:
                    changed_properties.extend(['delete', 'new'])  # staff-member already present, but has changed properties
                    wisa_item.update({'changed': changed_properties, 'staff': staff, 'delete': False, 'new': False})
                    changed_list.append(wisa_item)
                else:
                    flag_list.append({'changed': '', 'delete': False, 'new': False, 'staff': staff}) # staff already present, no change
                del(staff_in_db[wisa_item['code']])
            else:
                # staff-member not present in database, i.e. a new staff-member
                new_list.append(wisa_item)  # new staff-mmeber
            already_processed.append(wisa_item['code'])
            nbr_processed += 1
            if max > 0 and nbr_processed >= max:
                break
        # at this point, saved_staff contains the staff-memner not present in the wisa-import, i.e. the deleted staff-members
        for k, v in staff_in_db.items():
            if not v.delete and v.stamboeknummer != "":
                log.info(f"Delete staff {v.code}")
                flag_list.append({'changed': '', 'delete': True, 'new': False, 'staff': v})
                nbr_deleted += 1
        # add the new staff-members to the database
        mstaff.staff_add_m(new_list)
        # update the changed properties of the staff-members
        mstaff.staff_update_m(changed_list, overwrite=True) # previous changes are lost
        # deleted staff-members and staff-members that are not changed, set the flags correctly
        mstaff.staff_flag_m(flag_list)
        log.info(f'{sys._getframe().f_code.co_name}, processed {nbr_processed}, new {len(new_list)}, updated {len(changed_list)}, deleted {nbr_deleted}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}, {e}')


def cron_task_informat_get_student(opaque=None):
    informat_files = msettings.get_list('test-informat-xml-list')
    if informat_files:  # test with informat files
        current_informat_file = msettings.get_configuration_setting('test-informat-current-xml')
        if current_informat_file == '' or current_informat_file not in informat_files:
            current_informat_file = informat_files[0]
        else:
            new_index = informat_files.index(current_informat_file) + 1
            if new_index >= len(informat_files):
                new_index = 0
            current_informat_file = informat_files[new_index]
        msettings.set_configuration_setting('test-informat-current-xml', current_informat_file)
        student_from_informat_to_database(local_file=current_informat_file)
    else:
        # read_from_wisa_database(max=10)
        student_from_informat_to_database()


def cron_task_informat_get_staff(opaque=None):
    wisa_files = msettings.get_list('test-staff-wisa-json-list')
    if wisa_files:  # test with wisa files
        current_wisa_file = msettings.get_configuration_setting('test-staff-wisa-current-json')
        if current_wisa_file == '' or current_wisa_file not in wisa_files:
            current_wisa_file = wisa_files[0]
        else:
            new_index = wisa_files.index(current_wisa_file) + 1
            if new_index >= len(wisa_files):
                new_index = 0
            current_wisa_file = wisa_files[new_index]
        msettings.set_configuration_setting('test-staff-wisa-current-json', current_wisa_file)
        staff_from_wisa_to_database(local_file=current_wisa_file)
    else:
        staff_from_wisa_to_database()



