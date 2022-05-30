from app import log, flask_app
from app.data import student as mstudent, photo as mphoto
from app.data.utils import belgische_gemeenten
from app.application import settings as msettings, warning as mwarning
import datetime
import json, re, requests, os, glob, shutil, sys


def read_from_wisa_database(local_file=None):
    try:
        log.info('start import from wisa')
        if local_file:
            response_text = open(local_file).read()
        else:
            login = msettings.get_configuration_setting('wisa-login')
            password = msettings.get_configuration_setting('wisa-password')
            url = msettings.get_configuration_setting('wisa-url')
            werkdatum = str(datetime.date.today())
            url = f'{url}&werkdatum={werkdatum}&&_username_={login}&_password_={password}'
            response_text = requests.get(url).text
        # The query returns with the keys in uppercase.  Convert to lowercase first
        keys = mstudent.get_columns()
        for key in keys:
            response_text = response_text.replace(f'"{key.upper()}"', f'"{key}"')
        data = json.loads(response_text)
        saved_schoolyear = msettings.get_configuration_setting('wisa-schoolyear')
        saved_students = {}
        if saved_schoolyear == '':
            wisa_schoolyear = data[0]['schooljaar']
            msettings.set_configuration_setting('wisa-schoolyear', wisa_schoolyear)
        else:
            students = mstudent.get_students({'schooljaar': saved_schoolyear})
            if students:
                saved_students = {s.rijksregisternummer: s for s in students}
        new_list = []
        update_list = []
        flag_list = []
        nbr_deleted = 0
        nbr_processed = 0
        for item in data:  #clean up
            for k, v in item.items():
                item[k] = v.strip()
        for item in data:
            orig_geboorteplaats = None
            if "," in item['geboorteplaats'] or "-" in item['geboorteplaats'] and item['geboorteplaats'] not in belgische_gemeenten:
                if "," in item['geboorteplaats']:
                    gl = item['geboorteplaats'].split(",")
                else:
                    gl = item['geboorteplaats'].split("-")
                orig_geboorteplaats = item['geboorteplaats']
                item['geboorteplaats'] = gl[0].strip()
                item['geboorteland'] = gl[1].strip()
            item['inschrijvingsdatum'] = datetime.datetime.strptime(item['inschrijvingsdatum'].split(' ')[0], '%Y-%m-%d').date()
            item['geboortedatum'] = datetime.datetime.strptime(item['geboortedatum'].split(' ')[0], '%Y-%m-%d').date()
            try:
                item['klasnummer'] = int(item['klasnummer'])
            except:
                item['klasnummer'] = 0
            if item['rijksregisternummer'] in saved_students:
                update_properties = []
                student = saved_students[item['rijksregisternummer']]
                for k, v in item.items():
                    if v != getattr(student, k):
                        update_properties.append(k)
                item['student'] = student
                item['delete'] = False
                item['new'] = False
                if update_properties:
                    item['update'] = update_properties # student already present, did change
                    update_list.append(item)
                else:
                    item['update'] = None      # student already present, did not change
                    flag_list.append(item)
                del(saved_students[item['rijksregisternummer']])
            else:
                if orig_geboorteplaats:
                    mwarning.new_warning(f'Leerling met code {item["code"]} heeft mogelijk een verkeerde geboorteplaats/-land: {orig_geboorteplaats}')
                    log.info(f'Leerling met code {item["code"]} heeft mogelijk een verkeerde geboorteplaats/-land: {orig_geboorteplaats}')
                new_list.append(item)  # new student
            nbr_processed += 1
        for k, v in saved_students.items(): # student not present in wisa anymore
            if not v.delete:
                flag_list.append({'update': None, 'delete': True, 'new': False, 'student': v})
                nbr_deleted += 1
        mstudent.add_students(new_list)
        mstudent.update_wisa_students(update_list)
        mstudent.flag_wisa_students(flag_list)
        log.info(f'read_from_wisa_database: processed {nbr_processed}, new {len(new_list)}, updated {len(update_list)}, deleted {nbr_deleted}')
    except Exception as e:
        log.error(f'update from wisa error: {e}')

# https://www.putorius.net/mount-windows-share-linux.html#using-the-mountcifs-command
# on the linux server, mount the windows-share (e.g  mount.cifs //MyMuse/SharedDocs /mnt/cifs -o username=putorius,password=notarealpass,domain=PUTORIUS)
# in app/static, add a symlink to the the mounted windows share.  It is assumed all photo's are in the folder 'huidig'
# photo's are copied to the 'photos' folder when a photo does not exist or it's size changed

mapped_photos_path = 'app/static/mapped_photos/huidig'
photos_path = 'app/static/photos/'

def get_photos():
    try:
        log.info("start import photo's")
        mapped_photos = glob.glob(f'{mapped_photos_path}/*jpg')
        nbr_new = 0
        nbr_updated = 0
        nbr_processed = 0
        nbr_deleted = 0

        photo_sizes = mphoto.get_photos_size()
        saved_photos = {p[1]: {'size': p[5], 'new': p[2], 'update': p[3], 'delete': p[4]} for p in photo_sizes}

        for mapped_photo in mapped_photos:
            base_name = os.path.basename(mapped_photo)
            if base_name not in saved_photos:
                photo = open(mapped_photo, 'rb').read()     # new photo
                mphoto.add_photo({'code': base_name, 'photo': photo}, commit=False)
                nbr_new += 1
            else:
                mapped_size = os.path.getsize(mapped_photo)
                if mapped_size != saved_photos[base_name]['size']:
                    photo = open(mapped_photo, 'rb').read()  # new photo
                    mphoto.update_photo(base_name, {'photo': photo, 'new': False, 'update': True, 'delete': False}, commit=False)
                    nbr_updated += 1
                else:
                    if saved_photos[base_name]['new'] or saved_photos[base_name]['update'] or saved_photos[base_name]['delete']:
                        mphoto.update_photo(base_name, {'new': False, 'update': False, 'delete': False}, commit=False) # no update
                del(saved_photos[base_name])
            nbr_processed += 1
        for code, item in saved_photos.items():
            if not saved_photos[code]['delete']:
                mphoto.update_photo(code, {'new': False, 'update': False, 'delete': True}, commit=False)  # delete only when not already marked as delete
                nbr_deleted += 1
        mphoto.commit()
        log.info(f'get_new_photos: processed: {nbr_processed}, new {nbr_new}, updated {nbr_updated}, deleted {nbr_deleted}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def wisa_cront_task(opaque):
    with flask_app.app_context():
        read_from_wisa_database()
        # get_photos()


#to have access to the photo's, mount the windowsshare
#sudo apt install keyutils


