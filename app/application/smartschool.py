from app import flask_app
from app.data import klas as mklas, student as mstudent, photo as mphoto
from app.data.logging import ULog
import app.application.student
import json, sys, datetime, xmltodict, base64
from functools import wraps
from app.application.util import ss_create_password
from zeep import Client

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


###############################################################
############    Common specifications          ################
###############################################################

soap = Client(flask_app.config["SS_API_URL"])

def exception_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.error(f'{func.__name__}: {e}')
    return wrapper

KLAS_CHANGED_PROPERTIES_MASK = ["klastitularis", "schooljaar"]


###############################################################
############    Student specific cron task     ################
###############################################################

@exception_wrapper
def __get_leerkrachten():
    ret = soap.service.getAllAccounts(flask_app.config["SS_API_KEY"], "leerkracht", "1")
    xml_string = base64.b64decode(ret)
    data = xmltodict.parse(xml_string)
    return data


@exception_wrapper
def __create_ss_teacher_cache():
    ss_teachers = __get_leerkrachten()
    # ss_teacher_cache = {d["gebruikersnaam"].upper(): d["internnummer"] for d in ss_teachers["accounts"]["account"]}
    ss_teacher_cache = {}
    for teacher in ss_teachers["accounts"]["account"]:
        if teacher["internnummer"] is None:
            log.error(f"{sys._getframe().f_code.co_name}, teacher {teacher['gebruikersnaam']} has NO SS internal number")
            teacher["internnummer"] = "UNKNOWN"
        ss_teacher_cache[teacher["gebruikersnaam"].upper()] = teacher["internnummer"]
    return ss_teacher_cache


@exception_wrapper
def __update_titularis(klascode, ss_titularissen):
    internnummers_string = ",".join(ss_titularissen)
    ret = soap.service.changeGroupOwners(flask_app.config["SS_API_KEY"], klascode, internnummers_string)
    if ret == 0:
        log.info(f"{sys._getframe().f_code.co_name}, Titularis {ss_titularissen} added to {klascode}")
    else:
        log.error(f"{sys._getframe().f_code.co_name}, changeGroupOwners {klascode}, {ss_titularissen} returned error {ret}")


@exception_wrapper
def __klas_process_new_update():
    log.info(f"{sys._getframe().f_code.co_name}, START")
    changed_klassen = mklas.klas_get_m([("changed", "!", ""), ("new", "=", False)])
    new_klassen = mklas.klas_get_m([("new", "=", True)])
    db_klassen = new_klassen + changed_klassen
    if db_klassen:
        teacher_cache = __create_ss_teacher_cache()
        db_klasgroepen = {k.klasgroepcode: k for k in db_klassen if k.klasgroepcode != ""}
        for klasgroep, klas in db_klasgroepen.items():
            titularissen = json.loads(klas.klastitularis)
            titularissen_string = ','.join(titularissen) if titularissen else "/"
            klasindex = klasgroep[1] if klasgroep[0] == "T" else klasgroep[0]
            if klasindex == "O":
                continue # do nothing in case of OKAN
            if int(klasindex) < 3:
                oudergroep_code = f"jaar-sum-{klasindex}"
            else:
                if klas.instellingsnummer == "30593":
                    oudergroep_code = f"jaar-sul-{klasindex}"
                else:
                    oudergroep_code = f"jaar-sui-{klasindex}"
            if klasgroep[0] == "T":
                oudergroep_code = f"t{oudergroep_code}"
            klasgroep_code = klasgroep + "G"
            ret = soap.service.saveGroup(flask_app.config["SS_API_KEY"], klasgroep, titularissen_string, klasgroep_code, oudergroep_code, "")
            if ret == 0:
                log.info(f"{sys._getframe().f_code.co_name}, Groep {oudergroep_code}/{klasgroep} added/updated")
            else:
                log.error(f"{sys._getframe().f_code.co_name}, saveGroup {oudergroep_code}/{klasgroep} returned error {ret}")
            if titularissen:
                for k in titularissen:
                    k = k.upper()
                    if k not in teacher_cache:
                        raise Exception(f"{k} is NOT found in Smartschool")
                    elif teacher_cache[k] is None:
                            raise Exception(f"{k} has no Smartschool internal number")
                titularissen_list = [teacher_cache[k.upper()] for k in titularissen]
                __update_titularis(klas.klascode, titularissen_list)

        for klas in db_klassen:
            if klas.klasgroepcode != "":
                oudergroep_code = klas.klasgroepcode + "G"
            else:
                klasindex = klas.klascode[1] if klas.klascode[0] == "T" else klas.klascode[0]
                if klasindex == "O":
                    continue # do nothing in case of OKAN
                if int(klasindex) < 3:
                    oudergroep_code = f"jaar-sum-{klasindex}"
                else:
                    if klas.instellingsnummer == "30593":
                        oudergroep_code = f"jaar-sul-{klasindex}"
                    else:
                        oudergroep_code = f"jaar-sui-{klasindex}"
                if klas.klascode[0] == "T":
                    oudergroep_code = f"t{oudergroep_code}"
            klas_datum = f"{klas.schooljaar}-09-01"
            titularissen = json.loads(klas.klastitularis)
            titularissen_string = ','.join(titularissen) if titularissen else "/"
            ret = soap.service.saveClass(flask_app.config["SS_API_KEY"], klas.klascode, titularissen_string, klas.klascode, oudergroep_code, klas.klascode, klas.instellingsnummer, klas.administratievecode, klas_datum)
            if ret == 0:
                log.info(f"{sys._getframe().f_code.co_name}, Klas {oudergroep_code}/{klas.klascode} added/updated")
            else:
                log.error(f"{sys._getframe().f_code.co_name}, saveClass {oudergroep_code}/{klas.klascode} returned error {ret}")
            if titularissen:
                for k in titularissen:
                    k = k.upper()
                    if k not in teacher_cache:
                        raise Exception(f"{k} is NOT found in Smartschool")
                    elif teacher_cache[k] is None:
                            raise Exception(f"{k} has no Smartschool internal number")
                titularissen_list = [teacher_cache[k.upper()] for k in titularissen]
                __update_titularis(klas.klascode, titularissen_list)
    log.info(f"{sys._getframe().f_code.co_name}, STOP, processed {len(db_klassen)} klassen")


