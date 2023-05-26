from app.data import photo as mphoto
from app.application import settings as msettings
import base64, glob, os, sys, datetime


#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())



def api_photo_get_m(ids):
    try:
        photos = mphoto.photo_get_m(special={"ids": ids})
        encoded_photos = [{"id": p.id, "photo": base64.b64encode(p.photo).decode("ascii")} for p in photos]
        return {"status": True, "data": encoded_photos}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}


def api_photo_get_size_m(ids):
    try:
        photos = mphoto.photo_get_size_m(ids=ids)
        size_list = [{"id": p[0], "size": p[5]} for p in photos]
        return {"status": True, "data": size_list}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}


def api_photo_get_size_all():
    try:
        photos = mphoto.photo_get_size_all()
        size_list = [{"id": p[0], "size": p[5]} for p in photos]
        return {"status": True, "data": size_list}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}



#to have access to the photo's, mount the windowsshare
#sudo apt install keyutils
# https://www.putorius.net/mount-windows-share-linux.html#using-the-mountcifs-command
# on the linux server, mount the windows-share (e.g  mount.cifs //MyMuse/SharedDocs /mnt/cifs -o username=putorius,password=notarealpass,domain=PUTORIUS)
# in app/static, add a symlink to the the mounted windows share.  It is assumed all photo's are in the folder 'huidig'
# photo's are copied to the 'photos' folder when a photo does not exist or it's size changed
# wsl: sudo mount -t drvfs //10.10.0.211/sec /mnt/sec
# debian: sudo mount -t cifs -o username=xxxx //xxx.xxx.xxx.xxx/sec /mnt/sec

mapped_photos_path = 'app/static/mapped_photos/huidig'


def cron_task_photo(opaque=None):
    try:
        log.info("start import photo's")
        verbose_logging = msettings.get_configuration_setting('photo-verbose-logging')
        mapped_photos = glob.glob(f'{mapped_photos_path}/*jpg')
        nbr_new = 0
        nbr_updated = 0
        nbr_processed = 0
        nbr_deleted = 0

        photo_sizes = mphoto.photo_get_size_all()
        # (Photo.id, Photo.filename, Photo.new, Photo.changed, Photo.delete, func.octet_length(Photo.photo, Photo.timestamp)
        saved_photos = {p[1]: {'size': p[5], "timestamp": p[6], 'new': p[2], 'changed': p[3], 'delete': p[4]} for p in photo_sizes}

        for mapped_photo in mapped_photos:
            base_name = os.path.basename(mapped_photo)
            timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(mapped_photo))
            if base_name not in saved_photos:
                photo = open(mapped_photo, 'rb').read()  # new photo
                mphoto.add_photo({'filename': base_name, 'photo': photo, "timestamp": timestamp}, commit=False)
                nbr_new += 1
                if verbose_logging:
                    log.info(f'New photo {base_name}, {timestamp}')
            else:
                mapped_size = os.path.getsize(mapped_photo)
                if mapped_size != saved_photos[base_name]['size']:
                    photo = open(mapped_photo, 'rb').read()  # updated photo, different size
                    mphoto.update_photo(base_name, {'photo': photo, 'new': False, 'changed': True, 'delete': False, "timestamp": timestamp }, commit=False)
                    nbr_updated += 1
                    if verbose_logging:
                        log.info(f'Updated photo {base_name}')
                del (saved_photos[base_name])
            nbr_processed += 1
            if (nbr_processed % 100) == 0:
                log.info(f'get_photos: processed {nbr_processed} photo\'s...')
        for filename, item in saved_photos.items():
            if not saved_photos[filename]['delete']:
                mphoto.update_photo(filename, {'new': False, 'changed': False, 'delete': True}, commit=False)  # delete only when not already marked as delete
                nbr_deleted += 1
        mphoto.reset_flags()
        mphoto.commit()
        log.info(f'get_new_photos: processed: {nbr_processed}, new {nbr_new}, updated {nbr_updated}, deleted {nbr_deleted}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e



