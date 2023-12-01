from app.data import group as mgroup, klas as mklas, student as mstudent, staff as mstaff
from app.application.formio import iterate_components_cb
from app.data.entra import entra
import datetime, json

#logging on file level
import logging, sys
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def get_types():
    try:
        types = [v for k, v in dict(mgroup.Group.Types.__dict__).items() if not k.startswith("__")]
        return types
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return []


############## formio #########################
def form_update_cb(component, opaque):
    try:
        if component and "key" in component:
            if "update-properties" in opaque and component["key"] in opaque["update-properties"]:
                for property in opaque["update-properties"][component["key"]]:
                    component[property["name"]] = property["value"]
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def form_prepare_new_team(form):
    try:
        db_klassen = mklas.klas_get_m()
        klassen = sorted(list({k.klascode for k in db_klassen}))
        klas_choices = {"values": [{"value": k, "label": k} for k in klassen]}
        klasgroepen = sorted(list({k.klasgroepcode for k in db_klassen}))
        klasgroep_choices = {"values": [{"value": k, "label": k} for k in klasgroepen]}
        form_update = {"update-properties": {"klassen": [{"name": "data", "value": klas_choices}], "klasgroepen": [{"name": "data", "value": klasgroep_choices}]}}
        iterate_components_cb(form, form_update_cb, form_update)
        return form
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


############ API #########
def api_team_add(data):
    try:
        name = mgroup.Group.get_cc_display_name(data["groepsnaam"])
        db_cc_team = mgroup.group_get(("display_name", "=", name))
        if not db_cc_team:
            db_klassen = mklas.klas_get_m()
            klassen_cache = {k.klascode: k.klasgroepcode for k in db_klassen}
            klassen = data["klassen"]
            klasgroepen = data["klasgroepen"]
            klassen = [k for k in klassen if klassen_cache[k] not in klasgroepen]
            db_studenten = mstudent.student_get_m()
            members = [s.entra_id for s in db_studenten if s.klascode in klassen]
            members += [s.entra_id for s in db_studenten if klassen_cache[s.klascode] in klasgroepen]
            members = list(set(members))
            db_staff = mstaff.staff_get_m()
            owners = [s.entra_id for s in db_staff]
            data = {
                "name": name,
                "description": mgroup.Group.get_cc_description(data["groepsnaam"]),
                "owners": owners,
                "members": members
            }
            team_id = entra.create_team_with_members(data)
            if team_id:
                new_cc_team = {"entra_id": team_id, "display_name": data["name"], "description": data["description"], "members": json.dumps(members), "created": datetime.datetime.now(), "type": mgroup.Group.Types.cc_man,
                                "owners": json.dumps(owners), "klassen": json.dumps({"klassen": klassen, "klasgroepen": klasgroepen})}
                mgroup.group_add(new_cc_team)
                return {"status": True, "data": f'Nieuw team, {data["name"]}, {klassen + klasgroepen}'}
            return {"status": False, "data": f'Onbekende fout, waarschuw administrator'}
        return {"status": False, "data": f'Team {name} bestaat al'}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        log.error(data)
        return {"status": False, "data": f'fout, {e}'}


############ datatables: group overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for obj in db_list:
        em = obj.to_dict()
        em.update({
            'row_action': obj.id,
            'DT_RowId': obj.id,
            "display_name": f'<a href="https://entra.microsoft.com/#view/Microsoft_AAD_IAM/GroupDetailsMenuBlade/~/Overview/groupId/{em["entra_id"]}/menuId/" target="_blank">{em["display_name"]}</a>'
        })
        out.append(em)
    return total_count, filtered_count, out


def post_sql_order(l, on, direction):
    return sorted(l, key=lambda x: x[on], reverse=direction=="desc")
