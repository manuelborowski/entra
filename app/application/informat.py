# LPV
# Relaties
# < WsRelaties >
# < PPersoon > 62157 < / PPersoon >  ==> leerlingnummer
# < Relaties >
# < Relatie >
# < PRelatie > 60447 < / PRelatie >  ==> komt voor in ComnummersRelatie
# < Type > Moeder < / Type >
# < Naam > xxx < / Naam >
# < Voornaam > xxxx < / Voornaam >
# < Geslacht > V < / Geslacht >
# < Lpv > 1 < / Lpv >
# ComnummersRelaties
# < PPersoon > 62157 < / PPersoon >  ==> leerlingnummer
# < Nummer > 04 89 64 91 96 < / Nummer >
# < PRelatie > 60447 < / PRelatie >  ==> Komt van Relaties
# EmailRelaties
# < PPersoon > 62157 < / PPersoon >  ==> leerlingnummer
# < Email >
# < Adres > margit.hannes @ opzgeel.be < / Adres >
# < PRelatie > 60447 < / PRelatie >   ==> Komt van Relaties


# Klas en Klasgroep
# <wsKlasgroep>
# <p_persoon>86493</p_persoon>  ==> leerlingnummer
# <Groeptype>1</Groeptype>  ==> klasgroepcode
# <Klascode>5A EWi</Klascode>
# < wsKlasgroep >
# < p_persoon > 86493 < / p_persoon >  ==> leerlingnummer
# < Groeptype > 0 < / Groeptype > ==> officiele klas
# < Klastitularis > xxx yyy < / Klastitularis >
# < Klascode > 5A < / Klascode >

# levensbeschouwing codes
# Islamitische godsdienst,...


from app import flask_app
from app.data import student as mstudent, photo as mphoto, settings as msettings, staff as mstaff, utils as mutils, klas as mklas
import datetime, xmltodict
import json, requests, sys

# logging on file level
import logging
from app import MyLogFilter, top_log_handle

log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

# used to translate diacretic letters into regular letters (username, emailaddress)
normalMap = {'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
             'ª': 'A',
             'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E', 'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
             'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I', 'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
             'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O', 'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
             'º': 'O', '°': 'O',
             'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U', 'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
             'Ñ': 'N', 'ñ': 'n',
             'Ç': 'C', 'ç': 'c',
             '§': 'S', '³': '3', '²': '2', '¹': '1', ' ': '', '\'': ''}
normalize_letters = str.maketrans(normalMap)

STUDENT_MAP_I_Lln2DB_KEYS = {
    "Voornaam": "voornaam", "Naam": "naam", "rijksregnr": "rijksregisternummer", "Stamnr_kort": "stamboeknummer",
    "p_persoon": "leerlingnummer", "begindatum": "inschrijvingsdatum", "instelnr": "instellingsnummer", "Klascode": "klascode",
    "nr_admgr": "administratievecode", "Klasnr": "klasnummer", "Levensbeschouwing": "levensbeschouwing"
}


STUDENT_MAP_I_LlnExtra2DB_KEYS = {
    "GSMeigen": "gsm",
    "EmailEigen": "prive_email",
    "Fietsnummer": "middag"
}


STUDENT_CHANGED_PROPERTIES_MASK = [
    "voornaam", "naam", "roepnaam", "rijksregisternummer", "stamboeknummer", "geboortedatum", "geboorteplaats", "geboorteland", "geslacht", "nationaliteit",
    "levensbeschouwing", "straat", "huisnummer", "busnummer", "postnummer", "gemeente", "gsm", "email", "prive_email",
    "lpv1_type", "lpv1_naam", "lpv1_voornaam", "lpv1_geslacht", "lpv1_gsm", "lpv1_email",
    "lpv2_type", "lpv2_naam", "lpv2_voornaam", "lpv2_geslacht", "lpv2_gsm", "lpv2_email",
    "leerlingnummer", "middag", "inschrijvingsdatum", "klascode", "klasnummer", "instellingsnummer", "schooljaar", "foto", "foto_id"
]


