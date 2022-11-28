from app import log, flask_app
from app.data import student as mstudent, photo as mphoto, settings as msettings, staff as mstaff
from app.data.utils import belgische_gemeenten
from app.application import warning as mwarning
import datetime
import json, requests, sys

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


def get_students_from_wisa_database(local_file=None, max=0):
    try:
        log.info('start student import from wisa')
        if local_file:
            log.info(f'Reading from local file {local_file}')
            response_text = open(local_file).read()
        else:
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
        saved_students = {} # the current, active students in the database
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
        students = mstudent.get_students()
        if students:
            saved_students = {s.leerlingnummer: s for s in students}
            current_schoolyear = students[0].schooljaar
        new_list = []
        changed_list = []
        flag_list = []
        nbr_deleted = 0
        nbr_processed = 0
        # clean up, remove leading and trailing spaces
        for item in data:
            for k, v in item.items():
                if k == 'middag':  # this field may contain leading spaces
                    item[k] = v.replace(' ', '-')
                else:
                    item[k] = v.strip()
        # massage the imported data so that it fits the database.
        # for each student in the import, check if it's new or changed
        for item in data:
            orig_geboorteplaats = None
            if "," in item['geboorteplaats'] or "-" in item['geboorteplaats'] and item['geboorteplaats'] not in belgische_gemeenten:
                if "," in item['geboorteplaats']:   # sometimes, geboorteplaats is mis-used to also include geboorteland.
                    gl = item['geboorteplaats'].split(",")
                else:
                    gl = item['geboorteplaats'].split("-")
                orig_geboorteplaats = item['geboorteplaats']
                item['geboorteplaats'] = gl[0].strip()
                item['geboorteland'] = gl[1].strip()
            item['inschrijvingsdatum'] = datetime.datetime.strptime(item['inschrijvingsdatum'].split(' ')[0], '%Y-%m-%d').date()
            item['geboortedatum'] = datetime.datetime.strptime(item['geboortedatum'].split(' ')[0], '%Y-%m-%d').date()
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
            if item['leerlingnummer'] in saved_students:
                # student already exists in database
                # check if a student has updated properties
                changed_properties = []
                student = saved_students[item['leerlingnummer']]
                for k, v in item.items():
                    if v != getattr(student, k):
                        changed_properties.append(k)
                if changed_properties:
                    changed_properties.extend(['delete', 'new'])  # student already present, but has changed properties
                    item.update({'changed': changed_properties, 'student': student, 'delete': False, 'new': False})
                    changed_list.append(item)
                else:
                    flag_list.append({'changed': '', 'delete': False, 'new': False, 'student': student}) # student already present, no change
                del(saved_students[item['leerlingnummer']])
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
        for k, v in saved_students.items():
            if not v.delete:
                flag_list.append({'changed': '', 'delete': True, 'new': False, 'student': v})
                nbr_deleted += 1
        # add the new students to the database
        mstudent.add_students(new_list)
        # update the changed properties of the students
        mstudent.change_students(changed_list, overwrite=True) # previous changes are lost
        # deleted students and students that are not changed, set the flags correctly
        mstudent.flag_students(flag_list)
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


def wisa_get_student_cron_task(opaque=None):
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
            get_students_from_wisa_database(local_file=current_wisa_file)
        else:
            # read_from_wisa_database(max=10)
            get_students_from_wisa_database()


def get_staff_from_wisa_database(local_file=None, max=0):
    try:
        log.info('start staff import from wisa')
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
        saved_staff = {} # the staff in the database
        staff = mstaff.get_staffs()
        if staff:
            saved_staff = {s.rijksregisternummer: s for s in staff}
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
            if wisa_item['rijksregisternummer'] in already_processed:
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

            if wisa_item['rijksregisternummer'] in saved_staff:
                # staff-member already exists in database
                # check if a staff-member has updated properties
                changed_properties = []
                staff = saved_staff[wisa_item['rijksregisternummer']]
                for k, v in wisa_item.items():
                    if v != getattr(staff, k):
                        changed_properties.append(k)
                if changed_properties:
                    changed_properties.extend(['delete', 'new'])  # staff-member already present, but has changed properties
                    wisa_item.update({'changed': changed_properties, 'staff': staff, 'delete': False, 'new': False})
                    changed_list.append(wisa_item)
                else:
                    flag_list.append({'changed': '', 'delete': False, 'new': False, 'staff': staff}) # staff-mmeber already present, no change
                del(saved_staff[wisa_item['rijksregisternummer']])
            else:
                # staff-member not present in database, i.e. a new staff-member
                new_list.append(wisa_item)  # new staff-mmeber
            already_processed.append(wisa_item['rijksregisternummer'])
            nbr_processed += 1
            if max > 0 and nbr_processed >= max:
                break
        # at this point, saved_staff contains the staff-memner not present in the wisa-import, i.e. the deleted staff-members
        for k, v in saved_staff.items():
            if not v.delete:
                flag_list.append({'changed': '', 'delete': True, 'new': False, 'staff': v})
                nbr_deleted += 1
        # add the new staff-members to the database
        mstaff.add_staffs(new_list)
        # update the changed properties of the staff-members
        mstaff.update_staffs(changed_list, overwrite=True) # previous changes are lost
        # deleted staff-members and staff-members that are not changed, set the flags correctly
        mstaff.flag_staffs(flag_list)
        log.info(f'{sys._getframe().f_code.co_name}, processed {nbr_processed}, new {len(new_list)}, updated {len(changed_list)}, deleted {nbr_deleted}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}, {e}')


def wisa_get_staff_cron_task(opaque=None):
    with flask_app.app_context():
        get_staff_from_wisa_database()


