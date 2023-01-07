from app import flask_app
from app.data import student as mstudent, photo as mphoto, settings as msettings, staff as mstaff
from app.data.utils import belgische_gemeenten
from app.application import warning as mwarning
import datetime
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


def student_from_wisa_to_database(local_file=None, max=0):
    try:
        log.info('start student import from wisa')
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
            query = msettings.get_configuration_setting('wisa-student-query')
            today = datetime.date.today()
            # it is not passible to get students from wisa when month is 7 or 8.  It is when month is 9
            if today.month >= 7 and today.month <= 8:
                if msettings.get_configuration_setting('wisa-student-use-previous-schoolyear'):
                    today = datetime.date(today.year, 6, 30)
                else:
                    today = datetime.date(today.year, 9, 1)
            werkdatum = str(today)
            url = f'{base_url}/{query}?werkdatum={werkdatum}&_username_={login}&_password_={password}&format=json'
            response = requests.get(url)
            response_text = response.text.encode("iso-8859-1").decode("utf-8")
        # The query returns with the keys in uppercase.  Convert to lowercase first
        keys = mstudent.get_columns()
        for key in keys:
            response_text = response_text.replace(f'"{key.upper()}"', f'"{key}"')
        data = json.loads(response_text)
        # (Photo.id, Photo.filename, Photo.new, Photo.changed, Photo.delete, func.octet_length(Photo.photo))
        saved_photos = {p[1]: p[0] for p in mphoto.get_photos_size()}
        db_students = {} # the current, active students in the database
        # default previous and current schoolyear
        _, current_schoolyear, prev_schoolyear = msettings.get_changed_schoolyear()
        if current_schoolyear == '':
            now = datetime.datetime.now()
            if now.month <= 8:
                current_schoolyear = f'{now.year-1}-{now.year}'
                prev_schoolyear = f'{now.year-2}-{now.year-1}'
            else:
                current_schoolyear = f'{now.year}-{now.year+1}'
                prev_schoolyear = f'{now.year-1}-{now.year}'
            msettings.set_changed_schoolyear(prev_schoolyear, current_schoolyear)
        students = mstudent.student_get_m()
        if students:
            db_students = {s.leerlingnummer: s for s in students}
            current_schoolyear = students[0].schooljaar
        new_list = []
        changed_list = []
        flag_list = []
        check_inschrijvingsdatum = {} #the import can contain a student twice, with different inschrijvingsdatum.  The most recent inschrijvingsdatum wins...
        nbr_deleted = 0
        nbr_processed = 0
        # clean up, remove leading and trailing spaces, convert datetime-string to datetime
        for i, item in enumerate(data):
            for k, v in item.items():
                if k == 'middag':  # this field may contain leading spaces
                    item[k] = v.replace(' ', '-')
                else:
                    item[k] = v.strip()
            item['inschrijvingsdatum'] = datetime.datetime.strptime(item['inschrijvingsdatum'].split(' ')[0], '%Y-%m-%d').date()
            item['geboortedatum'] = datetime.datetime.strptime(item['geboortedatum'].split(' ')[0], '%Y-%m-%d').date()
            if item["leerlingnummer"] in check_inschrijvingsdatum:
                log.error(f'{sys._getframe().f_code.co_name}: Import contains twice the same student {item["leerlingnummer"]}, {data[check_inschrijvingsdatum[item["leerlingnummer"]]]["inschrijvingsdatum"]}, {item["inschrijvingsdatum"]}')
                if data[check_inschrijvingsdatum[item["leerlingnummer"]]]["inschrijvingsdatum"] < item["inschrijvingsdatum"]:
                    data[check_inschrijvingsdatum[item["leerlingnummer"]]] = None
                    check_inschrijvingsdatum["leerlingnummer"] = i
                else:
                    data[i] = None
            else:
                check_inschrijvingsdatum[item["leerlingnummer"]] = i
        # massage the imported data so that it fits the database.
        # for each student in the import, check if it's new or changed
        for item in data:
            if not item: # skip empty items
                continue
            orig_geboorteplaats = None
            if "," in item['geboorteplaats'] or "-" in item['geboorteplaats'] and item['geboorteplaats'] not in belgische_gemeenten:
                if "," in item['geboorteplaats']:   # sometimes, geboorteplaats is mis-used to also include geboorteland.
                    gl = item['geboorteplaats'].split(",")
                else:
                    gl = item['geboorteplaats'].split("-")
                orig_geboorteplaats = item['geboorteplaats']
                item['geboorteplaats'] = gl[0].strip()
                item['geboorteland'] = gl[1].strip()
            try:
                item['foto'] = item['foto'].split('\\')[1]
            except:
                pass
            item['foto_id'] = -1
            if f"{item['leerlingnummer']}.jpg" in saved_photos:
                item['foto_id'] = saved_photos[f"{item['leerlingnummer']}.jpg"]
                item['foto'] = f"{item['leerlingnummer']}.jpg"
            if item['foto'] in saved_photos:
                item['foto_id'] = saved_photos[item['foto']]
            try:
                item['klasnummer'] = int(item['klasnummer'])
            except:
                item['klasnummer'] = 0
            try:
                item['schooljaar'] = item['schooljaar'].split(' ')[1]
            except:
                pass
            if "email" in item:
                del(item["email"])
            if item['leerlingnummer'] in db_students:
                # student already exists in database
                # check if a student has updated properties
                changed_properties = []
                student = db_students[item['leerlingnummer']]
                for k, v in item.items():
                    if hasattr(student, k) and v != getattr(student, k):
                        changed_properties.append(k)
                if changed_properties:
                    changed_properties.extend(['delete', 'new'])  # student already present, but has changed properties
                    item.update({'changed': changed_properties, 'student': student, 'delete': False, 'new': False})
                    changed_list.append(item)
                else:
                    flag_list.append({'changed': '', 'delete': False, 'new': False, 'student': student}) # student already present, no change
                del(db_students[item['leerlingnummer']])
            else:
                # student not present in database, i.e. a new student
                if orig_geboorteplaats:
                    mwarning.new_warning(f'Leerling met leerlingnummer {item["leerlingnummer"]} heeft mogelijk een verkeerde geboorteplaats/-land: {orig_geboorteplaats}')
                    log.info(f'Leerling met leerlingnummer {item["leerlingnummer"]} heeft mogelijk een verkeerde geboorteplaats/-land: {orig_geboorteplaats}')
                item['email'] = f"{item['voornaam'].translate(normalize_letters).lower()}.{item['naam'].translate(normalize_letters).lower()}@lln.campussintursula.be"
                item['username'] = f's{item["leerlingnummer"]}'
                new_list.append(item)  # new student
            nbr_processed += 1
            if max > 0 and nbr_processed >= max:
                break
        # at this point, saved_students contains the students not present in the wisa-import, i.e. the deleted students
        for k, v in db_students.items():
            if not v.delete:
                flag_list.append({'changed': '', 'delete': True, 'new': False, 'student': v})
                nbr_deleted += 1
        # add the new students to the database
        mstudent.student_add_m(new_list)
        # update the changed properties of the students
        mstudent.student_change_m(changed_list, overwrite=True) # previous changes are lost
        # deleted students and students that are not changed, set the flags correctly
        mstudent.student_flag_m(flag_list)
        # if required, update the current and previous schoolyear (normally at the beginning of a new schoolyear)
        if new_list:
            if new_list[0]['schooljaar'] != current_schoolyear:
                msettings.set_changed_schoolyear(current_schoolyear, new_list[0]['schooljaar'])
        if changed_list:
            if 'schooljaar' in changed_list[0]['changed']:
                msettings.set_changed_schoolyear(current_schoolyear, changed_list[0]['schooljaar'])
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
            if not v.delete:
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


def cron_task_wisa_get_student(opaque=None):
    with flask_app.app_context():
        wisa_files = msettings.get_list('test-wisa-json-list')
        if wisa_files:  # test with wisa files
            current_wisa_file = msettings.get_configuration_setting('test-wisa-current-json')
            if current_wisa_file == '' or current_wisa_file not in wisa_files:
                current_wisa_file = wisa_files[0]
            else:
                new_index = wisa_files.index(current_wisa_file) + 1
                if new_index >= len(wisa_files):
                    new_index = 0
                current_wisa_file = wisa_files[new_index]
            msettings.set_configuration_setting('test-wisa-current-json', current_wisa_file)
            student_from_wisa_to_database(local_file=current_wisa_file)
        else:
            # read_from_wisa_database(max=10)
            student_from_wisa_to_database()


def cront_task_wisa_get_staff(opaque=None):
    with flask_app.app_context():
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