Subgroepen_keys = {
    "Klascode": "klascode", "Instelnr": "instellingsnummer", "Klastitularis": "klastitularis"
}


klas_required_fields = [
    "instellingsnummer", "klascode", "klasgroepcode", "administratievecode", "klastitularis", "schooljaar"
]


filter_school = {
    "no_klasprefix": {"instelling": ["30569", "30593"], "deelschool": False},
    "csu": {"instelling": ["30569", "30593"], "klasprefix": ["1", "2", "3", "4", "5", "6", "7", "O"], "deelschool": False},
    "sum": {"instelling": ["30569", "30593"], "klasprefix": ["1", "2"], "deelschool": True},
    "sul": {"instelling": ["30593"], "klasprefix": ["3", "4", "5", "6", "O"], "deelschool": True},
    "sui": {"instelling": ["30569"], "klasprefix": ["3", "4", "5", "6", "7"], "deelschool": True},
    "testklassen": {"instelling": ["30569", "30593"], "klasprefix": ["T"], "deelschool": True}
}


def __check_if_can_delete_in_july_august():
    now_month = datetime.datetime.now().month
    if now_month == 7 or now_month == 8:
        return msettings.get_configuration_setting("cron-delete-july-august")
    return True


def __students_get_from_informat_raw(topic, item_name, filter_on, replace_keys=None, force_list=None):
    try:
        out = []
        url = f'{flask_app.config["INFORMAT_URL"]}/{topic}'
        params = {"login": flask_app.config["INFORMAT_USERNAME"], "paswoord": flask_app.config["INFORMAT_PASSWORD"],
                  "hoofdstructuur": ""}
        today = datetime.date.today()
        start_schooljaar = datetime.date(int(mutils.get_current_schoolyear()), 9, 1)
        stop_schooljaar = datetime.date(int(mutils.get_current_schoolyear()) + 1, 6, 30)
        if today < start_schooljaar:
            referentiedatum = start_schooljaar.strftime("%d-%m-%Y")
        elif today > stop_schooljaar:
            referentiedatum = stop_schooljaar.strftime("%d-%m-%Y")
        else:
            referentiedatum = today.strftime("%d-%m-%Y")
        params["schooljaar"] = mutils.get_current_schoolyear(format=2)
        params["referentiedatum"] = referentiedatum
        params["gewijzigdSinds"] = "1-1-2010"
        for instelling in filter_school[filter_on]["instelling"]:
            params["instelnr"] = instelling
            xml_data = requests.get(url=url, params=params).content
            log.info(f"from Informat, {url}, {params['instelnr']}, {params['schooljaar']}, {params['referentiedatum']}, {params['gewijzigdSinds']}")
            if replace_keys:
                for k, v in replace_keys.items():
                    xml_data = xml_data.replace(bytes(f"<{k}>", "utf-8"), bytes(f"<{v}>", "utf-8"))
                    xml_data = xml_data.replace(bytes(f"</{k}>", "utf-8"), bytes(f"</{v}>", "utf-8"))
            data = xmltodict.parse(xml_data, force_list=force_list)[f"ArrayOf{item_name[0].upper() + item_name[1::]}"]
            if item_name in data:
                data = data[item_name]
                if not isinstance(data, list):
                    data = [data]
                if "klasprefix" in filter_school[filter_on]:
                    data = [d for d in data if d["klascode"][0] in filter_school[filter_on]["klasprefix"]]
                out += data
        return out
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return []


