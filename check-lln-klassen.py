import configparser, requests, xmltodict, logging.handlers, os, sys, json, datetime
from zeep import Client

config = configparser.ConfigParser()
config.read('instance/config.ini')

log = logging.getLogger("informat")
LOG_FILENAME = os.path.join(sys.path[0], f'check-lln-klassen.txt')
log_level = getattr(logging, 'INFO')
log.setLevel(log_level)
log_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=16 * 1024 * 1024, backupCount=20)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)

log.info("START check-lln-klassen")

def __get_students_from_sdh():
    res = requests.get(config["sdh"]["API_URL2"], headers={'x-api-key': config["sdh"]["API_KEY"]})
    if res.status_code == 200:
        sdh_students = res.json()
        if sdh_students['status']:
            log.info(f'{sys._getframe().f_code.co_name}, retrieved {len(sdh_students["data"])} students from SDH')
            return sdh_students["data"]
    return []


soap = Client(config["ss"]["API_URL"])

SCHOOL_TOP_GROEPEN = ["klassenstructuur-sui", "klassenstructuur-sul", "klassenstructuur-sum"]

def __ss_get_students():
    students = []
    for group in SCHOOL_TOP_GROEPEN:
        ret = soap.service.getAllAccountsExtended (config["ss"]["API_KEY"], group, "1")
        students += list(json.loads(ret))
    students = [s for s in students if s["basisrol"] == "1"] # include students (basisrol 1) only
    log.info(f'{sys._getframe().f_code.co_name}, retrieved {len(students)} students from Smartschool')
    return students


STUDENT_MAP_SS2SDH_KEYS = {
    "voornaam": "voornaam",
    "naam": "naam",
    "klascode": "klascode"
}

def compare_ss_with_sdh():
    try:
        students = __get_students_from_sdh()
        students_cache = {s["leerlingnummer"]: s for s in students}
        nbr_in_ss_not_in_sdh = 0
        nbr_mismatch = 0
        ss_students = __ss_get_students()
        for ss_student in ss_students:
            if ss_student["internnummer"] not in students_cache:
                if ss_student["status"] == "actief":
                    log.error(f"WEL in SS, NIET in SDH, {ss_student['naam']} {ss_student['voornaam']}, {ss_student['internnummer']}")
                    nbr_in_ss_not_in_sdh += 1
                continue
            klassen = [g["code"] for g in ss_student["groups"] if g["isOfficial"]]
            if len(klassen) == 1:
                ss_student["klascode"] = klassen[0]
            else:
                ss_student["klascode"] = "-"
            sdh_student = students_cache[ss_student["internnummer"]]
            mismatches = []
            for ss_k, sdh_k in STUDENT_MAP_SS2SDH_KEYS.items():
                sdh_v = sdh_student[sdh_k]
                ss_v = ss_student[ss_k]
                sdh_v = sdh_v.replace(" ", "").lower()
                ss_v = ss_v.replace(" ", "").lower()
                if sdh_v != ss_v:
                    mismatches.append(f"SDH: {sdh_k} ({sdh_v}) <> SS: {ss_k} ({ss_student[ss_k]})")
            if mismatches:
                log.error(f"MISMATCH, {ss_student['naam']} {ss_student['voornaam']}, {ss_student['internnummer']}, {', '.join(mismatches)}")
                nbr_mismatch += 1
            del(students_cache[ss_student["internnummer"]])
        for _, student in students_cache.items():
            log.error(f"WEL in SDH, NIET in SS, {student['naam']} {student['voornaam']}, {student['leerlingnummer']}")
        log.info(f"done, nbr-in-sdh-not-in-ss {len(students_cache)}, nbr-in-ss-not-in-sdh {nbr_in_ss_not_in_sdh}, nbr-mismatch {nbr_mismatch}")
    except Exception as e:
        log.info("Error:", e)


INSTELLINGEN = ["30569", "30593"]


def __students_get_from_informat_raw(topic, item_name, replace_keys=None, force_list=None):
    try:
        now =datetime.date.today()
        if now.month >= 9:
            current_schoolyear = now.year
        else:
            current_schoolyear = now.year - 1
        out = []
        url = f'{config["informat"]["INFORMAT_URL"]}/{topic}'
        params = {"login": config["informat"]["INFORMAT_USERNAME"], "paswoord": config["informat"]["INFORMAT_PASSWORD"],
                  "hoofdstructuur": ""}
        today = datetime.date.today()
        start_schooljaar = datetime.date(current_schoolyear, 9, 1)
        stop_schooljaar = datetime.date(current_schoolyear + 1, 6, 30)
        if today < start_schooljaar:
            referentiedatum = start_schooljaar.strftime("%d-%m-%Y")
        elif today > stop_schooljaar:
            referentiedatum = stop_schooljaar.strftime("%d-%m-%Y")
        else:
            referentiedatum = today.strftime("%d-%m-%Y")
        params["schooljaar"] = str(current_schoolyear) + "-" + str(current_schoolyear + 1 - 2000)
        params["referentiedatum"] = referentiedatum
        params["gewijzigdSinds"] = "1-1-2010"
        for instelling in INSTELLINGEN:
            params["instelnr"] = instelling
            xml_data = requests.get(url=url, params=params).content
            log.info(f"from Informat, {url}, {params['instelnr']}, {params['schooljaar']}, {params['referentiedatum']}, {params['gewijzigdSinds']}")
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


