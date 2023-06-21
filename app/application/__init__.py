__all__ = ['tables', 'datatables', 'socketio', 'settings', 'warning', 'cron', 'cardpresso', 'photo', 'student', 'ad', 'test', 'staff', "azure", "informat"]

from app import flask_app

from app.application.photo import cron_task_photo
# from app.application.wisa import cron_task_wisa_get_student
# from app.application.wisa import cron_task_wisa_get_staff
from app.application.informat import cron_task_informat_get_student, cron_task_informat_get_staff
from app.application.student import cron_task_vsk_numbers
from app.application.cardpresso import cron_task_new_badges
from app.application.cardpresso import cron_task_new_rfid_to_database
from app.application.ad import student_process_flagged, staff_process_flagged, student_cron_task_get_computer
from app.application.student import student_post_processing
from app.application.staff import staff_post_processing
# from app.application.student import cron_task_schoolyear_clear_changed_flag


# tag, cront-task, label, help
cron_table = [
    ('PHOTO', cron_task_photo, 'VAN foto (windows share), leerlingen bijwerken', '', False),
    # ('WISA-STUDENT', cron_task_wisa_get_student, 'VAN wisa, leerlingen bijwerken', '', False),
    # ('WISA-STAFF', cron_task_wisa_get_staff, 'VAN wisa, personeel bijwerken', '', False),
    ('INFORMAT-STUDENT', cron_task_informat_get_student, 'VAN informat, leerlingen bijwerken', '', False),
    ('INFORMAT-STAFF', cron_task_informat_get_staff, 'VAN informat, personeel bijwerken', '', False),
    ('VSK-NUMMERS', cron_task_vsk_numbers, 'NAAR SDH, Vsk nummers bijwerken', '', False),
    ('CARDPRESSO-NEW', cron_task_new_badges, 'NAAR cardpresso, nieuwe badges klaarmaken', '', False),
    ('CARDPRESSO-RFID', cron_task_new_rfid_to_database, 'VAN cardpresso, RFID van studenten bijwerken', '', False),
    ('AD-STUDENT', student_process_flagged, 'NAAR AD, studenten bijwerken', '', True),
    ('AD-STAFF', staff_process_flagged, 'NAAR AD, personeel bijwerken', '', True),
    ('AD-COMPUTER', student_cron_task_get_computer, 'NAAR SDH, computer van studenten bijwerken', '', False),
    ('SDH-MARKED-STUDENT', student_post_processing, 'NAAR SDH, verwijder gemarkeerde studenten', 'studenten die gemarkeerd zijn als delete worden uit de database verwijderd.  CHECK om de goede werking te verzekeren', False),
    ('SDH-MARKED-STAFF', staff_post_processing, 'NAAR SDH, verwijder gemarkeerde personeelsleden', 'personeelsleden die gemarkeerd zijn als delete worden uit de database verwijderd.  CHECK om de goede werking te verzekeren', False),
    # ('SDH-SCHOOLYEAR-CHANGED', cron_task_schoolyear_clear_changed_flag, 'NAAR SDH, wis schooljaar-is-veranderd-vlag', '', False),
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