def __students_get_from_informat(filter_on):
    try:
        lln = __students_get_from_informat_raw("Lln", "wsInschrijving", filter_on, STUDENT_MAP_I_Lln2DB_KEYS)
        lln = [l for l in lln if l["inschrijvingsdatum"] != l["einddatum"]]
        if not lln:
            return []
        lln_extra = __students_get_from_informat_raw("LlnExtra", "wsLeerling", "no_klasprefix", STUDENT_MAP_I_LlnExtra2DB_KEYS)
        lln_extra_cache = {l["pointer"]: l for l in lln_extra}
        relaties = __students_get_from_informat_raw("Relaties", "WsRelaties", "no_klasprefix", force_list={"Relatie"})
        relaties_cache = {r["PPersoon"]: r for r in relaties}
        adressen = __students_get_from_informat_raw("Adressen", "wsAdres", "no_klasprefix", force_list={"wsAdres"})
        addressen_cache = {a["p_persoon"]: a for a in adressen if a["Domicilie"] == "1"}
        for l in lln:
            leerlingnummer = l["leerlingnummer"]
            if leerlingnummer in lln_extra_cache:
                l.update(lln_extra_cache[leerlingnummer])
            if leerlingnummer in relaties_cache:
                lpv = [None] * 3
                for relatie in relaties_cache[leerlingnummer]["Relaties"]["Relatie"]:
                    if "Lpv" in relatie:
                        lpv[int(relatie["Lpv"])] = relatie
                for i in range(1, 3):
                    if lpv[i]:
                        l[f"lpv{i}_type"] = "Begeleider" if lpv[i]["Type"] == "trajectbegeleider" else lpv[i]["Type"]
                        l[f"lpv{i}_naam"] = lpv[i]["Naam"]
                        l[f"lpv{i}_voornaam"] = lpv[i]["Voornaam"]
                        l[f"lpv{i}_geslacht"] = lpv[i]["Geslacht"]
                        l[f"lpv{i}_PRelatie"] = lpv[i]["PRelatie"] + lpv[i]["Type"]
                    else:
                        l[f"lpv{i}_type"] = ""
                        l[f"lpv{i}_naam"] = ""
                        l[f"lpv{i}_voornaam"] = ""
                        l[f"lpv{i}_geslacht"] = ""
            if leerlingnummer in addressen_cache:
                adres = addressen_cache[leerlingnummer]
                l["roepnaam"] = adres["nickname"]
                l["straat"] = adres["straat"]
                l["huisnummer"] = adres["nr"]
                l["busnummer"] = adres["dombus"]
                l["postnummer"] = adres["dlpostnr"]
                l["gemeente"] = adres["dlgem"]
            else:
                log.error(f'{sys._getframe().f_code.co_name}: {l["leerlingnummer"]}, {l["naam"]} {l["voornaam"]} does not have an address')

            if "prive_email" not in l:
                l["prive_email"] = ""
        comnummers_relatie = __students_get_from_informat_raw("ComnummersRelatie", "WsComnummers", "no_klasprefix", force_list={"Comnr"})
        comnr_relatie_cache = {comnr["PRelatie"] + comnr["Type"]: comnr for comnummers in comnummers_relatie for comnr in comnummers["Comnrs"]["Comnr"] if "PRelatie" in comnr and comnr["Soort"] in ["Gsm"]}
        comnr_ppersoon_cache = {comnummers["PPersoon"]: comnr for comnummers in comnummers_relatie for comnr in comnummers["Comnrs"]["Comnr"] if comnr["Type"] == "Eigen"}
        email_relatie = __students_get_from_informat_raw("EmailRelatie", "WsEmailadressen", "no_klasprefix", force_list={"Email"})
        email_relatie_cache = {email["PRelatie"] + email["Type"]: email for email_adressen in email_relatie for email in email_adressen["Emails"]["Email"] if "PRelatie" in email}
        email_ppersoon_cache = {email_adressen["PPersoon"]: email for email_adressen in email_relatie for email in email_adressen["Emails"]["Email"] if email["Type"] in ["Privé", "Eigen"]}
        for l in lln:
            for i in range(1, 3):
                if f"lpv{i}_PRelatie" in l and l[f"lpv{i}_PRelatie"] in email_relatie_cache:
                    l[f"lpv{i}_email"] = email_relatie_cache[l[f"lpv{i}_PRelatie"]]["Adres"]
                else:
                    l[f"lpv{i}_email"] = ""
                if f"lpv{i}_PRelatie" in l and l[f"lpv{i}_PRelatie"] in comnr_relatie_cache:
                    l[f"lpv{i}_gsm"] = comnr_relatie_cache[l[f"lpv{i}_PRelatie"]]["Nummer"]
                else:
                    l[f"lpv{i}_gsm"] = ""
            if l["leerlingnummer"] in comnr_ppersoon_cache:
                l["gsm"] = comnr_ppersoon_cache[l["leerlingnummer"]]["Nummer"]
            if l["leerlingnummer"] in email_ppersoon_cache:
                l["prive_email"] = email_ppersoon_cache[l["leerlingnummer"]]["Adres"]
        return lln
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return []


