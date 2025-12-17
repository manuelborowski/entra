__all__ = ['tables', 'datatables', 'socketio', 'settings', 'logging', 'cron', 'student', 'staff', "entra", "sdh", "device", "email"]

from app import flask_app
from app.application.sdh import cron_staff_load_from_sdh, cron_student_load_from_sdh, cron_klas_load_from_sdh, cron_push_devices
from app.application.entra import cron_sync_groups, cron_sync_users, cron_sync_cc_auto_teams, cron_sync_team_activities, cron_sync_devices, cron_verify_cc_auto_teams, cron_cleanup_db
from app.application.device import cron_remove_devices

# tag, cront-task, label, help
cron_table = [
    ('SDH-STUDENT', cron_student_load_from_sdh, 'VAN SDH, leerlingen bijwerken', '', False),
    ('SDH-STAFF', cron_staff_load_from_sdh, 'VAN SDH, personeel bijwerken', '', False),
    ('SDH-KLAS', cron_klas_load_from_sdh, 'VAN SDH, klassen bijwerken', '', False),
    ('ENTRA-SYNC-USERS', cron_sync_users, 'VAN ENTRA, sync leerlingen en personeel', '', False),
    ('ENTRA-SYNC-GROUPS', cron_sync_groups, 'VAN ENTRA, sync groepen', '', False),
    ('ENTRA-SYNC-ACTIVITIES', cron_sync_team_activities, 'VAN ENTRA, sync team activities', '', False),
    ('ENTRA-SYNC-CC-TEAMS', cron_sync_cc_auto_teams, 'NAAR ENTRA, sync classroomcloud teams', '', False),
    ('ENTRA-VERIFY-CC-TEAMS', cron_verify_cc_auto_teams, 'VERIFIEER classroomcloud teams', '', False),
    ('ENTRA-SYNC-DEVICES', cron_sync_devices, 'VAN ENTRA, sync devices', '', False),
    ('ENTRA-REMOVE-DEVICES', cron_remove_devices, 'NAAR ENTRA, verwijder devices', '', False),
    ('SDH-PUSH-DEVICES', cron_push_devices, 'VAN DB NAAR SDH, sync devices', '', False),
    ('DB-CLEANUP', cron_cleanup_db, 'NAAR DB, reset DB vlaggen', '', False),
]

import app.application.entra

# Check if the program started in testmode (configured server name is different from real server name)
# If so, disable marked crontasks to prevent unforeseen, possible disastrous, actions
flask_app.testmode = app.data.utils.get_testmode()
if flask_app.testmode:
    cron_settings = app.data.settings.get_configuration_setting("cron-enable-modules")
    for setting in cron_table:
        if setting[4]:
            cron_settings[setting[0]] = False
    app.data.settings.set_configuration_setting("cron-enable-modules", cron_settings)

import app.application.email