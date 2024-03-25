import sys, json, datetime

import app.data.models
from app import log, db
from sqlalchemy_serializer import SerializerMixin


class Group(db.Model, SerializerMixin):
    __tablename__ = 'groups'

    date_format = '%d/%m/%Y'
    datetime_format = '%d/%m/%Y %H:%M'

    class Types:
        team = "team"
        klas = "klas"
        groep = "groep"
        cc_auto = "cc-auto"
        cc_man = "cc-man"

    id = db.Column(db.Integer(), primary_key=True)
    entra_id = db.Column(db.String(256), default='')
    klassen = db.Column(db.TEXT, default='')
    description = db.Column(db.TEXT, default='')
    display_name = db.Column(db.TEXT, default='')
    owners = db.Column(db.TEXT, default='[]')
    members = db.Column(db.TEXT, default='[]')
    created = db.Column(db.DateTime, default=None)
    last_activity = db.Column(db.Date, default=None)
    type = db.Column(db.String(256), default=Types.team)
    archived = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term

    def add_owners(self, owners):
        self.owners = json.dumps(list(set(json.loads(self.owners) + [o.code for o in owners])))
        
    def del_owners(self, owners):
        if owners:
            current_owners = json.loads(self.owners)
            for owner in owners:
                if owner.code in current_owners:
                    current_owners.remove(owner.code)
            self.owners = json.dumps(current_owners)

    def add_members(self, members):
        self.members = json.dumps(list(set(json.loads(self.members) + [m.leerlingnummer for m in members])))
        
    def del_members(self, members):
        if members:
            current_members = json.loads(self.members)
            for member in members:
                if member.leerlingnummer in current_members:
                    current_members.remove(member.leerlingnummer)
            self.members = json.dumps(current_members)

    def get_staff_code(self):
        if "cc-" in self.description:
            return self.description[3]

    def get_klasgroep_code(self):
        if "cc-" in self.description:
            return self.description[5:]

    def get_cc_description(staff_code, klasgroep_code):
        return f"cc-{staff_code}-{klasgroep_code}"

    def get_cc_display_name(staff_code, klasgroep_code):
        return f"cc-{staff_code}-{klasgroep_code}"


def get_columns():
    return [p for p in dir(Group) if not p.startswith('_')]


def commit():
    return app.data.models.commit()

def group_add(data = {}, commit=True):
    return app.data.models.add_single(Group, data, commit)


def group_add_m(data=[]):
    return app.data.models.add_multiple(Group, data)


def group_update(student, data={}, commit=True):
    return app.data.models.update_single(Group, student, data, commit)


def group_delete_m(ids=[], groups=[]):
    return app.data.models.delete_multiple(Group, ids, groups)


def group_get_m(filters=[], fields=[], ids=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Group, filters=filters, fields=fields, ids=ids, order_by=order_by, first=first, count=count, active=active)


def group_get(filters=[]):
    return app.data.models.get_first_single(Group, filters)



# data is a list, with:
# group: the ORM-student-object
# changed: a list of properties that are changed
# property#1: the first property changed
# property#2: ....
# overwrite: if True, overwrite the changed field, else extend the changed field
def group_update_m(data=[], overwrite=False):
    try:
        for d in data:
            group = d['group']
            for property in d['changed']:
                v = d[property]
                if hasattr(group, property):
                    if getattr(Group, property).expression.type.python_type == type(v):
                        setattr(group, property, v.strip() if isinstance(v, str) else v)
            # if the student is new, do not set the changed flag in order not to confuse other modules that need to process the groups (new has priority over changed)
            if group.new:
                group.changed = ''
            else:
                if overwrite:
                    group.changed = json.dumps(d['changed'])
                else:
                    changed = json.loads(group.changed) if group.changed != '' else []
                    changed.extend(d['changed'])
                    changed = list(set(changed))
                    group.changed = json.dumps(changed)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


def group_flag_m(data=[]):
    try:
        for d in data:
            student = d['student']
            for k, v in d.items():
                if hasattr(student, k):
                    setattr(student, k, v)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None


############ student overview list #########
def pre_sql_query():
    return db.session.query(Group).filter(Group.active == True)


def pre_sql_filter(query, filter):
    for f in filter:
        if f['name'] == 'type':
            if f['value'] != 'default':
                query = query.filter(Group.type == f["value"])
        if f['name'] == 'archived':
            if f['value'] != 'default':
                query = query.filter(Group.archived == (f["value"] == "True"))
    return query


def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Group.display_name.like(search_string))
    search_constraints.append(Group.description.like(search_string))
    return search_constraints