def __klas_get_from_informat(filter_on):
    try:
        subgroepen = __students_get_from_informat_raw("Subgroepen", "wsKlasgroep", filter_on, Subgroepen_keys)

        klas_cache = {k["klascode"]: k for k in subgroepen if k["Groeptype"] == "0"}
        for code, klas in klas_cache.items():
            if int(klas["Graad"]) > 1 and klas["instellingsnummer"] == "030569" or len(code) == 2 or code == "OKAN":
                klas["klasgroepcode"] = ""
            else:
                klas["klasgroepcode"] = code[:2]
        return list(klas_cache.values())
        klasgroep_cache = {k["p_persoon"]: k for k in subgroepen if k["Groeptype"] == "1"}
        for klas in subgroepen:
            if klas["klascode"] not in klas_cache and klas["Groeptype"] == "0":
                klas_cache[klas["klascode"]] = klas
                if klas["p_persoon"] in klasgroep_cache:
                    klas["klasgroepcode"] = klasgroep_cache[klas["p_persoon"]]["klascode"]
                    if "klastitularis" in klasgroep_cache[klas["p_persoon"]]:
                        klas["klastitularis"] = klasgroep_cache[klas["p_persoon"]]["klastitularis"]
        klas_cache = {i["klascode"]: i for i  in klas_cache.values() if "klasgroepcode" in i}
        return klas_cache
        # klassen = list(klas_cache.values())
        # return klassen
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return []


def __students_get_from_database(filter_on):
    try:
        out = []
        for instelling in filter_school[filter_on]["instelling"]:
            for klasprefix in filter_school[filter_on]["klasprefix"]:
                students = mstudent.student_get_m([("instellingsnummer", "=", instelling), ("klascode", "like", f"{klasprefix}%")])
                if students:
                    out += students
        return out
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return []


def __klas_get_from_database(filter_on):
    try:
        out = []
        for instelling in filter_school[filter_on]["instelling"]:
            for klasprefix in filter_school[filter_on]["klasprefix"]:
                klassen = mklas.klas_get_m([("instellingsnummer", "=", instelling), ("klascode", "like", f"{klasprefix}%")])
                if klassen:
                    out += klassen
        return out
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return []