@exception_wrapper
def __klas_process_delete():
    log.info(f"{sys._getframe().f_code.co_name}, START")
    db_klassen = mklas.klas_get_m([("delete", "=", True)])
    if db_klassen:
        for klas in db_klassen:
            try:
                ret = soap.service.delClass(flask_app.config["SS_API_KEY"], klas.klascode)
                if ret == 0:
                    log.info(f"{sys._getframe().f_code.co_name}, Klas {klas.klascode} deleted")
                else:
                    log.error(f"{sys._getframe().f_code.co_name}, delClass {klas.klascode} returned error {ret}")
            except Exception as e:
                log.error(f"{sys._getframe().f_code.co_name}, delClass {klas.klascode} threw error {e}")
    log.info(f"{sys._getframe().f_code.co_name}, STOP, processed {len(db_klassen)} klassen")


SS_TOP_GROEPEN_TO_CHECK = ['leerlingen', 'test-leerlingen']


def __iterate_over_groepen(groepen, leaf_groepen, klassen, check_key=True):
    try:
        for groep in groepen:
            if check_key and (not groep["code"] or "klassenstructuur" not in groep["code"]): # process marked groepen only
                continue
            if groep["type"] == "G":
                if "children" in groep:
                    __iterate_over_groepen(groep["children"]["group"], leaf_groepen, klassen, False)
                else:
                    leaf_groepen.append(groep["code"])
            elif groep["isOfficial"] == "1":
                klassen.append(groep["code"])
    except Exception as e:
        print(e)


