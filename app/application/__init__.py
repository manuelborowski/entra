__all__ = ['tables', 'datatables', 'socketio', 'settings', 'warning', 'wisa', 'cron', 'cardpresso', 'photo', 'student', 'ad', 'test', 'staff', "azure"]


from app.application.photo import photo_cron_task
from app.application.wisa import wisa_get_student_cron_task
from app.application.wisa import wisa_get_staff_cron_task
from app.application.student import vsk_numbers_cron_task
from app.application.cardpresso import new_badges_cron_task
from app.application.cardpresso import new_rfid_to_database_cron_task
from app.application.ad import cron_ad_student_task
from app.application.ad import cron_ad_get_student_computer_task
from app.application.student import delete_marked_students_cron_task
from app.application.staff import deactivate_deleted_staff_cron_task
from app.application.student import clear_schoolyear_changed_flag_cron_task


# tag, cront-task, label, help
cron_table = [
    ('PHOTO', photo_cron_task, 'VAN foto (windows share), leerlingen bijwerken', ''),
    ('WISA-STUDENT', wisa_get_student_cron_task, 'VAN wisa, leerlingen bijwerken', ''),
    ('WISA-STAFF', wisa_get_staff_cron_task, 'VAN wisa, personeel bijwerken', ''),
    ('VSK-NUMMERS', vsk_numbers_cron_task, 'NAAR centrale database, Vsk nummers bijwerken', ''),
    ('CARDPRESSO-NEW', new_badges_cron_task, 'NAAR cardpresso, nieuwe badges klaarmaken', ''),
    ('CARDPRESSO-RFID', new_rfid_to_database_cron_task, 'VAN cardpresso, RFID van studenten bijwerken', ''),
    ('AD-STUDENT', cron_ad_student_task, 'NAAR AD, studenten bijwerken', ''),
    ('AD-COMPUTER', cron_ad_get_student_computer_task, 'NAAR SDH, computer van studenten bijwerken', ''),
    ('SDH-MARKED-STUDENT', delete_marked_students_cron_task, 'NAAR centrale database, verwijder gemarkeerde studenten', 'studenten die gemarkeerd zijn als delete worden uit de database verwijderd.  CHECK om de goede werking te verzekeren'),
    ('SDH-MARKED-STAFF', deactivate_deleted_staff_cron_task, 'NAAR centrale database, verwijder gemarkeerde personeelsleden', 'personeelsleden die gemarkeerd zijn als delete worden uit de database verwijderd.  CHECK om de goede werking te verzekeren'),
    ('SDH-SCHOOLYEAR-CHANGED', clear_schoolyear_changed_flag_cron_task, 'NAAR centrale database, wis schooljaar-is-veranderd-vlag', ''),
]

import app.application.azure