STUDENT_MAP_I_Lln2DB_KEYS = {
    "Voornaam": "voornaam", "Naam": "naam", "rijksregnr": "rijksregisternummer", "Stamnr_kort": "stamboeknummer",
    "p_persoon": "leerlingnummer", "begindatum": "inschrijvingsdatum", "instelnr": "instellingsnummer", "Klascode": "klascode",
    "nr_admgr": "administratievecode", "Klasnr": "klasnummer", "Levensbeschouwing": "levensbeschouwing"
}


STUDENT_MAP_I_LlnExtra2DB_KEYS = {
    "nr": "huisnummer",
    "bus": "busnummer",
    "dlpostnr": "postnummer",
    "dlgem": "gemeente",
    "GSMeigen": "gsm",
    "EmailEigen": "prive_email",
    "Fietsnummer": "middag"
}


def __students_get_from_informat():
    try:
        lln = __students_get_from_informat_raw("Lln", "wsInschrijving", STUDENT_MAP_I_Lln2DB_KEYS)
        lln = [l for l in lln if l["inschrijvingsdatum"] != l["einddatum"]]
        if not lln:
            return []
        lln_extra = __students_get_from_informat_raw("LlnExtra", "wsLeerling", STUDENT_MAP_I_LlnExtra2DB_KEYS)
        lln_extra_cache = {l["pointer"]: l for l in lln_extra}
        relaties = __students_get_from_informat_raw("Relaties", "WsRelaties", force_list={"Relatie"})
        relaties_cache = {r["PPersoon"]: r for r in relaties}
        adressen = __students_get_from_informat_raw("Adressen", "wsAdres", force_list={"wsAdres"})
        addressen_cache = {a["p_persoon"]: a for a in adressen}
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
                addressen = addressen_cache[leerlingnummer]
                if "nickname" in addressen:
                    l["roepnaam"] = addressen["nickname"]
                if "dlpostnr" in addressen:
                    l["postnummer"] = addressen["dlpostnr"]
                if "dlgem" in addressen:
                    l["gemeente"] = addressen["dlgem"]

            if "prive_email" not in l:
                l["prive_email"] = ""
        comnummers_relatie = __students_get_from_informat_raw("ComnummersRelatie", "WsComnummers", force_list={"Comnr"})
        comnr_relatie_cache = {comnr["PRelatie"] + comnr["Type"]: comnr for comnummers in comnummers_relatie for comnr in comnummers["Comnrs"]["Comnr"] if "PRelatie" in comnr and comnr["Soort"] in ["Gsm"]}
        comnr_ppersoon_cache = {comnummers["PPersoon"]: comnr for comnummers in comnummers_relatie for comnr in comnummers["Comnrs"]["Comnr"] if comnr["Type"] == "Eigen"}
        email_relatie = __students_get_from_informat_raw("EmailRelatie", "WsEmailadressen", force_list={"Email"})
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


STUDENT_MAP_I2SDH_KEYS = {
    "voornaam": "voornaam",
    "naam": "naam",
    "klascode": "klascode"
}

def compare_informat_with_sdh():
    try:
        students = __get_students_from_sdh()
        students_cache = {s["leerlingnummer"]: s for s in students}
        nbr_in_i_not_in_sdh = 0
        nbr_mismatch = 0
        processed_list = []
        i_students = __students_get_from_informat()
        for i_student in i_students:
            if i_student["voorlopig"] == "1":
                log.info(f"Student is voorlopig, skip {i_student['leerlingnummer']}, {i_student['naam']} {i_student['voornaam']}")
                continue
            if i_student["leerlingnummer"] in processed_list:
                log.error(f"Student already imported {i_student['leerlingnummer']}, {i_student['naam']} {i_student['voornaam']}")
                continue
            if i_student["leerlingnummer"] not in students_cache:
                log.error(f"WEL in INFORMAT, NIET in SDH, {i_student['naam']} {i_student['voornaam']}, {i_student['leerlingnummer']}")
                nbr_in_i_not_in_sdh += 1
                continue
            sdh_student = students_cache[i_student["leerlingnummer"]]
            mismatches = []
            for i_k, sdh_k in STUDENT_MAP_I2SDH_KEYS.items():
                sdh_v = sdh_student[sdh_k]
                i_v = i_student[i_k]
                sdh_v = sdh_v.replace(" ", "").lower()
                i_v = i_v.replace(" ", "").lower()
                if sdh_v != i_v:
                    mismatches.append(f"SDH: {sdh_k} ({sdh_v}) <> INFORMAT: {i_k} ({i_student[i_k]})")
            if mismatches:
                log.error(f"MISMATCH, {i_student['naam']} {i_student['voornaam']}, {i_student['leerlingnummer']}, {', '.join(mismatches)}")
                nbr_mismatch += 1
            del(students_cache[i_student["leerlingnummer"]])
            processed_list.append(i_student["leerlingnummer"])
        for _, student in students_cache.items():
            log.error(f"WEL in SDH, NIET in INFORMAT, {student['naam']} {student['voornaam']}, {student['leerlingnummer']}")
        log.info(f"done, nbr-in-sdh-not-in-informat {len(students_cache)}, nbr-in-informat-not-in-sdh {nbr_in_i_not_in_sdh}, nbr-mismatch {nbr_mismatch}")
    except Exception as e:
        log.info("Error:", e)


compare_ss_with_sdh()
compare_informat_with_sdh()