@exception_wrapper
def __klas_process_remove_empty_groepen():
    log.info(f"{sys._getframe().f_code.co_name}, START")
    ret = soap.service.getAllGroupsAndClasses(flask_app.config["SS_API_KEY"])
    xml_string = base64.b64decode(ret)
    alle_groepen = xmltodict.parse(xml_string, force_list="group")["groups"]["group"][0]["children"]["group"]
    leaf_groepen = []
    klassen = []
    for top_groep in alle_groepen:
        if top_groep["code"] in SS_TOP_GROEPEN_TO_CHECK and "children" in top_groep:
            __iterate_over_groepen(top_groep["children"]["group"], leaf_groepen, klassen)
    groepen_to_delete = []
    for groep in leaf_groepen:
        if not groep:
            continue    # skip groepen with code None
        ret = soap.service.getAllAccounts(flask_app.config["SS_API_KEY"], groep, "0")
        xml_string = base64.b64decode(ret)
        data = xmltodict.parse(xml_string, force_list='account')
        if not data["accounts"]:
            groepen_to_delete.append(groep)
    for groep in groepen_to_delete:
        ret = soap.service.delClass(flask_app.config["SS_API_KEY"], groep)
        if ret == 0:
            log.info(f"{sys._getframe().f_code.co_name}, Groep {groep} deleted")
        else:
            log.error(f"{sys._getframe().f_code.co_name}, delClass {groep} returned error {ret}")

    # empty_klassen = []
    # for klas in klassen:
    #     ret = soap.service.getAllAccounts(flask_app.config["SS_API_KEY"], klas, "0")
    #     xml_string = base64.b64decode(ret)
    #     data = xmltodict.parse(xml_string, force_list='account')
    #     if not data["accounts"]:
    #         empty_klassen.append(klas)
    # for klas in empty_klassen:
    #     ret = soap.service.delClass(flask_app.config["SS_API_KEY"], klas)
    #     if ret == 0:
    #         log.info(f"{sys._getframe().f_code.co_name}, empty klas {klas} deleted")
    #     else:
    #         log.error(f"{sys._getframe().f_code.co_name}, delClass {klas} returned error {ret}")
    log.info(f"{sys._getframe().f_code.co_name}, STOP, processed {len(leaf_groepen)} groepen and {len(klassen)} klassen")


STUDENT_GODSDIENSTEN_MAP = {"0140": "CAT"}

STUDENT_D2S_MAP = {
    "lpv1_type": "type_coaccount1",
    "lpv1_naam": "naam_coaccount1",
    "lpv1_voornaam": "voornaam_coaccount1",
    "lpv1_gsm": "mobielnummer_coaccount1",
    "lpv1_email": "email_coaccount1",

    "lpv2_type": "type_coaccount2",
    "lpv2_naam": "naam_coaccount2",
    "lpv2_voornaam": "voornaam_coaccount2",
    "lpv2_gsm": "mobielnummer_coaccount2",
    "lpv2_email": "email_coaccount2",

    "levensbeschouwing": "Godsdienstkeuze",
    "voornaam": "name",
    "naam": "surname",
    "geslacht": "sex",
    "stamboeknummer": "stamboeknummer",
    "geboortedatum": "birthday",

    "geboorteplaats": "birthplace",
    "geboorteland": "birthcountry",
    "rijksregisternummer": "prn",
    "straat": "street",
    "huisnummer": "streetnr",
    "busnummer": "busnr",

    "postnummer": "postalCode",
    "gemeente": "location",
    "prive_email": "email",
    "gsm": "mobilePhone",
}

STUDENT_NEW_PROPERTIES_MASK = [
    "lpv1_type", "lpv1_naam", "lpv1_voornaam", "lpv1_gsm", "lpv1_email", "lpv2_type", "lpv2_naam", "lpv2_voornaam",
    "lpv2_gsm", "lpv2_email", "levensbeschouwing"
]


STUDENT_CHANGED_PROPERTIES_MASK = [
    "lpv1_type", "lpv1_naam", "lpv1_voornaam", "lpv1_gsm", "lpv1_email", "lpv2_type", "lpv2_naam", "lpv2_voornaam", "lpv2_gsm", "lpv2_email", "levensbeschouwing", "voornaam",
    "naam", "geslacht", "stamboeknummer", "geboortedatum", "geboorteplaats", "geboorteland", "rijksregisternummer", "straat", "huisnummer", "busnummer", "postnummer", "gemeente",
    "prive_email", "gsm", "klascode", "foto_id"
]


