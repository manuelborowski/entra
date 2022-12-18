from flask import request
from sqlalchemy import or_, desc
import time, json
from app import data

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


######################################################################################################
###                                       Build a generic filter
######################################################################################################

def check_date_in_form(date_key, form):
    if date_key in form and form[date_key] != '':
        try:
            time.strptime(form[date_key].strip(), '%d-%M-%Y')
            return form[date_key].strip()
        except Exception as e:
            data.utils.raise_error('Verkeerd datumformaat, moet in de vorm zijn: d-m-y', e)
    return ''


def check_value_in_form(value_key, form):
    if value_key in form and form[value_key] != '':
        try:
            float(form[value_key])
            return form[value_key]
        except Exception as e:
            data.utils.raise_error('Verkeerde getal notatie', e)
    return ''


def check_string_in_form(value_key, form):
    if value_key in form and form[value_key] != '':
        try:
            str(form[value_key])
            return form[value_key]
        except Exception as e:
            data.utils.raise_error('Verkeerde tekst notatie', e)
    return None


def prepare_data_for_ajax(table_config, paginate=True):
    try:
        template = table_config.template

        sql_query = table_config.pre_sql_query()

        total_count = sql_query.count()

        filter = None
        if 'filter' in request.values:
            filter = json.loads(request.values['filter'])
            sql_query = table_config.pre_sql_filter(sql_query, filter)

        search_value = check_string_in_form('search[value]', request.values)
        if search_value:
            search_constraints = table_config.pre_sql_search(f"%{search_value}%")
            if search_constraints:
                sql_query = sql_query.filter(or_(*search_constraints))

        filtered_count = sql_query.count()

        order_on = order_direction = None
        order_column_nbr = int(check_value_in_form('order[0][column]', request.values))
        if "orderable" in template[order_column_nbr] and template[order_column_nbr]["orderable"]:
            order_on = template[order_column_nbr]['data']
            order_direction = check_string_in_form('order[0][dir]', request.values)
        if order_on and "post_order" not in template[order_column_nbr]:
            sql_query = table_config.pre_sql_order(sql_query, order_on, order_direction)

        paginate_start = paginate_length = None
        if paginate:
            paginate_start = check_value_in_form('start', request.values)
            if paginate_start:
                paginate_length = int(check_value_in_form('length', request.values))
                paginate_start = int(paginate_start)

        if paginate and paginate_length > 0 and "post_order" not in template[order_column_nbr]:
            sql_query = table_config.pre_sql_paginate(sql_query, paginate_start, paginate_start + paginate_length)

        db_data = sql_query.all()

        total_count, filtered_count, formatted_data = table_config.format_data(db_data, total_count, filtered_count)

        if filter:
            filtered_count, formatted_data = table_config.post_sql_filter(formatted_data, filter, filtered_count)

        if search_value:
            filtered_count, formatted_data = table_config.post_sql_search(formatted_data, search_value, filtered_count)

        if order_on and "post_order" in template[order_column_nbr]:
            formatted_data = table_config.post_sql_order(formatted_data, order_on, order_direction)

        if paginate and paginate_length > 0 and "post_order" in template[order_column_nbr]:
            formatted_data = table_config.post_sql_paginate(formatted_data, paginate_start, paginate_start + paginate_length)

    except Exception as e:
        log.error(f'could not prepare data for ajax: {e}')
        data.utils.raise_error('prepare_data_for_ajax', e)

    return formatted_data, total_count, filtered_count
