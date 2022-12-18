__all__ = ['tables', 'datatables', 'socketio', 'settings', 'warning', 'wisa', 'cron', 'cardpresso', 'photo', 'student', 'ad', 'test', 'staff', "azure"]


from app.application.photo import cron_task_photo
from app.application.wisa import cron_task_wisa_get_student
from app.application.wisa import cront_task_wisa_get_staff
from app.application.student import cront_task_vsk_numbers
from app.application.cardpresso import cron_task_new_badges
from app.application.cardpresso import cron_task_new_rfid_to_database
from app.application.ad import cron_task_ad_student, cron_task_ad_staff, cron_task_ad_get_student_computer
from app.application.student import cron_task_delete_marked_students
from app.application.staff import cron_task_deactivate_deleted_staff
from app.application.student import cron_task_schoolyear_clear_changed_flag


# tag, cront-task, label, help
cron_table = [
    ('PHOTO', cron_task_photo, 'VAN foto (windows share), leerlingen bijwerken', ''),
    ('WISA-STUDENT', cron_task_wisa_get_student, 'VAN wisa, leerlingen bijwerken', ''),
    ('WISA-STAFF', cront_task_wisa_get_staff, 'VAN wisa, personeel bijwerken', ''),
    ('VSK-NUMMERS', cront_task_vsk_numbers, 'NAAR centrale database, Vsk nummers bijwerken', ''),
    ('CARDPRESSO-NEW', cron_task_new_badges, 'NAAR cardpresso, nieuwe badges klaarmaken', ''),
    ('CARDPRESSO-RFID', cron_task_new_rfid_to_database, 'VAN cardpresso, RFID van studenten bijwerken', ''),
    ('AD-STUDENT', cron_task_ad_student, 'NAAR AD, studenten bijwerken', ''),
    ('AD-STAFF', cron_task_ad_staff, 'NAAR AD, personeel bijwerken', ''),
    ('AD-COMPUTER', cron_task_ad_get_student_computer, 'NAAR SDH, computer van studenten bijwerken', ''),
    ('SDH-MARKED-STUDENT', cron_task_delete_marked_students, 'NAAR centrale database, verwijder gemarkeerde studenten', 'studenten die gemarkeerd zijn als delete worden uit de database verwijderd.  CHECK om de goede werking te verzekeren'),
    ('SDH-MARKED-STAFF', cron_task_deactivate_deleted_staff, 'NAAR centrale database, verwijder gemarkeerde personeelsleden', 'personeelsleden die gemarkeerd zijn als delete worden uit de database verwijderd.  CHECK om de goede werking te verzekeren'),
    ('SDH-SCHOOLYEAR-CHANGED', cron_task_schoolyear_clear_changed_flag, 'NAAR centrale database, wis schooljaar-is-veranderd-vlag', ''),
]

import app.application.azure