def student_from_informat_to_database(settings=None):
    try:
        log.info(f'start student import from informat, with settings: {settings}')
        max = settings["max"] if settings and "max" in settings else 0
        # prevent accidental import from informat
        # log.error("NO IMPORT FROM informat ALLOWED")
        # return
        if settings and "sync-school" in settings:
            filter_on = settings["sync-school"]
        else:
            filter_on = "csu"

        informat_students = __students_get_from_informat(filter_on)
        if not informat_students:
            log.info(f'{sys._getframe().f_code.co_name}: No students to import, abort...')
            return
        schooljaar = int(mutils.get_current_schoolyear(format=1))
        # (Photo.id, Photo.filename, Photo.new, Photo.changed, Photo.delete, func.octet_length(Photo.photo))
        saved_photos = {p[1]: p[0] for p in mphoto.photo_get_size_all()}
        # students = __students_get_from_database(filter_on)
        students = mstudent.student_get_m()
        db_students = {s.leerlingnummer: s for s in students} if students else {}
        new_list = []
        changed_list = []
        flag_list = []
        processed_list = []  # to detect double entries in the informat-import
        administratievecode_cache = {}
        nbr_deleted = 0
        nbr_processed = 0
        # clean up, remove leading and trailing spaces, convert datetime-string to datetime
        for informat_student in informat_students:
            if informat_student["voorlopig"] == "1":
                log.info(f"Student is voorlopig, skip {informat_student['leerlingnummer']}, {informat_student['naam']} {informat_student['voornaam']}")
                continue
            if informat_student["leerlingnummer"] in processed_list:
                log.info(f"Student already imported {informat_student['leerlingnummer']}, {informat_student['naam']} {informat_student['voornaam']}")
                continue
            if informat_student["administratievecode"] not in administratievecode_cache:
                administratievecode_cache[informat_student["klascode"]] = informat_student["administratievecode"]
            informat_student["geboortedatum"] = datetime.datetime.strptime(informat_student["geboortedatum"], "%Y-%m-%d").date()
            informat_student["inschrijvingsdatum"] = datetime.datetime.strptime(informat_student["inschrijvingsdatum"], "%Y-%m-%d").date()
            informat_student["schooljaar"] = schooljaar
            informat_student["instellingsnummer"] = informat_student["instellingsnummer"][1::] #remove leading 0
            if "roepnaam" in informat_student:
                informat_student["roepnaam"] = informat_student["roepnaam"][len(informat_student["naam"])+1::].strip()
            else:
                informat_student["roepnaam"] = informat_student["voornaam"]

            # if informat_student["roepnaam"] != informat_student["voornaam"]:
            #     log.info(f"ROEPNAAM, {informat_student['naam']} {informat_student['voornaam']}, {informat_student['roepnaam']}")

            if f"{informat_student['leerlingnummer']}.jpg" in saved_photos:
                informat_student['foto_id'] = saved_photos[f"{informat_student['leerlingnummer']}.jpg"]
                informat_student['foto'] = f"{informat_student['leerlingnummer']}.jpg"

            # clean up some fields
            for k, v in informat_student.items():
                if k == "middag":
                    if v is None:
                        v = ""
                    v = v.replace(" ", "-")
                    informat_student[k] = v
                    continue
                if k in ["klasnummer"]:
                    informat_student[k] = -1 if v is None else int(v)
                    continue
                if v is None:
                    informat_student[k] = ""
                    continue

            if informat_student['leerlingnummer'] in db_students:
                # student already exists in database
                # check if a student has updated properties
                changed_properties = []
                db_student = db_students[informat_student['leerlingnummer']]
                for k in STUDENT_CHANGED_PROPERTIES_MASK:
                    if k in informat_student and informat_student[k] != getattr(db_student, k):
                        changed_properties.append(k)
                if changed_properties:
                    changed_properties.extend(['delete', 'new'])  # student already present, but has changed properties
                    informat_student.update({'changed': changed_properties, 'student': db_student, 'delete': False, 'new': False})
                    changed_list.append(informat_student)
                    log.info(f'{sys._getframe().f_code.co_name}: updated, {db_student.leerlingnummer}, {db_student.naam} {db_student.voornaam}, {changed_properties}')
                del (db_students[informat_student['leerlingnummer']])
            else:
                # student not present in database, i.e. a new student
                informat_student['email'] = f"{informat_student['voornaam'].translate(normalize_letters).lower()}.{informat_student['naam'].translate(normalize_letters).lower()}@lln.campussintursula.be"
                informat_student['username'] = f's{informat_student["leerlingnummer"]}'
                informat_student["status"] = json.dumps(mstudent.Student.get_statuses())
                new_list.append(informat_student)  # new student
                log.info(f'{sys._getframe().f_code.co_name}: new, {informat_student["leerlingnummer"]}, {informat_student["naam"]} {informat_student["voornaam"]}, {informat_student["username"]}, {informat_student["email"]}')
            processed_list.append(informat_student["leerlingnummer"])
            nbr_processed += 1
            if max > 0 and nbr_processed >= max:
                break
        # at this point, saved_students contains the students not present in the informat-import, i.e. the deleted students
        # Normally, in July and August it is not possible to delete students from the database.  During these months, students are being transferred to the new schoolyear on a daily basis
        # So, imports do not contain all students yet.
        # In addition, when only a deelschool is imported from Informat and db_students contains ALL students (not only from the deelschool), then a lot of students are going to be deleted.  So,
        # skip if importing a deelschool.
        if __check_if_can_delete_in_july_august():
            if "deelschool" in filter_school[filter_on] and not filter_school[filter_on]["deelschool"]:
                for k, v in db_students.items():
                    if not v.delete:
                        flag_list.append({'changed': '', 'delete': True, 'new': False, 'student': v})
                        log.info(f'{sys._getframe().f_code.co_name}: delete, {v.leerlingnummer}, {v.naam} {v.voornaam}')
                        nbr_deleted += 1
        # add the new students to the database
        mstudent.student_add_m(new_list)
        # update the changed properties of the students
        mstudent.student_change_m(changed_list)
        # deleted students and students that are not changed, set the flags correctly
        mstudent.student_flag_m(flag_list)
        log.info(f'{sys._getframe().f_code.co_name}, Studenten processed {nbr_processed}, new {len(new_list)}, updated {len(changed_list)}, deleted {nbr_deleted}')

        #process klassen
        log.info(f'start klas import from informat, with settings: {settings}')
        informat_klassen = __klas_get_from_informat(filter_on)
        klassen = __klas_get_from_database(filter_on)
        db_klassen = {k.klascode: k for k in klassen} if klassen else {}
        db_staff = mstaff.staff_get_m()
        staff_cache = {f"{s.naam} {s.voornaam}": s.code for s in db_staff} #required to translate titularis-naam-voornaam to code
        new_list = []
        changed_list = []
        flag_list = []
        processed_list = []  # to detect double entries in the informat-import
        nbr_deleted = 0
        nbr_processed = 0
        for informat_klas in informat_klassen:
            if informat_klas["klascode"] not in administratievecode_cache:
                log.error(f"Empty klas {informat_klas['klascode']}")
                continue
            informat_klas["instellingsnummer"] = informat_klas["instellingsnummer"][1::] #remove leading 0
            informat_klas["administratievecode"] = administratievecode_cache[informat_klas["klascode"]]
            informat_klas["schooljaar"] = schooljaar
            # if "klasgroepcode" not in informat_klas:
            #     informat_klas["klasgroepcode"] = ""
            if "klastitularis" in informat_klas: # translate the titularis name to its code
                teachers = []
                for teacher in informat_klas["klastitularis"].split(","):
                    if teacher.strip() in staff_cache:
                        teachers.append(staff_cache[teacher.strip()])
                    else:
                        log.error(f'{sys._getframe().f_code.co_name}: Klastitularis not found in SDH, {teacher}')
                informat_klas["klastitularis"] = json.dumps(teachers)
            else:
                informat_klas["klastitularis"] = "[]"
            if informat_klas["klascode"] in db_klassen:
                # klas already exists in database.  Check for updates
                db_klas = db_klassen[informat_klas["klascode"]]
                changed_properties = []

                for k, v in informat_klas.items():
                    if k in klas_required_fields and hasattr(db_klas, k) and v != getattr(db_klas, k):
                        changed_properties.append(k)
                if changed_properties:
                    changed_properties.extend(['delete', 'new'])  # klas already present, but has changed properties
                    informat_klas.update({'changed': changed_properties, 'klas': db_klas, 'delete': False, 'new': False})
                    changed_list.append(informat_klas)
                    log.info(f'{sys._getframe().f_code.co_name}: updated, {db_klas.klascode}, {db_klas.klasgroepcode}, {changed_properties}')
                else:
                    flag_list.append({'changed': '', 'delete': False, 'new': False, 'klas': db_klas})  # klas already present, no change
                del (db_klassen[informat_klas['klascode']])
            else:
                # klas not present in database, i.e. a new klas
                new_list.append(informat_klas)  # new klas
                log.info(f'{sys._getframe().f_code.co_name}: new, {informat_klas["klascode"]}, {informat_klas["klasgroepcode"]}')
            processed_list.append(informat_klas["klascode"])
            nbr_processed += 1
            if max > 0 and nbr_processed >= max:
                break
        # at this point, saved_klas contains the students not present in the informat-import, i.e. the deleted students
        if __check_if_can_delete_in_july_august():
            if "deelschool" in filter_school[filter_on] and not filter_school[filter_on]["deelschool"]:
                for k, v in db_klassen.items():
                    if not v.delete:
                        flag_list.append({'changed': '', 'delete': True, 'new': False, 'klas': v})
                        log.info(f'{sys._getframe().f_code.co_name}: delete, {v.klascode}, {v.klasgroepcode}')
                        nbr_deleted += 1
        # add the new klassen to the database
        mklas.klas_add_m(new_list)
        # update the changed properties of the klassen
        mklas.klas_change_m(changed_list, overwrite=True) # previous changes are lost
        # deleted klassen and klassen that are not changed, set the flags correctly
        mklas.klas_flag_m(flag_list)
        log.info(f'{sys._getframe().f_code.co_name}, Klassen processed {nbr_processed}, new {len(new_list)}, updated {len(changed_list)}, deleted {nbr_deleted}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


STAFF_MAP_I2DB_KEYS = {
    "Voornaam": "voornaam",
    "Naam": "naam",
    "Rijksregnr": "rijksregisternummer",
    "Stamnummer": "stamboeknummer",
    "Geslacht": "geslacht",
    "Geboortedatum": "geboortedatum",
    "Geboorteplaats": "geboorteplaats",
    "Prive_email": "prive_email",
    "School_email": "email",
    "Instelnr": "instellingsnummer",
}


def __staff_get_from_informat_raw(topic, item_name, replace_keys=None, force_list=None):
    try:
        out = []
        url = f'{flask_app.config["INFORMAT_URL"]}/{topic}'
        params = {"login": flask_app.config["INFORMAT_USERNAME"], "paswoord": flask_app.config["INFORMAT_PASSWORD"]}
        params["schooljaar"] = mutils.get_current_schoolyear(format=2)
        params["personeelsgroep_is_een_optie"] = ""
        for instelling in ["30569", "30593"]:
            params["instelnr"] = instelling
            xml_data = requests.get(url=url, params=params).content
            log.info(f"from Informat, {url}, {params['instelnr']}, {params['schooljaar']}")
            if replace_keys:
                for k, v in replace_keys.items():
                    xml_data = xml_data.replace(bytes(f"<{k}", "utf-8"), bytes(f"<{v}", "utf-8"))
                    xml_data = xml_data.replace(bytes(f"{k}>", "utf-8"), bytes(f"{v}>", "utf-8"))
            data = xmltodict.parse(xml_data, force_list=force_list)[f"ArrayOf{item_name[0].upper() + item_name[1::]}"]
            if item_name in data:
                data = data[item_name]
                if not isinstance(data, list):
                    data = [data]
                out += data
        return out
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e, xml_data}')
        return []


