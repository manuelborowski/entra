import datetime, sys
# noinspection PyUnresolvedReferences
from bleach.sanitizer import Cleaner
from app.application.util import deepcopy

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


# search, in a given hierarchical tree of components, for a component with the given 'key'
def search_component(form, key):
    components = None
    if 'components' in form:
        components = form['components']
    elif 'columns' in form:
        components = form['columns']
    if components:
        for component in components:
            if 'key' in component and component['key'] == key:
                return component
            if 'components' in component or 'columns' in component:
                found_component = search_component(component, key)
                if found_component: return found_component
    return None


# template is a formio component (with subcomponents, if needed)
# data is a list of structures.  Each entry creates a new component (from template) and the relevant properties are filled in (found via key)
def create_components(template, data):
    try:
        out = []
        for component_info in data:
            new_component = deepcopy(template)
            new_component["key"] = component_info["key"]
            for property in component_info['properties']:
                sub_component = search_component(new_component, property['key'])
                if sub_component:
                    if property['name'] == "attrs":
                        if "attrs" in sub_component:
                            for i, attr in enumerate(sub_component['attrs']):
                                if attr['attr'] in property["value"]:
                                    sub_component["attrs"][i] = {"attr": attr["attr"], "value": property["value"][attr["attr"]]}
                                    del property["value"][attr["attr"]]
                        else:
                            sub_component['attrs'] = []
                        for k, v in property["value"].items():
                            sub_component["attrs"].append({"attr": k, "value": v})
                    else:
                        sub_component[property['name']] = property['value']
            out.append(new_component)
        return out
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


#in a form, iterate over all components and execute callback for each component
def iterate_components_cb(form, cb, opaque=None):
    component_iter = iterate_components(form)
    try:
        while True:
            component = next(component_iter)
            if "key" in component:
                cb(component, opaque)
    except StopIteration as e:
        pass

# iterate over all components.
# If a component is a container (i.e. contains a list of components, such as type container or columns), iterate first over de child-components
def iterate_components(form):
    components = []
    if 'components' in form:
        components = form['components']
    elif 'columns' in form:
        components = form['columns']
    for component in components:
        yield component
        if 'components' in component or 'columns' in component or 'rows' in component:
            yield from iterate_components(component)
    if 'rows' in form:
        for row in form['rows']:
            for column in row:
                yield column
                if 'components' in column or 'columns' in column or 'rows' in column:
                    yield from iterate_components(column)


def datetimestring_to_datetime(date_in, seconds=False):
    try:
        format_string = '%d/%m/%Y %H:%M:%S' if seconds else '%d/%m/%Y %H:%M'
        date_out = datetime.datetime.strptime(date_in, format_string)
        return date_out
    except:
        return None


def datestring_to_date(date_in):
    try:
        date_out = datetime.datetime.strptime(date_in, '%d/%m/%Y')
        return date_out.date()
    except:
        return None


# formio returns:
# 2022-3-4T13:34:23+02:00 OR SOMETIMES
# 2022-3-4T13:34:23.000Z OR SOMETIMES
# 2022-3-4 OR SOMETIMES
# 4/3/2022.  WHO KNOWS WHY???
def formiodate_to_datetime(formio_date):
    split_code = '.' if '.' in formio_date else '+'
    date_time = datetime.datetime.strptime(formio_date.split(split_code)[0], '%Y-%m-%dT%H:%M:%S')
    return date_time


# formio returns:
# 2022-3-4T13:34:23+02:00 OR SOMETIMES
# 2022-3-4T13:34:23.000Z OR SOMETIMES
# 2022-3-4 OR SOMETIMES
# 4/3/2022.  WHO KNOWS WHY???
def formiodate_to_date(formio_date):
    try:
        date = datetime.datetime.strptime(formio_date.split('T')[0], "%Y-%m-%d")
    except:
        date = datetime.datetime.strptime(formio_date, "%d/%m/%Y")
    return date.date()


def date_to_datestring(date):
    string = datetime.datetime.strftime(date, '%d/%m/%Y')
    return string


def datetime_to_datetimestring(date):
    string = datetime.datetime.strftime(date, '%d/%m/%Y %H:%M')
    return string


def datetime_to_formio_datetime(date):
    string = f"{datetime.datetime.strftime(date, '%Y-%m-%dT%H:%M')}:00+01:00"
    return string


def strip_html(input):
    cleaner = Cleaner(tags=[], attributes={}, styles=[], protocols=[], strip=True, strip_comments=True, filters=None)
    return cleaner.clean(input)