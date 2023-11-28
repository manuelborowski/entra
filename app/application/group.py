from app.data import group as mgroup

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


############ datatables: group overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for obj in db_list:
        em = obj.to_dict()
        em["display_name"] = f'<a href="https://entra.microsoft.com/#view/Microsoft_AAD_IAM/GroupDetailsMenuBlade/~/Overview/groupId/{em["entra_id"]}/menuId/" target="_blank">{em["display_name"]}</a>'
        em.update({
            'row_action': obj.id,
            'DT_RowId': obj.id
        })
        out.append(em)
    return total_count, filtered_count, out


def post_sql_order(l, on, direction):
    return sorted(l, key=lambda x: x[on], reverse=direction=="desc")
