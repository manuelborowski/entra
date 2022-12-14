import random, string, sys, datetime
from app.data import utils as mutils, models as mmodels
from app import log


def datetime_to_dutch_datetime_string(date):
    return mutils.datetime_to_dutch_datetime_string(date)


def create_random_string(len=32):
    return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(len))


# fields=geboortedatum,geboorteplaats,voornaam&filters=geboorteplaats=wilrijk,-voornaam=joren
# fields are the properties request.  If not present, all properties are returned
# filters are applied on the database query; only entries where the given key matches the entry-property will be returned.
# A key (e.g. voornaam) preceded with a '-' will return entries where the key does not match the entry-property.
def api_process_options(options):
    try:
        fields = options['fields'].split(',') if 'fields' in options else []
        filters = {}
        if 'filters' in options:
            for filter in options['filters'].split(','):
                k_v = filter.split('=')
                filters[k_v[0]] = k_v[1]
        return fields, filters
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": True, "data": e}


# generic function to retrieve model data (from the database)
# model is the model reauired
# options is a string with fields and filters (see above)
def api_get_model_data(model, options=None):
    try:
        fields, filters = api_process_options(options)
        items = mmodels.get_multiple(model, data=filters, fields=fields)
        if fields:
            # if only a limited number of properties is required, it is possible that some properties must be converted to a string (e.g. datetime and date) because these cannot be
            # serialized to json
            field_conversion = []
            conversion_required = False
            for f in fields:
                if getattr(model, f).expression.type.python_type == datetime.date:
                    field_conversion.append(lambda x: x.strftime(model.date_format))
                    conversion_required = True
                elif getattr(model, f).expression.type.python_type == datetime.datetime:
                    field_conversion.append(lambda x: x.strftime(model.datetime_format))
                    conversion_required = True
                else:
                    field_conversion.append(lambda x: x)
            if conversion_required:
                out = []
                for item in items:
                    converted_fields = [ field_conversion[i](f) for i, f in enumerate(item)]
                    out.append(dict(zip(fields, converted_fields)))
            else:
                out = [dict(zip(fields, s)) for s in items]
        else:
            out = [s.to_dict() for s in items]
        return {"status": True, "data": out}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": True, "data": e}


# If the roepnaam is filled in and it is different from the voornaam, then the roepnaam is used
def get_student_voornaam(student):
    if student.roepnaam != '' and student.roepnaam != student.voornaam:
        return student.roepnaam
    return student.voornaam


def deepcopy(table):
    if type(table) == dict:
        out = {}
        for k, v in table.items():
            if type(v) == list or type(v) == dict:
                out[k] = deepcopy(v)
            else:
                out[k] = v
    elif type(table) == list:
        out = []
        for i in table:
            if type(i) == list or type(i) == dict:
                out.append(deepcopy(i))
            else:
                out.append(i)
    else:
        out = table
    return out