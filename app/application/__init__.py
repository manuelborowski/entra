__all__ = ['tables', 'datatables', 'socketio', 'settings', 'logging', 'cron', 'cardpresso', 'photo', 'student', 'ad', 'test', 'staff', "azure", "informat"]

from app import flask_app

from app.application.photo import cron_task_photo
from app.application.informat import cron_task_informat_get_student, cron_task_informat_get_staff
from app.application.student import cron_task_vsk_numbers
from app.application.cardpresso import cron_task_new_badges
from app.application.cardpresso import cron_task_new_rfid_to_database
from app.application.ad import ad_student_process_flagged, ad_staff_process_flagged, ad_student_cron_task_get_computer
from app.application.student import student_post_processing
from app.application.klas import klas_post_processing
from app.application.staff import staff_post_processing
from app.application.smartschool import ss_student_process_flagged, ss_student_coaacount_send_info_email


# tag, cront-task, label, help
cron_table = [
    ('PHOTO', cron_task_photo, 'VAN foto (windows share), leerlingen bijwerken', '', False),
    ('INFORMAT-STUDENT', cron_task_informat_get_student, 'VAN informat, leerlingen bijwerken', '', False),
    ('INFORMAT-STAFF', cron_task_informat_get_staff, 'VAN informat, personeel bijwerken', '', False),
    ('VSK-NUMMERS', cron_task_vsk_numbers, 'NAAR SDH, Vsk nummers bijwerken', '', False),
    ('CARDPRESSO-NEW', cron_task_new_badges, 'NAAR cardpresso, nieuwe badges klaarmaken', '', False),
    ('CARDPRESSO-RFID', cron_task_new_rfid_to_database, 'VAN cardpresso, RFID van studenten bijwerken', '', False),
    ('AD-STUDENT', ad_student_process_flagged, 'NAAR AD, studenten bijwerken', '', True),
    ('AD-STAFF', ad_staff_process_flagged, 'NAAR AD, personeel bijwerken', '', True),
    ('SS-STUDENT', ss_student_process_flagged, 'NAAR Smartschool, studenten bijwerken', '', True),
    ('SS-STUDENT-EMAIL', ss_student_coaacount_send_info_email, 'Nieuwe student: e-mail Smartschool gegevens', '', True),
    ('AD-COMPUTER', ad_student_cron_task_get_computer, 'NAAR SDH, computer van studenten bijwerken', '', False),
    ('SDH-MARKED-STUDENT', student_post_processing, 'NAAR SDH, reset new/delete/change flag, verwijder deleted studenten uit database', 'CHECK om de goede werking te verzekeren', False),
    ('SDH-MARKED-KLAS', klas_post_processing, 'NAAR SDH, reset new/delete/change flag, verwijder deleted klassen uit database', 'CHECK om de goede werking te verzekeren', False),
    ('SDH-MARKED-STAFF', staff_post_processing, 'NAAR SDH, reset new/delete/change flag, verwijder deleted personeelsleden uit database', 'CHECK om de goede werking te verzekeren', False),
]

import app.application.azure

# Check if the program started in testmode (configured server name is different from real server name)
# If so, disable marked crontasks to prevent unforeseen, possible disastrous, actions
flask_app.testmode = app.data.utils.get_testmode()
if flask_app.testmode:
    cron_settings = app.data.settings.get_configuration_setting("cron-enable-modules")
    for setting in cron_table:
        if setting[4]:
            cron_settings[setting[0]] = False
    app.data.settings.set_configuration_setting("cron-enable-modules", cron_settings)
