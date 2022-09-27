# l = ldap.initialize('ldap://x.x.x.x')
# l.simple_bind_s('xxx@su.local', 'pasword')
#  l.search_s("CN=firstname lastname,OU=Beheerders,OU=Accounts,DC=SU,DC=local", ldap.SCOPE_SUBTREE, attrlist=["cn"])
# l.modify_s("CN=firstname lastname,OU=Beheerders,OU=Accounts,DC=SU,DC=local", [(ldap.MOD_REPLACE, "info", [b"nieuwe info"])])
# wwwhomepage: leerlingnummer
# pager: rfid
# postofficebox: computer
# l.search_s("CN=1A,OU=Klassen,OU=Groepen,DC=SU,DC=local", ldap.SCOPE_SUBTREE, attrlist=["member"])
# l.search_s(b"CN=F\xc3\xa9 Dieltjens,OU=2020-2021,OU=Leerlingen,OU=Accounts,DC=SU,DC=local".decode("utf-8"), ldap.SCOPE_SUBTREE)
# https://social.technet.microsoft.com/wiki/contents/articles/5392.active-directory-ldap-syntax-filters.aspx
# filter : "(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))" enabled/active user
# filter : "(&(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=2))" disabled/inactive user

# l.rename_s('CN=Evelien Merckx,OU=terug,OU=2020-2021,OU=Leerlingen,OU=Accounts,DC=SU,DC=local', 'CN=Evelien Merckx', "OU=2021-2022,OU=Leerlingen,OU=Accounts,DC=SU,DC=local")
# move evelien from 2020-2021/terug to 2021-2022

#all ou's under leerlingen:  l.search_s("OU=Leerlingen,OU=Accounts,DC=SU,DC=local", ldap.SCOPE_SUBTREE, "(objectCategory=Organizationalunit)")

# use ldap3 (pip install ldap3)
# from ldap3 import Server, Connection, SAFE_SYNC

# s = ldap3.Server('ldaps://x.x.x.x', use_ssl=True)
# ldap_s = ldap3.Connection(s, 'su.local\\<user>', '<pasword>', auto_bind=True, authentication=ldap3.NTLM)
# ldap3.extend.microsoft.modifyPassword.ad_modify_password(ldap_s, 'CN=manuel test,OU=manuel-test,OU=Leerlingen,OU=Accounts,DC=SU,DC=local', 'Azerty12', None)
# set password empty
# ldap3.extend.microsoft.modifyPassword.ad_modify_password(ldap, 'CN=M-Akhunbaev Deniz,OU=2026-2027,OU=Leerlingen,OU=Accounts,DC=SU,DC=local', '', None)
# user must change password at next logon
# ldap.modify('CN=M-Akhunbaev Deniz,OU=2026-2027,OU=Leerlingen,OU=Accounts,DC=SU,DC=local', changes={"pwdLastSet": (ldap3.MODIFY_REPLACE, [0])})
# status, result, response, _ = conn.search('o=test', '(objectclass=*)')  # usually yo
# conn.add('OU=manuel-test,OU=Leerlingen,OU=Accounts,DC=SU,DC=local', 'organizationalunit') # add OU manuel-test
# ret = conn.search('OU=Leerlingen,OU=Accounts,DC=SU,DC=local', '(objectclass=*)')  returns true or false
# conn.response : return values returned
# conn.search('OU=Leerlingen,OU=Accounts,DC=SU,DC=local', '(objectclass=organizationalunit)', SUBTREE, attributes=ALL_ATTRIBUTES)
# move user to other OU
# ldap_s.modify("CN=manuel test,OU=manuel-test,OU=Leerlingen,OU=Accounts,DC=SU,DC=local", {'description': [(ldap3.MODIFY_REPLACE, 'dit is een test')]})
# conn.modify_dn('CN=Rik Fabri,OU=2018-2019,OU=Leerlingen,OU=Accounts,DC=SU,DC=local', 'CN=Rik Fabri', new_superior='OU=manuel-test,OU=Leerlingen,OU=Accounts,DC=SU,DC=local')
#  attributes = {'samaccountname': 's66666', 'wwwhomepage': '66666', 'name': 'manuel test', 'useraccountcontrol': 544, 'cn': 'manuel test', 'sn': 'test', 'l': 'manuel-6IT', 'description': 'manuel-test manuel-6IT', 'postalcode': '26-27', 'physicalDeliveryOfficeName': 'manuel-6IT', 'givenname': 'manuel', 'displayname': 'manuel test'}
# ldap_s.add(f'CN=manuel-test,{klas_location_toplevel}', 'group', {'cn': 'manuel-test', 'member': 'CN=Michiel Smans,OU=2021-2022,OU=Leerlingen,OU=Accounts,DC=SU,DC=local'})
import app
from app import log
from app.data import student as mstudent
from app.data import settings as msettings
import ldap3, json, sys
from app.application.util import get_student_voornaam

KLAS_LOCATION_TOPLEVEL = 'OU=Klassen,OU=Groepen,DC=SU,DC=local'
STUDENT_LOCATION_TOPLEVEL = 'OU=Leerlingen,OU=Accounts,DC=SU,DC=local'
TEACHER_LOCATION_TOPLEVEL = 'OU=Leerkrachten,OU=Accounts,DC=SU,DC=local'
STAFF_LOCATION_TOPLEVEL = 'OU=Secretariaat,DC=SU,DC=local'


