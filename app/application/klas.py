from app import log
from app.data  import klas as mklas
import sys


# delete klas that is flagged delete
# reset new and changed flags
def klas_post_processing(opaque=None):
    try:
        log.info(f'{sys._getframe().f_code.co_name}: START')
        deleted_klassen = mklas.klas_get_m([("delete", "=",  True)])
        mklas.klas_delete_m(klassen=deleted_klassen)
        log.info(f"deleted {len(deleted_klassen)} klassen")
        changed_new_klassen = mklas.klas_get_m([("changed", "!", "")])
        changed_new_klassen.extend(mklas.klas_get_m([("new", "=", True)]))
        for klas in changed_new_klassen:
            mklas.klas_update(klas, {"changed": "", "new": False}, commit=False)
        mklas.commit()
        log.info(f"new, changed {len(changed_new_klassen)} klassen")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


def get_klassen_klasgroepen():
    klassen = mklas.klas_get_m()
    data = {}
    for klas in klassen:
        klasgroepcode = klas.klasgroepcode if klas.klasgroepcode != "" else klas.klascode
        if klasgroepcode in data:
            data[klasgroepcode].append(klas.klascode)
        else:
            data[klasgroepcode] = [klas.klascode]
    return data