@exception_wrapper
def __student_process_new():
    log.info(f"{sys._getframe().f_code.co_name}, START")
    db_studenten = mstudent.student_get_m([("new", "=", True)])
    foto_id_cache = [s.foto_id for s in db_studenten if s.foto_id > -1]
    fotos = mphoto.photo_get_m(special={"ids": foto_id_cache})
    foto_cache = {p.id: p for p in fotos}
    for student in db_studenten:
        internnumber = student.leerlingnummer
        username = student.username
        passwd1 = ss_create_password(None, use_standard_password=True)
        passwd2 = ss_create_password(int(f"{student.leerlingnummer}2"))
        passwd3 = ss_create_password(int(f"{student.leerlingnummer}3"))
        name = student.voornaam
        surname = student.naam
        sex = student.geslacht
        birthday = str(student.geboortedatum)
        birthplace = student.geboorteplaats
        birthcountry = student.geboorteland
        adres = f"{student.straat} {student.huisnummer}"
        if student.busnummer != "":
            adres = f"{adres} bus {student.busnummer}"
        address = adres
        postalcode = student.postnummer
        location = student.gemeente
        email = student.prive_email
        mobilephone = student.gsm
        prn = student.rijksregisternummer
        stamboeknummer = student.stamboeknummer
        ret = soap.service.saveUser(flask_app.config["SS_API_KEY"], internnumber, username, passwd1, passwd2, passwd3, name, surname, "", "", sex, birthday, birthplace,
                                    birthcountry, address, postalcode, location, "", email, mobilephone, "", "", prn, stamboeknummer, "leerling", "")
        if ret == 0:
            log.info(f"{sys._getframe().f_code.co_name}, User {internnumber}/{username} added")
        else:
            log.error(f"{sys._getframe().f_code.co_name}, saveUser {internnumber} returned error {ret}")

        for db_key in STUDENT_NEW_PROPERTIES_MASK:
            v = str(getattr(student, db_key))
            if db_key == "levensbeschouwing":
                v = STUDENT_GODSDIENSTEN_MAP[v]
            ret = soap.service.saveUserParameter(flask_app.config["SS_API_KEY"], internnumber, STUDENT_D2S_MAP[db_key], v)
            if ret != 0:
                log.error(f"{sys._getframe().f_code.co_name}, saveUserParameter {internnumber}/{db_key}/{v} returned error {ret}")
        if student.foto_id in foto_cache:
            encoded_foto = base64.b64encode(foto_cache[student.foto_id].photo)
            ret = soap.service.setAccountPhoto(flask_app.config["SS_API_KEY"], internnumber, encoded_foto)
            if ret == 0:
                log.info(f"{sys._getframe().f_code.co_name}, Student {internnumber}, photo updated")
            else:
                log.error(f"{sys._getframe().f_code.co_name}, setAccountPhoto {internnumber} returned error {ret}")
        else:
            log.info(f"{sys._getframe().f_code.co_name}, Student {internnumber}, no photo found")
        ret = soap.service.saveUserToClass(flask_app.config["SS_API_KEY"], internnumber, student.klascode, str(student.inschrijvingsdatum))
        if ret == 0:
            log.info(f"{sys._getframe().f_code.co_name}, Student {internnumber} added to klas {student.klascode}")
        else:
            log.error(f"{sys._getframe().f_code.co_name}, saveUser {internnumber} returned error {ret}")
    log.info(f"{sys._getframe().f_code.co_name}, STOP, processed {len(db_studenten)} students")


@exception_wrapper
def __student_process_update():
    log.info(f"{sys._getframe().f_code.co_name}, START")
    db_studenten = mstudent.student_get_m([("changed", "!", ""), ("new", "=", False)])
    foto_id_cache = [s.foto_id for s in db_studenten if s.foto_id > -1]
    fotos = mphoto.photo_get_m(special={"ids": foto_id_cache})
    foto_cache = {p.id: p for p in fotos}
    for student in db_studenten:
        changed = json.loads(student.changed)
        changed_masked = list(set(STUDENT_CHANGED_PROPERTIES_MASK).intersection(changed))
        for db_key in changed_masked:
            if db_key == "foto_id":
                if student.foto_id in foto_cache:
                    encoded_foto = base64.b64encode(foto_cache[student.foto_id].photo)
                    ret = soap.service.setAccountPhoto(flask_app.config["SS_API_KEY"], student.leerlingnummer, encoded_foto)
                    if ret == 0:
                        log.info(f"{sys._getframe().f_code.co_name}, Student {student.leerlingnummer}, photo updated")
                    else:
                        log.error(f"{sys._getframe().f_code.co_name}, setAccountPhoto {student.leerlingnummer} returned error {ret}")
                else:
                    log.info(f"{sys._getframe().f_code.co_name}, Student {student.leerlingnummer}, no photo found")
            elif db_key == "klascode":
                ret = soap.service.saveUserToClass(flask_app.config["SS_API_KEY"], student.leerlingnummer, student.klascode, str(student.inschrijvingsdatum))
                if ret == 0:
                    log.info(f"{sys._getframe().f_code.co_name}, Student {student.leerlingnummer} added to klas {student.klascode}")
                else:
                    log.error(f"{sys._getframe().f_code.co_name}, saveUser {student.leerlingnummer} returned error {ret}")
            else:
                v = str(getattr(student, db_key))
                if db_key == "levensbeschouwing":
                    v = STUDENT_GODSDIENSTEN_MAP[v]
                ret = soap.service.saveUserParameter(flask_app.config["SS_API_KEY"], student.leerlingnummer, STUDENT_D2S_MAP[db_key], v)
                if ret != 0:
                    log.error(f"{sys._getframe().f_code.co_name}, saveUserParameter {student.leerlingnummer}/{db_key}/{v} returned error {ret}")
        else:
            if changed_masked:
                log.info(f"{sys._getframe().f_code.co_name}, Student {student.leerlingnummer}/{student.naam} {student.voornaam} update {changed_masked}")
    log.info(f"{sys._getframe().f_code.co_name}, STOP, processed {len(db_studenten)} students")