class Context:
    def __init__(self):
        self.check_properties_changed = ['naam', 'voornaam', 'klascode', 'schooljaar', 'rfid', 'computer', 'roepnaam', 'email']
        self.student_location_toplevel = STUDENT_LOCATION_TOPLEVEL
        self.klas_location_toplevel = KLAS_LOCATION_TOPLEVEL
        self.leerlingen_group = 'CN=Leerlingen,OU=Groepen,DC=SU,DC=local'
        self.veyon_group = 'CN=Veyon-Leerling-Groeperingen,OU=Speciaal,OU=Groepen,DC=SU,DC=local'
        self.email_domain = '@lln.campussintursula.be'
        self.student_ou_current_year = ''
        self.ad_active_students_leerlingnummer = {}  # cache active students, use leerlingnummer as key
        self.ad_active_students_dn = {}  # cache active students, use dn as key
        self.ad_active_students_mail = []   # a list of existing emails, needed to check for doubles
        self.leerlingnummer_to_klas = {} # find a klas a student belongs to, use leerlingnummer as key
        self.ad_klassen = []
        self.add_student_to_klas = {}  # dict of klassen with list-of-students-to-add-to-the-klas
        self.delete_student_from_klas = {}  # dict of klassen with list-of-students-to-delete-from-the-klas
        self.new_students_to_add = []  # these students do not exist yet in AD, must be added
        self.students_to_leerlingen_group = []  # these students need to be placed in the group leerlingen
        self.students_move_to_current_year_ou = []
        self.students_change_cn = []
        self.students_must_update_password = []
        self.ldap = None
        self.changed_schoolyear, self.prev_year, self.current_year = msettings.get_changed_schoolyear()
        if self.changed_schoolyear:  # keep a local copy of changed-schoolyear
            msettings.set_configuration_setting('ad-schoolyear-changed', True)
        self.changed_schoolyear = msettings.get_configuration_setting('ad-schoolyear-changed')


# translate a list of leerlingnummers to AD-DN's   If a leerlingnummer is not found in the local cache (not active) try to find in AD
def __leerlingnummers_to_ad_dn(ctx, leerlingnummers):
    student_dns = []
    for leerlingnummer in leerlingnummers:
        if leerlingnummer in ctx.ad_active_students_leerlingnummer:
            student_dns.append(ctx.ad_active_students_leerlingnummer[leerlingnummer]['dn'])
        else:
            res = ctx.ldap.search(STUDENT_LOCATION_TOPLEVEL, f'(&(objectclass=user)(wwwhomepage={leerlingnummer}))', ldap3.SUBTREE)
            if res:
                student_dn = ctx.ldap.response[0]['dn']
                student_dns.append(student_dn)
            else:
                e = ctx.ldap.result
                log.error(f'{sys._getframe().f_code.co_name} could not find student {leerlingnummer} in AD, {e}')
    return student_dns