def staff_from_informat_to_database(local_file=None, max=0):
    try:
        log.info('start staff import from informat')
        informat_staffs = __staff_get_from_informat_raw("Leerkrachten", "wsPersoneelslid", STAFF_MAP_I2DB_KEYS)
        staff_vrijevelden = __staff_get_from_informat_raw("LeerkrachtenVrijevelden", "wsPersoneelVrijVeld")
        vrijevelden_cache = {s["pPersoon"]: s for s in staff_vrijevelden if s["OmschrijvingVrijVeld"] == "CODE"}
        for informat_staff in informat_staffs:
            if informat_staff["p_persoon"] in vrijevelden_cache:
                informat_staff["code"] = vrijevelden_cache[informat_staff["p_persoon"]]["WaardeVrijVeld"]

        db_staff = mstaff.staff_get_m()
        staff_in_db = {s.code: s for s in db_staff}
        new_list = []
        changed_list = []
        flag_list = []
        already_processed = []
        nbr_deleted = 0
        nbr_processed = 0

        # massage the imported data so that it fits the database.
        # for each staff-member in the import, check if it's new or changed
        for informat_staff in informat_staffs:
            #skip double or inactive items
            if "code" not in informat_staff or informat_staff['code'] in already_processed or informat_staff["Actief"] == "N":
                continue

            informat_staff["geboortedatum"] = datetime.datetime.strptime(informat_staff["geboortedatum"], "%d.%m.%Y").date()
            informat_staff["geslacht"] = "V" if informat_staff["geslacht"] == "2" else "M"
            if not informat_staff["prive_email"]:
                informat_staff["prive_email"] = ""
            if not informat_staff["email"]:
                informat_staff["email"] = ""

            if 'campussintursula.be' in informat_staff['email']:
                email = informat_staff['email']
            elif 'campussintursula.be' in informat_staff['prive_email']:
                email = informat_staff['prive_email']
            else:
                email = ""
            if 'campussintursula.be' not in informat_staff['email'] and informat_staff["email"] != "":
                prive_email = informat_staff['email']
            elif 'campussintursula.be' not in informat_staff['prive_email'] and informat_staff['prive_email'] != "":
                prive_email = informat_staff['prive_email']
            else:
                prive_email = ""
            if email != "":
                informat_staff['email'] = email
            else:
                informat_staff['email'] = f"{informat_staff['voornaam'].translate(normalize_letters).lower()}.{informat_staff['naam'].translate(normalize_letters).lower()}@campussintursula.be"
            informat_staff["prive_email"] = prive_email

            if informat_staff['code'] in staff_in_db:
                # staff-member already exists in database, check if a staff-member has updated properties
                changed_properties = []
                db_staff = staff_in_db[informat_staff['code']]
                for k, v in informat_staff.items():
                    if v is None:
                        v = ""
                    if hasattr(db_staff, k) and v != getattr(db_staff, k):
                        changed_properties.append(k)
                # if the naam or voornaam changes AND the email is already set in the database THEN ignore the new email (will cause confusion)
                if "email" in changed_properties and db_staff.email != "":
                    changed_properties.remove("email")
                if changed_properties:
                    log.info(f"UPDATE {informat_staff['code']}, {informat_staff['naam']} {informat_staff['voornaam']}, {changed_properties}")
                    changed_properties.extend(['delete', 'new'])  # staff-member already present, but has changed properties
                    informat_staff.update({'changed': changed_properties, 'staff': db_staff, 'delete': False, 'new': False})
                    changed_list.append(informat_staff)
                else:
                    flag_list.append({'changed': '', 'delete': False, 'new': False, 'staff': db_staff}) # staff already present, no change
                del(staff_in_db[informat_staff['code']])
            else:
                # staff-member not present in database, i.e. a new staff-member
                log.info(f"NEW {informat_staff['code']}, {informat_staff['naam']} {informat_staff['voornaam']}")
                new_list.append(informat_staff)  # new staff-mmeber
            already_processed.append(informat_staff['code'])
            nbr_processed += 1
            if max > 0 and nbr_processed >= max:
                break

        # at this point, staff_in_db contains the staff-member not present in the informat-import, i.e. the deleted staff-members
        for k, v in staff_in_db.items():
            if not v.delete and v.stamboeknummer != "":
                log.info(f"DELETED {v.code} {v.naam} {v.voornaam}")
                flag_list.append({'changed': '', 'delete': True, 'new': False, 'staff': v})
                nbr_deleted += 1
        # add the new staff-members to the database
        mstaff.staff_add_m(new_list)
        # update the changed properties of the staff-members
        mstaff.staff_update_m(changed_list, overwrite=True) # previous changes are lost
        # deleted staff-members and staff-members that are not changed, set the flags correctly
        mstaff.staff_flag_m(flag_list)
        log.info(f'{sys._getframe().f_code.co_name}, processed {nbr_processed}, new {len(new_list)}, updated {len(changed_list)}, deleted {nbr_deleted}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}, {e}')


def cron_task_informat_get_student(opaque=None):
    student_from_informat_to_database(opaque)


def cron_task_informat_get_staff(opaque=None):
    staff_from_informat_to_database()