@exception_wrapper
def __student_process_delete():
    log.info(f"{sys._getframe().f_code.co_name}, START")
    db_studenten = mstudent.student_get_m([("delete", "=", True)])
    today = str(datetime.date.today())
    for student in db_studenten:
        ret = soap.service.unregisterStudent(flask_app.config["SS_API_KEY"], student.leerlingnummer, today)
        if ret == 0:
            log.info(f"{sys._getframe().f_code.co_name}, Student {student.leerlingnummer}/{student.naam} {student.voornaam} deleted")
        else:
            log.error(f"{sys._getframe().f_code.co_name}, delUser {student.leerlingnummer}/{student.naam} {student.voornaam} returned error {ret}")
    log.info(f"{sys._getframe().f_code.co_name}, STOP, processed {len(db_studenten)} students")


@exception_wrapper
def ss_student_process_flagged(opaque=None, **kwargs):
    settings = opaque if opaque else {}
    log.info(f"{sys._getframe().f_code.co_name}, START, with settings {settings}")
    __klas_process_new_update()
    __student_process_new()
    __student_process_update()
    __student_process_delete()
    __klas_process_delete()
    __klas_process_remove_empty_groepen()

    log.info(f"{sys._getframe().f_code.co_name}, STOP")
    return True


@exception_wrapper
def cron_send_ss_info_to_student_and_coaacount(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    students = mstudent.student_get_m([("new", "=", True)])
    for student in students:
        app.application.student.send_info_to_student(student)
        app.application.student.send_info_to_coaccount(student, 1)
        app.application.student.send_info_to_coaccount(student, 2)
    log.info(f"{sys._getframe().f_code.co_name}, STOP")
    return True


ACCOUNT_STUDENT = 0
ACCOUNT_CO_1 = 1
ACCOUNT_CO_2 = 2
ACCOUNT_CO_1_AND_2 = 3

def api_send_info_email(student_ids, account):
    try:
        warning = ULog(ULog.warning, "Smartschool info mailen:")
        if student_ids:
            students = mstudent.student_get_m(ids=student_ids)
            for student in students:
                if account == ACCOUNT_STUDENT:
                    valid_email = app.application.student.send_info_to_student(student)
                    if not valid_email:
                        warning.add(f"{student.naam} {student.voornaam}, {student.leerlingnummer} heeft geen e-mail")
                else:
                    accounts = [account] if account != ACCOUNT_CO_1_AND_2 else [ACCOUNT_CO_1, ACCOUNT_CO_2]
                    for a in accounts:
                        valid_account, valid_email = app.application.student.send_info_to_coaccount(student, a)
                        if not valid_account:
                            warning.add(f"{student.naam} {student.voornaam}, {student.leerlingnummer}, heeft geen co-account-{a}")
                        elif not valid_email:
                            warning.add(f"{student.naam} {student.voornaam}, {student.leerlingnummer}, co-account-{a} heeft geen e-mail")
        valid_warning = warning.finish()
        if valid_warning:
            return {"status": True, "data": valid_warning.message}
        return {"status": True, "data": "Info is verstuurd"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f"Fout, {e}"}


def api_print_info(student_ids, account):
    try:
        if student_ids:
            students = mstudent.student_get_m(ids=student_ids)
            if students:
                info_file = app.application.student.print_smartschool_info(students, account)
                return {"status": True, "data": info_file}
        return {"status": False, "data": "Geen student geselecteerd"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": False, "data": f"Fout, {e}"}