def __handle_student_ldap_response(ctx, student, res, info, verbose_logging=True):
    try:
        if res:
            if verbose_logging:
                log.info(f'student {student.naam} {student.voornaam}, {student.leerlingnummer}, {info}')
        else:
            log.error(f'student {student.naam} {student.voornaam}, {student.leerlingnummer}, COULD NOT {info}, {ctx.ldap.result}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# do the update of the klassen in the AD
# create sdh_klas_cache: {klas#1: [leerlingnummer#1, leerlingnummer#2,...], klas#2: [...]}
# create ad_klas_cache: {klas#1: [leerlingnummer#1, leerlingnummer#2,...], klas#2: [...]}
# compare klas per klas:
# leerlingen present in sdh and ad: ok
# leerlingen present in sdh but not in ad: add to add
# leerlingen present in ad but not in sdh: delete
def klas_put_students_in_correct_klas(ctx):
    try:
        log.info(f'{sys._getframe().f_code.co_name}, start')
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        #create SDH klas cache
        sdh_klas_cache = {}
        students = mstudent.get_students()
        for student in students:
            if student.klascode in sdh_klas_cache:
                sdh_klas_cache[student.klascode].append(student.leerlingnummer)
            else:
                sdh_klas_cache[student.klascode] = [student.leerlingnummer]
        # Create AD klas cache
        ad_klas_cache = {}
        res = ctx.ldap.search(ctx.klas_location_toplevel, '(objectclass=group)', ldap3.SUBTREE, attributes=['member', 'cn'])
        if res:
            for klas in ctx.ldap.response:
                klascode = klas['attributes']['cn']
                ad_klas_cache[klascode] = []
                for member in klas['attributes']['member']:
                    if member in ctx.ad_active_students_dn:
                        ad_klas_cache[klascode].append(ctx.ad_active_students_dn[member]['attributes']['wwwhomepage'])
                    else:
                        log.info(f'{sys._getframe().f_code.co_name}, student {member}, klas {klascode} not found in cache')
            for klascode, sdh_leerlingnummers in sdh_klas_cache.items():
                klas_dn = f'CN={klascode},{ctx.klas_location_toplevel}'
                if klascode not in ad_klas_cache:
                    # create new klas and add memebers
                    members = __leerlingnummers_to_ad_dn(ctx, sdh_leerlingnummers)
                    res = ctx.ldap.add(klas_dn, 'group', {'cn': f'{klascode}', 'member': members})
                    if res:
                        if verbose_logging:
                            log.info(f'AD: created new klas {klas_dn}, {members}')
                    else:
                        e = ctx.ldap.result
                        log.error(f'AD: could not create klas {klas_dn}, {members}, {e}')
                else:
                    add_leerlingnummers = []
                    delete_leerlingnummers = []
                    all_leerlingnummers = set(sdh_leerlingnummers)
                    all_leerlingnummers.update(set(ad_klas_cache[klascode]))
                    for nummer in all_leerlingnummers:
                        if nummer in sdh_leerlingnummers and nummer not in ad_klas_cache[klascode]:
                            add_leerlingnummers.append(nummer)
                        elif nummer in ad_klas_cache[klascode] and nummer not in sdh_leerlingnummers:
                            delete_leerlingnummers.append(nummer)
                    if add_leerlingnummers:
                        members = __leerlingnummers_to_ad_dn(ctx, add_leerlingnummers)
                        res = ctx.ldap.modify(klas_dn, {'member': [(ldap3.MODIFY_ADD, members)]})
                        if res:
                            if verbose_logging:
                                log.info(f'AD: added to klas {klas_dn}, members {members}')
                        else:
                            e = ctx.ldap.result
                            log.error(f'AD: could not add to klas {klas_dn} members {members}, {e}')
                    if delete_leerlingnummers:
                        members = __leerlingnummers_to_ad_dn(ctx, delete_leerlingnummers)
                        res = ctx.ldap.modify(klas_dn, {'member': [(ldap3.MODIFY_DELETE, members)]})
                        if res:
                            if verbose_logging:
                                log.info(f'AD: deleted from klas {klas_dn} members {members}')
                        else:
                            e = ctx.ldap.result
                            log.error(f'AD: could not delete from klas {klas_dn} members {members}, {e}')
            log.info(f'{sys._getframe().f_code.co_name}, end')
        else:
            e = ctx.ldap.result
            log.error(f'AD: could not create ad_klas_cache, {e}')
            return
        # remove empty klassen
        res = ctx.ldap.search(ctx.klas_location_toplevel, '(&(objectclass=group)(!(member=*)))', attributes=['cn'])
        if res:
            ad_klassen = ctx.ldap.response
            for klas in ad_klassen:
                res = ctx.ldap.delete(klas['dn'])
                if res:
                    log.info(f'AD, removed empty klas {klas["dn"]}')
                else:
                    log.info(f'AD, could not remove empty klas {klas["dn"]}, {ctx.ldap.result}')
            log.info(f'AD, removed {len(ad_klassen)} empty klassen')
        else:
            log.info(f'AD, could not find empty klassen, {ctx.ldap.result}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# do the update of the students to the group leerlingen in the AD
def students_do_to_group_leerlingen(ctx):
    try:
        for student in ctx.students_to_leerlingen_group:
            dn = ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['dn']
            res = ctx.ldap.modify(ctx.leerlingen_group, {'member': [(ldap3.MODIFY_ADD, dn)]})
            __handle_student_ldap_response(ctx, student, res, f'already-present-in-AD, add to group {ctx.leerlingen_group}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def ldap_init(ctx):
    try:
        ad_host = msettings.get_configuration_setting('ad-url')
        ad_login = msettings.get_configuration_setting('ad-login')
        ad_password = msettings.get_configuration_setting('ad-password')
        ldap_server = ldap3.Server(ad_host, use_ssl=True)
        ctx.ldap = ldap3.Connection(ldap_server, ad_login, ad_password, auto_bind=True, authentication=ldap3.NTLM)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def students_cache_init(ctx):
    try:
        # Create student caches
        res = ctx.ldap.search(ctx.student_location_toplevel, f'(&(objectclass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))', ldap3.SUBTREE,
                              attributes=['cn', 'wwwhomepage', 'userAccountControl', 'mail', 'l', 'sn', 'givenname', 'pager', 'displayname', 'postOfficeBox'])
        if res:
            ctx.ad_active_students_leerlingnummer = {s['attributes']['wwwhomepage']: s for s in ctx.ldap.response if s['attributes']['wwwhomepage'] != []}
            ctx.ad_active_students_dn = {s['dn']: s for s in ctx.ldap.response if s['attributes']['wwwhomepage'] != []}
            ctx.ad_active_students_mail = [s['attributes']['mail'].lower() for s in ctx.ldap.response if s['attributes']['wwwhomepage'] != []]
            log.info(f'AD: create active-students-caches, {len(ctx.ad_active_students_leerlingnummer)} entries')
        else:
            e = ctx.ldap.result
            log.error(f'AD: could not create active-students-caches, {e}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def klas_cache_init(ctx):
    try:
        # Create klas caches
        res = ctx.ldap.search(ctx.klas_location_toplevel, '(objectclass=group)', ldap3.SUBTREE, attributes=['member', 'cn'])
        if res:
            for klas in ctx.ldap.response:
                ctx.ad_klassen.append(klas['attributes']['cn'])
                ctx.leerlingnummer_to_klas.update({ctx.ad_active_students_dn[m]['attributes']['wwwhomepage']: klas['attributes']['cn'] for m in klas['attributes']['member'] if m in ctx.ad_active_students_dn})
            log.info(f'AD: create student-to-leerlingnummer-cache, with {len(ctx.leerlingnummer_to_klas)} entries')
        else:
            e = ctx.ldap.result
            log.error(f'AD: could not create student-to-leerlingnummer-cache, {e}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def ldap_deinit(ctx):
    try:
        ctx.ldap.unbind()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def create_current_year_ou(ctx):
    try:
        # check if OU current year exists.  If not, create
        log.info(f"{sys._getframe().f_code.co_name}, START")
        find_current_year_ou = ctx.ldap.search(ctx.student_location_toplevel, f'(&(objectclass=organizationalunit)(name={ctx.current_year}))', ldap3.SUBTREE)
        if not find_current_year_ou:
            res = ctx.ldap.add(f'OU={ctx.current_year},{ctx.student_location_toplevel}', 'organizationalunit')
            if res:
                log.info(f'AD: added new OU: {ctx.current_year}')
            else:
                log.error(f'AD error: could not add OU {ctx.current_year}, aborting...')
                return False
        ctx.student_ou_current_year = f'OU={ctx.current_year},{ctx.student_location_toplevel}'
        log.info(f"{sys._getframe().f_code.co_name}, STOP")

        return True
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def students_new(ctx):
    try:
        # check if new student already exists in AD (student left school and came back)
        # if so, activate and put in current OU
        log.info(f"{sys._getframe().f_code.co_name}, START")
        log.info(f"{sys._getframe().f_code.co_name}, check for students, already present in AD")
        new_students = mstudent.get_students({"new": True})
        reset_student_password = msettings.get_configuration_setting('ad-reset-student-password')
        default_password = msettings.get_configuration_setting('generic-standard-password')
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        log.info('AD: new students: if student is already in AD: activate and put in current year OU')
        for student in new_students:
            res = ctx.ldap.search(ctx.student_location_toplevel, f'(&(objectclass=user)(wwwhomepage={student.leerlingnummer}))', ldap3.SUBTREE, attributes=['cn', 'userAccountControl', 'mail'])
            if res:  # student already in AD, but inactive and probably in wrong OU and wrong klas
                ad_student = ctx.ldap.response[0]
                dn = ad_student['dn']  # old OU
                account_control = ad_student['attributes']['userAccountControl']  # to activate
                ctx.students_move_to_current_year_ou.append(student)
                if reset_student_password:
                    ctx.students_must_update_password.append(student)
                account_control &= ~2  # clear bit 2 to activate
                changes = {
                    'userAccountControl': [(ldap3.MODIFY_REPLACE, [account_control])],
                    'description': [ldap3.MODIFY_REPLACE, (f'{student.schooljaar} {student.klascode}')],
                    'postalcode': [ldap3.MODIFY_REPLACE, (student.schooljaar,)],
                    'l': [ldap3.MODIFY_REPLACE, (student.klascode)],
                    'physicalDeliveryOfficeName': [ldap3.MODIFY_REPLACE, (student.klascode)],
                }
                if student.rfid and student.rfid != '':
                    changes.update({'pager': [ldap3.MODIFY_REPLACE, (student.rfid)]})
                res = ctx.ldap.modify(dn, changes)
                __handle_student_ldap_response(ctx, student, res, f'already-present-in-AD, changed {changes}', verbose_logging=verbose_logging)
                if reset_student_password:
                    res = ldap3.extend.microsoft.modifyPassword.ad_modify_password(ctx.ldap, dn, default_password, None)  # reset the password to default
                    __handle_student_ldap_response(ctx, student, res, f'set default password', verbose_logging=verbose_logging)
                if student.email != ad_student['attributes']['mail']:
                    mstudent.update_student(student, {'email': ad_student['attributes']['mail']})
                    if verbose_logging:
                        log.info(f'add-new-student-already-in-ad, {student.naam} {student.voornaam}, {student.leerlingnummer}, update email in SDH {ad_student["attributes"]["mail"]}')
                # add student to cache
                ctx.ad_active_students_leerlingnummer[student.leerlingnummer] = ad_student
                ctx.students_to_leerlingen_group.append(student)
            else:
                ctx.new_students_to_add.append(student)

        log.info(f"{sys._getframe().f_code.co_name}, new students, not in AD yet")
        # add new students to current OU
        # new students are created with default password and are required to set a password at first login
        object_class = ['top', 'person', 'organizationalPerson', 'user']
        for student in ctx.new_students_to_add:
            cn = f'{student.naam} {student.voornaam}'
            dn = f'CN={cn},{ctx.student_ou_current_year}'
            email = student.email
            if student.email in ctx.ad_active_students_mail or dn in ctx.ad_active_students_dn and ctx.ad_active_students_dn[dn]['attributes']['wwwhomepage'] != student.leerlingnummer:
                leerlingnummer_suffix = str(student.leerlingnummer)[-2:]
                cn = f'{cn} {leerlingnummer_suffix}'
                dn = f'CN={cn},{ctx.student_ou_current_year}'
                email_split = student.email.split('@')
                email = f'{email_split[0]}{leerlingnummer_suffix}@{email_split[1]}'
                mstudent.update_student(student, {'email': email})
                if verbose_logging:
                    log.info(f'student with same name already in ad, {student.naam} {student.voornaam}, {student.leerlingnummer}, email is {email}')
            attributes = {'samaccountname': student.username, 'wwwhomepage': f'{student.leerlingnummer}',
                          'userprincipalname': f'{student.username}{ctx.email_domain}',
                          'mail': email,
                          'name': f'{student.naam} {student.voornaam}',
                          'useraccountcontrol': 0X220,     #password not required, normal account, account active
                          'cn': cn,
                          'sn': student.naam,
                          'l': student.klascode,
                          'description': f'{student.schooljaar} {student.klascode}', 'postalcode': student.schooljaar,
                          'physicaldeliveryofficename': student.klascode, 'givenname': student.voornaam,
                          'displayname': f'{app.application.util.get_student_voornaam(student)} {student.naam} '}
            if student.rfid and student.rfid != '':
                attributes['pager'] = student.rfid
            res = ctx.ldap.add(dn, object_class, attributes)
            __handle_student_ldap_response(ctx, student, res, f'new-in-AD, changed {attributes}', verbose_logging=verbose_logging)
            res = ldap3.extend.microsoft.modifyPassword.ad_modify_password(ctx.ldap, dn, default_password, None)  # reset the password to empty
            __handle_student_ldap_response(ctx, student, res, 'set standard password', verbose_logging=verbose_logging)
            ad_student = {'dn': dn, 'attributes': {'cn': cn}}
            ctx.ad_active_students_leerlingnummer[student.leerlingnummer] = ad_student
            ctx.students_to_leerlingen_group.append(student)
            ctx.students_must_update_password.append(student)
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def students_changed(ctx):
    try:
        # check if there are students with valid, changed attributes.  If so, update the attributes
        # if required, move the students to the current OU
        log.info(f"{sys._getframe().f_code.co_name}, START")
        changed_students = mstudent.get_students({"-changed": "", "new": False})
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        if changed_students:
            for student in changed_students:
                changed = json.loads(student.changed)
                if list(set(ctx.check_properties_changed).intersection(changed)):
                    if student.leerlingnummer in ctx.ad_active_students_leerlingnummer:
                        changes = {}
                        if 'naam' in changed or 'voornaam' in changed:
                            changes.update({
                                            'sn': [ldap3.MODIFY_REPLACE, (student.naam)],
                                            'givenname': [ldap3.MODIFY_REPLACE, (student.voornaam)],
                                            'displayname': [ldap3.MODIFY_REPLACE, (f'{app.application.util.get_student_voornaam(student)} {student.naam}')]})
                            ctx.students_change_cn.append(student)
                        if 'roepnaam' in changed and student.roepnaam != '':
                            changes.update({'displayname': [ldap3.MODIFY_REPLACE, (f'{app.application.util.get_student_voornaam(student)} {student.naam}')]})
                        if 'email' in changed:
                            changes.update({'mail': [ldap3.MODIFY_REPLACE, (student.email)]})
                        if 'rfid' in changed:
                            changes.update({'pager': [ldap3.MODIFY_REPLACE, (student.rfid)]})
                        if 'schooljaar' in changed or 'klascode' in changed:
                            changes.update(
                                {'description': [ldap3.MODIFY_REPLACE, (f'{student.schooljaar} {student.klascode}')],
                                 'postalcode': [ldap3.MODIFY_REPLACE, (student.schooljaar,)],
                                 'l': [ldap3.MODIFY_REPLACE, (student.klascode)],
                                 'physicalDeliveryOfficeName': [ldap3.MODIFY_REPLACE, (student.klascode)]})
                        res = ctx.ldap.modify(ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['dn'], changes)
                        __handle_student_ldap_response(ctx, student, res, f'already-present-in-AD, changed {changes}', verbose_logging=verbose_logging)
                        if 'schooljaar' in changed:  # move to new OU
                            ctx.students_move_to_current_year_ou.append(student)
                    else:
                        log.error(f'{sys._getframe().f_code.co_name}, student {student.naam} {student.voornaam}, {student.leerlingnummer}, NOT PRESENT in AD')
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def students_deleted(ctx):
    try:
        log.info(f"{sys._getframe().f_code.co_name}, START")
        deleted_students = mstudent.get_students({"delete": True})
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        deactivate_student = msettings.get_configuration_setting('ad-deactivate-deleled-student')
        if deleted_students:
            for student in deleted_students:
                if deactivate_student:
                    ad_student = ctx.ad_active_students_leerlingnummer[student.leerlingnummer]
                    dn = ad_student['dn']
                    account_control = ad_student['attributes']['userAccountControl']  # to activate
                    account_control |= 2  # set bit 2 to deactivate
                    changes = {'userAccountControl': [(ldap3.MODIFY_REPLACE, [account_control])]}
                    res = ctx.ldap.modify(dn, changes)
                    __handle_student_ldap_response(ctx, student, res, 'deactive', verbose_logging=verbose_logging)
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# These tasks are done last because they alter the DN, which is used to identify the students in the AD.
def students_process_postponed_tasks(ctx):
    try:
        log.info(f"{sys._getframe().f_code.co_name}, START move students to current-year-OU")

        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        for student in ctx.students_move_to_current_year_ou:
            dn = ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['dn']
            cn = f"CN={ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['attributes']['cn']}"
            res = ctx.ldap.modify_dn(dn, cn, new_superior=ctx.student_ou_current_year)
            __handle_student_ldap_response(ctx, student, res, f'moved to OU {ctx.student_ou_current_year}', verbose_logging=verbose_logging)
        log.info(f"{sys._getframe().f_code.co_name}, START update CN (student has name changed)")
        for student in ctx.students_change_cn:
            old_cn = ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['attributes']['cn']
            old_dn = f'CN={old_cn},{ctx.student_ou_current_year}'
            new_cn = f'CN={student.naam} {student.voornaam}'
            new_dn = f'{new_cn},{ctx.student_ou_current_year}'
            if new_dn in ctx.ad_active_students_dn and ctx.ad_active_students_dn[new_dn]['attributes']['wwwhomepage'] != student.leerlingnummer:  # check if CN alreaddy exists.  If so, append part of leerlingnummer
                leerlingnummer_suffix = str(student.leerlingnummer)[-2:]
                new_cn = f'{new_cn} {leerlingnummer_suffix}'
            res = ctx.ldap.modify_dn(old_dn, new_cn, new_superior=ctx.student_ou_current_year)
            __handle_student_ldap_response(ctx, student, res, f'updated CN {new_cn}', verbose_logging=verbose_logging)
        log.info(f"{sys._getframe().f_code.co_name}, START update password")
        for student in ctx.students_must_update_password:
            cn = f"CN={ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['attributes']['cn']}"
            dn = f'{cn},{ctx.student_ou_current_year}'
            changes = {"pwdLastSet": [(ldap3.MODIFY_REPLACE, [0])]}  # student must update password at first login
            res = ctx.ldap.modify(dn, changes)
            __handle_student_ldap_response(ctx, student, res, f'changed {changes}', verbose_logging=verbose_logging)
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def students_must_update_password(ctx):
    try:
        log.info(f"{sys._getframe().f_code.co_name}, START")
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        for student in ctx.students_must_update_password:
            cn = f"CN={ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['attributes']['cn']}"
            dn = f'{cn},{ctx.student_ou_current_year}'
            changes = {"pwdLastSet": [(ldap3.MODIFY_REPLACE, [0])]}  # student must update password at first login
            res = ctx.ldap.modify(dn, changes)
            __handle_student_ldap_response(ctx, student, res, f'changed {changes}', verbose_logging=verbose_logging)
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# check if a student is in 2 or more classes,  If so, remove from all but in 'kantoor' (i.e. l-property)
def klas_check_if_student_is_in_one_klas(ctx):
    try:
        log.info(f"{sys._getframe().f_code.co_name}, START")
        remove_students_from_klas = {}
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        # re-create student cache.  Students may have an updated klas
        res = ctx.ldap.search(ctx.student_location_toplevel, f'(&(objectclass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))', ldap3.SUBTREE, attributes=['cn', 'wwwhomepage', 'l'])
        if res:
            ad_active_students_cn = {s['dn']: s for s in ctx.ldap.response if s['attributes']['wwwhomepage'] != []}
            # re-create klas cache, students may have an update klas
            res = ctx.ldap.search(ctx.klas_location_toplevel, '(objectclass=group)', ldap3.SUBTREE, attributes=['member', 'cn'])
            if res:
                for klas in ctx.ldap.response:
                    for member in klas['attributes']['member']:
                        if member in ad_active_students_cn:
                            student_klas = ad_active_students_cn[member]['attributes']['l']
                            if student_klas != klas['attributes']['cn']:
                                # student should not be in this klas
                                if klas["dn"] in remove_students_from_klas:
                                    remove_students_from_klas[klas["dn"]].append(ad_active_students_cn[member]["dn"])
                                else:
                                    remove_students_from_klas[klas["dn"]] = [ad_active_students_cn[member]["dn"]]
                                if verbose_logging:
                                    log.info(f'remove student {ad_active_students_cn[member]["dn"]}, klas {ad_active_students_cn[member]["attributes"]["l"]}, from klas, {klas["dn"]}')
                log.info(f'AD: students-in-double-klas, nbr of students in multiple klassen {len(remove_students_from_klas)} ')
                for klas_dn, members in remove_students_from_klas.items():
                    res = ctx.ldap.modify(klas_dn, {'member': [(ldap3.MODIFY_DELETE, members)]})
                    if res:
                        log.info(f'AD: removed from klas {klas_dn} members {members}')
                    else:
                        log.error(f'AD: could not remove from klas {klas_dn} members {members}')
            else:
                log.error('AD: could not create single/multiple-klas cache')
        else:
            log.error('AD: could not create student cache')
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# should be executed once to update the usernames in SDH from AD
def get_usernames_from_ad():
    try:
        log.info(('Read usernames from AD'))
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        ad_host = msettings.get_configuration_setting('ad-url')
        ad_login = msettings.get_configuration_setting('ad-login')
        ad_password = msettings.get_configuration_setting('ad-password')
        ldap_server = ldap3.Server(ad_host, use_ssl=True)
        ldap = ldap3.Connection(ldap_server, ad_login, ad_password, auto_bind=True, authentication=ldap3.NTLM)
        # Create student caches
        res = ldap.search(STUDENT_LOCATION_TOPLEVEL, f'(&(objectclass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))', ldap3.SUBTREE, attributes=['wwwhomepage', 'samaccountname'])
        if res:
            ad_leerlingnummer_to_username = {s['attributes']['wwwhomepage']: s['attributes']['samaccountname'] for s in ldap.response if s['attributes']['wwwhomepage'] != []}
            log.info(f'AD: create ad_leerlingnummer_to_username cache, {len(ad_leerlingnummer_to_username)} entries')
        else:
            log.error('AD: could not ad_leerlingnummer_to_username cache')
            return
        ldap.unbind()
        students = mstudent.get_students()
        nbr_students = 0
        for student in students:
            if not student.username and student.leerlingnummer in ad_leerlingnummer_to_username:
                student.username = ad_leerlingnummer_to_username[student.leerlingnummer]
                nbr_students += 1
                if verbose_logging:
                    log.info(f'{sys._getframe().f_code.co_name}, {student.naam} {student.voornaam}, {student.leerlingnummer}, update username in SDH {student.username}')
        mstudent.commit()
        log.info(f'{sys._getframe().f_code.co_name}, Update usernames from AD, updated {nbr_students} students')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


# should be executed once to set the displayname in ad correct (first-name last name) and the cn (last-name first-name)
def update_ad_cn_and_displayname():
    try:
        ctx = Context()
        ldap_init(ctx)
        students_cache_init(ctx)
        if not create_current_year_ou(ctx):
            ldap_deinit(ctx)
            return

        log.info('update CN and displayname')
        studenten = mstudent.get_students()
        naam_cache = []
        for student in studenten:
            if student.leerlingnummer in ctx.ad_active_students_leerlingnummer:
                dn = ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['dn']
                if student.naam + student.voornaam in naam_cache:
                    leerlingnummer_suffix = str(student.leerlingnummer)[-2:]
                    new_cn = f'CN={student.naam} {student.voornaam} {leerlingnummer_suffix}'
                    log.info(f'Student already exists, cn is {new_cn}')
                else:
                    new_cn = f'CN={student.naam} {student.voornaam}'
                    naam_cache.append(student.naam + student.voornaam)
                # update displayname
                res = ctx.ldap.modify(dn, {'displayname': [ldap3.MODIFY_REPLACE, (f'{student.voornaam} {student.naam}')]})
                if res:
                    log.info(f'Student {student.naam} {student.voornaam}, {student.leerlingnummer}, updated displayname')
                else:
                    log.error(f'Student {student.naam} {student.voornaam}, {student.leerlingnummer}, could not update displayname, {ctx.ldap.result}')
                # update cn
                res = ctx.ldap.modify_dn(dn, new_cn, new_superior=ctx.student_ou_current_year)
                if res:
                    log.info(f'Student {student.naam} {student.voornaam}, {student.leerlingnummer}, changed dn {dn} to cn {new_cn}')
                else:
                    log.error(f'Student {student.naam} {student.voornaam}, {student.leerlingnummer}, could not update, {ctx.ldap.result}')

            else:
                log.error(f'Student {student.naam} {student.voornaam}, {student.leerlingnummer} not found in AD')
        ldap_deinit(ctx)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def cron_ad_student_task(opaque=None):
    try:
        log.info(f"{sys._getframe().f_code.co_name}, START")
        ctx = Context()
        ldap_init(ctx)
        students_cache_init(ctx)
        if not create_current_year_ou(ctx):
            ldap_deinit(ctx)
            return {"status": False, "data": "Kan huidig-jaar-ou niet aanmaken"}
        students_new(ctx)
        students_changed(ctx)
        students_deleted(ctx)
        klas_cache_init(ctx)
        klas_put_students_in_correct_klas(ctx)  # put all students in the correct klas in AD
        students_do_to_group_leerlingen(ctx) # then put the new students in the group leerlingen
        students_process_postponed_tasks(ctx) # then move the students to the current schoolyear OU
        klas_check_if_student_is_in_one_klas(ctx)
        ldap_deinit(ctx)

        # only once and then comment out
        # get_usernames_from_ad()
        # only once and then comment out
        # update_ad_cn_and_displayname()

        msettings.set_configuration_setting('ad-schoolyear-changed', False)
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
        return {"status": True, "data": "AD sync is ok"}
    except Exception as e:
        log.error(f'update to AD error: {e}')
        return {"status": False, "data": e}


def cron_ad_get_student_computer_task(opaque=None):
    try:
        log.info(f"{sys._getframe().f_code.co_name}, START")
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        ctx = Context()
        ldap_init(ctx)
        students_cache_init(ctx)
        students = mstudent.get_students()
        for student in students:
            if student.leerlingnummer in ctx.ad_active_students_leerlingnummer:
                computers = ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['attributes']['postOfficeBox']
                computer = computers[0] if computers else ''
                mstudent.update_student(student, {'computer': computer}, commit=False)
                if verbose_logging:
                    log.info(f'Student {student.naam} {student.voornaam}, {student.leerlingnummer}, updated computer {computer}')
            else:
                log.error(f'Student {student.naam} {student.voornaam}, {student.leerlingnummer}, not found in AD')
        mstudent.commit()
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.info(f"{sys._getframe().f_code.co_name}, {e}")




def update_student(student, data):
    try:
        update_property([STUDENT_LOCATION_TOPLEVEL], student.username, data)
    except Exception as e:
        raise e


def update_staff(staff, data):
    try:
        update_property([STAFF_LOCATION_TOPLEVEL, TEACHER_LOCATION_TOPLEVEL], staff.code, data)
    except Exception as e:
        raise e


def update_property(ous, username, data):
    try:
        ad_host = msettings.get_configuration_setting('ad-url')
        ad_login = msettings.get_configuration_setting('ad-login')
        ad_password = msettings.get_configuration_setting('ad-password')
        ldap_server = ldap3.Server(ad_host, use_ssl=True)
        ldap = ldap3.Connection(ldap_server, ad_login, ad_password, auto_bind=True, authentication=ldap3.NTLM)
        found = False
        for ou in ous:
            res = ldap.search(ou, f'(&(objectclass=user)(samaccountname={username}))', ldap3.SUBTREE, attributes=['cn', 'userAccountControl', 'mail', 'pager'])
            if res:
                found = True
                ad_user = ldap.response[0]
                if 'rfid' in data:
                    if data['rfid'] == '':
                        changes = {'pager': [ldap3.MODIFY_DELETE, ([])]}
                    else:
                        changes = {'pager': [ldap3.MODIFY_REPLACE, (data['rfid'])]}
                    res = ldap.modify(ad_user['dn'], changes)
                    if res:
                        log.info(f'Update to AD, {username} RFID {data}')
                    else:
                        log.error(f'{sys._getframe().f_code.co_name}: could not update changes of {username}: {changes}')
                        raise Exception('Kan AD niet updaten')
                if 'password' in data:
                    res = ldap3.extend.microsoft.modifyPassword.ad_modify_password(ldap, ad_user['dn'], data['password'], None)
                    if res:
                        log.info(f'Updated password of {username}')
                    else:
                        log.error(f'{sys._getframe().f_code.co_name}: could not update password of {username}')
                        raise Exception('Paswoord voldoet niet aan de eisen')
                if 'must_update_password' in data and data['must_update_password']:
                    res = ldap.modify(ad_user['dn'], changes={"pwdLastSet": (ldap3.MODIFY_REPLACE, [0])})
                    if res:
                        log.info(f'{username} must set password at next login')
                    else:
                        log.error(f'{sys._getframe().f_code.co_name}: could not update set-password-at-next-login of {username}')
                        raise Exception('Paswoord-opnieuw-instellen kan niet worden gezet')
                break
        if not found:
            log.error(f'{sys._getframe().f_code.co_name}: could not find {username} in AD')
            raise Exception(f'Kan {username} niet vinden in AD')
        ldap.unbind()
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


# if return_log is True, return the logging as a single string.
def database_integrity_check(return_log=False, mark_changes_in_db=False):

    class DisplayLog :
        def __init__(self):
            self.log = ''

        def add(self, text):
            if return_log:
                self.log += text
                self.log += '\n'
        def get(self):
            return self.log if self.log != '' else 'Check ok'

    def __check_property(student, sdh_property, ad_property, db_property):
        if sdh_property != ad_property:
            if verbose_logging:
                log.info(f'{sys._getframe().f_code.co_name}: student {student.leerlingnummer} {db_property.upper()}, SDH="{sdh_property}", AD="{ad_property}"')
            dl.add(f'AD, student {student.naam} {student.voornaam}, {student.leerlingnummer}, {db_property.upper()}, SDH="{sdh_property}", AD="{ad_property}"')
            if student in changed_students:
                changed_students[student].append(db_property)
            else:
                changed_students[student] = [db_property]

    try:
        verbose_logging = msettings.get_configuration_setting('ad-verbose-logging')
        dl = DisplayLog()
        log.info(f'{sys._getframe().f_code.co_name}: start')
        ctx = Context()
        ldap_init(ctx)
        sdh_students = mstudent.get_students()
        students_cache_init(ctx)
        changed_students = {}
        for student in sdh_students:
            if student.leerlingnummer in ctx.ad_active_students_leerlingnummer:
                ad_student = ctx.ad_active_students_leerlingnummer[student.leerlingnummer]['attributes']
                __check_property(student, student.naam, ad_student['sn'], 'naam')
                __check_property(student, f"{get_student_voornaam(student)} {student.naam}", ad_student['displayname'], 'roepnaam')
                __check_property(student, student.voornaam, ad_student['givenname'], 'voornaam')
                __check_property(student, student.klascode, ad_student['l'], 'klascode')
                __check_property(student, student.email, ad_student['mail'].lower(), 'email')
                if not ad_student['pager']:
                    ad_student['pager'] = None
                __check_property(student, student.rfid, ad_student['pager'], 'rfid')
            else:
                log.info(f'{sys._getframe().f_code.co_name}: student {student.leerlingnummer} not found in AD')
                dl.add(f'AD, student {student.leerlingnummer} niet gevonden in AD')
        if mark_changes_in_db:
            flagged_students = [{'student': s, 'changed': json.dumps(c)} for s, c in changed_students.items()]
            mstudent.flag_students(flagged_students)
        ldap_deinit(ctx)
        log.info(f'{sys._getframe().f_code.co_name}: end')
        return {"status": True, "data": dl.get()}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": e}


