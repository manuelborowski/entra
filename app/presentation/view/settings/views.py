from flask import render_template
from flask_login import login_required

from app import admin_required
from app.application import socketio as msocketio, event as mevent
from . import settings
from app.application import settings as msettings, cron as mcron, formio as mformio, cron_table
import json

@settings.route('/settings', methods=['GET', 'POST'])
@admin_required
@login_required
def show():
  cron_module_enable_settings = msettings.get_configuration_setting('cron-enable-modules')
  cron_module = mformio.search_component(settings_formio, 'cron-enable-modules')
  cron_module["components"] = []
  for nbr, module in enumerate(cron_table):
    enabled = cron_module_enable_settings[module[0]] if module[0] in cron_module_enable_settings else False
    cron_module["components"].append({"label": f'({nbr+1}) {module[2]}', "tooltip": module[3], "tableView": False, "defaultValue": enabled, "key": module[0], "type": "checkbox", "input": True})
  default_settings = msettings.get_configuration_settings(convert_to_string=True)
  data = {'default': default_settings, 'template': settings_formio}
  return render_template('/settings/settings.html', data=data)


def update_settings_cb(msg, client_sid=None):
  try:
    data = msg['data']
    settings = json.loads(data['value'])
    msettings.set_setting_topic(settings)
    msocketio.broadcast_message({'type': 'settings', 'data': {'status': True}})
  except Exception as e:
    msocketio.broadcast_message({'type': 'settings', 'data': {'status': False, 'message': str(e)}})


msocketio.subscribe_on_type('settings', update_settings_cb)


from app.presentation.view import false, true, null

# https://formio.github.io/formio.js/app/builder
settings_formio = \
  {
    "display": "form",
    "components": [
      {
        "label": "Algemeen",
        "tableView": false,
        "key": "algemeen",
        "type": "container",
        "input": true,
        "components": [
          {
            "title": "Algemeen",
            "theme": "primary",
            "collapsible": true,
            "key": "algemeen",
            "type": "panel",
            "label": "Algemeen",
            "collapsed": true,
            "input": false,
            "tableView": false,
            "components": [
              {
                "label": "Opslaan",
                "showValidations": false,
                "theme": "warning",
                "tableView": false,
                "key": "submit",
                "type": "button",
                "input": true,
                "saveOnEnter": false
              },
              {
                "label": "Nieuwe gebruikers via Smartschool",
                "tooltip": "Nieuwe gebruikers kunnen inloggen via Smartschool en krijgen automatisch het laagste profiel",
                "tableView": false,
                "key": "generic-new-via-smartschool",
                "type": "checkbox",
                "input": true,
                "defaultValue": false
              }
            ]
          }
        ]
      },
      {
        "title": "Templates",
        "theme": "warning",
        "collapsible": true,
        "key": "templates",
        "type": "panel",
        "label": "Panel",
        "collapsed": true,
        "input": false,
        "tableView": false,
        "components": [
          {
            "label": "Gebruikers",
            "tableView": false,
            "key": "gebruikers",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Gebruikers",
                "theme": "primary",
                "collapsible": true,
                "key": "algemeen",
                "type": "panel",
                "label": "Algemeen",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true,
                    "saveOnEnter": false
                  },
                  {
                    "label": "Lijst template (JSON)",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "user-datatables-template",
                    "type": "textarea",
                    "input": true
                  }
                ]
              }
            ]
          },
          {
            "label": "templates-studenten",
            "tableView": false,
            "key": "templates-studenten",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Studenten",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate1",
                "type": "panel",
                "label": "Studenten",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true,
                    "saveOnEnter": false
                  },
                  {
                    "label": "Detail template (formio)",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "student-formio-template",
                    "type": "textarea",
                    "input": true
                  },
                  {
                    "label": "Lijst template (JSON)",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "student-datatables-template",
                    "type": "textarea",
                    "input": true
                  },
                  {
                    "label": "Detail zicht van studenten: maximum aantal studenten te bekijken met 1 click",
                    "labelPosition": "left-left",
                    "mask": false,
                    "tableView": false,
                    "delimiter": false,
                    "requireDecimal": false,
                    "inputFormat": "plain",
                    "truncateMultipleSpaces": false,
                    "key": "student-max-students-to-view-with-one-click",
                    "type": "number",
                    "input": true
                  }
                ]
              }
            ]
          },
          {
            "label": "templates-staff",
            "tableView": false,
            "key": "templates-staff",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Personeelsleden",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate1",
                "type": "panel",
                "label": "Studenten",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true,
                    "saveOnEnter": false
                  },
                  {
                    "label": "Detail template (formio)",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "staff-formio-template",
                    "type": "textarea",
                    "input": true
                  },
                  {
                    "label": "Lijst template (JSON)",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "staff-datatables-template",
                    "type": "textarea",
                    "input": true
                  }
                ]
              }
            ]
          },
          {
            "label": "templates-cardpresso",
            "tableView": false,
            "key": "templates-cardpresso",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Popups",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate1",
                "type": "panel",
                "label": "Studenten",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true,
                    "saveOnEnter": false
                  },
                  {
                    "label": "Student/Leerkracht paswoord update",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "popup-student-teacher-update-password",
                    "type": "textarea",
                    "input": true
                  },
                  {
                    "label": "Database integriteits controle",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "popup-database-integrity-check",
                    "type": "textarea",
                    "input": true
                  },
                  {
                    "label": "Nieuwe gebruiker / gebruiker aanpassen",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "popup-new-update-user",
                    "type": "textarea",
                    "input": true
                  }
                ]
              }
            ]
          },
          {
            "label": "templates-pop-ups",
            "tableView": false,
            "key": "templates-pop-ups",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Cardpresso",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate1",
                "type": "panel",
                "label": "Studenten",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true,
                    "saveOnEnter": false
                  },
                  {
                    "label": "Detail template (formio)",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "cardpresso-formio-template",
                    "type": "textarea",
                    "input": true
                  },
                  {
                    "label": "Lijst template (JSON)",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "cardpresso-datatables-template",
                    "type": "textarea",
                    "input": true
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "title": "Modules",
        "theme": "warning",
        "collapsible": true,
        "key": "modules",
        "type": "panel",
        "label": "Panel",
        "input": false,
        "tableView": false,
        "components": [
          {
            "label": "School Data Hub",
            "tableView": false,
            "key": "sdh",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Centrale database",
                "theme": "primary",
                "collapsible": true,
                "key": "general1",
                "type": "panel",
                "label": "General",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Meldt veranderingen aan volgende adressen",
                    "tooltip": "één adres per rij\nEen adres wordt niet gebruikt als er een # voor staat",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "sdh-inform-emails",
                    "type": "textarea",
                    "input": true
                  },
                  {
                    "label": "Standaard paswoord",
                    "labelPosition": "left-left",
                    "tooltip": "Nieuwe studenten krijgen dit als standaard paswoord (computer en Smartschool)",
                    "tableView": true,
                    "key": "generic-standard-password",
                    "type": "textfield",
                    "input": true
                  },
                  {
                    "label": "Columns",
                    "columns": [
                      {
                        "components": [
                          {
                            "label": "Nieuw schooljaar?",
                            "disabled": true,
                            "tableView": false,
                            "defaultValue": false,
                            "key": "sdh-schoolyear-changed",
                            "type": "checkbox",
                            "input": true
                          }
                        ],
                        "width": 4,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 4
                      },
                      {
                        "components": [
                          {
                            "label": "Vorig schooljaar",
                            "labelPosition": "left-left",
                            "disabled": true,
                            "tableView": true,
                            "key": "sdh-prev-schoolyear",
                            "type": "textfield",
                            "input": true
                          }
                        ],
                        "width": 4,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 4
                      },
                      {
                        "components": [
                          {
                            "label": "Huidig schooljaar",
                            "labelPosition": "left-left",
                            "disabled": true,
                            "tableView": true,
                            "key": "sdh-current-schoolyear",
                            "type": "textfield",
                            "input": true
                          }
                        ],
                        "size": "md",
                        "width": 4,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "currentWidth": 4
                      }
                    ],
                    "key": "columns",
                    "type": "columns",
                    "input": false,
                    "tableView": false
                  }
                ]
              }
            ]
          },
          {
            "label": "Cron-generic",
            "tableView": false,
            "key": "cron-generic",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Cron: generiek",
                "theme": "primary",
                "collapsible": true,
                "key": "cron-generic",
                "type": "panel",
                "label": "Smartschool",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Cron template",
                    "labelPosition": "left-left",
                    "tooltip": "Check https://crontab.guru/ voor de layout van de cron template",
                    "tableView": true,
                    "persistent": false,
                    "key": "cron-scheduler-template",
                    "type": "textfield",
                    "labelWidth": 20,
                    "input": true
                  },
                  {
                    "label": "Columns",
                    "columns": [
                      {
                        "components": [
                          {
                            "label": "Start cron cyclus",
                            "tableView": false,
                            "defaultValue": false,
                            "key": "check-start-cron-cycle",
                            "type": "checkbox",
                            "input": true
                          }
                        ],
                        "width": 3,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 3
                      },
                      {
                        "components": [
                          {
                            "label": "Start cron cyclus",
                            "showValidations": false,
                            "theme": "danger",
                            "tableView": false,
                            "key": "button-start-cron-cycle",
                            "conditional": {
                              "show": true,
                              "when": "cron-generic.check-start-cron-cycle",
                              "eq": "true"
                            },
                            "type": "button",
                            "saveOnEnter": false,
                            "input": true
                          }
                        ],
                        "width": 6,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 6
                      }
                    ],
                    "key": "columns",
                    "type": "columns",
                    "input": false,
                    "tableView": false
                  },
                  {
                    "label": "Container",
                    "tableView": false,
                    "key": "cron-enable-modules",
                    "type": "container",
                    "input": true,
                    "components": []
                  }
                ]
              }
            ]
          },
          {
            "label": "Cron-veyon",
            "tableView": false,
            "key": "cron-veyon",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Cron: veyon specifiek",
                "theme": "primary",
                "collapsible": true,
                "key": "cron-generic",
                "type": "panel",
                "label": "Smartschool",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Cron template",
                    "labelPosition": "left-left",
                    "tooltip": "Check https://crontab.guru/ voor de layout van de cron template",
                    "tableView": true,
                    "persistent": false,
                    "key": "cron-veyon-scheduler-template",
                    "type": "textfield",
                    "labelWidth": 20,
                    "input": true
                  },
                  {
                    "label": "Columns",
                    "columns": [
                      {
                        "components": [
                          {
                            "label": "Start cron cyclus",
                            "tableView": false,
                            "defaultValue": false,
                            "key": "check-start-cron-cycle",
                            "type": "checkbox",
                            "input": true
                          }
                        ],
                        "width": 3,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 3
                      },
                      {
                        "components": [
                          {
                            "label": "Start cron cyclus",
                            "showValidations": false,
                            "theme": "danger",
                            "tableView": false,
                            "key": "button-start-veyon-cron-cycle",
                            "conditional": {
                              "show": true,
                              "when": "cron-veyon.check-start-cron-cycle",
                              "eq": "true"
                            },
                            "type": "button",
                            "saveOnEnter": false,
                            "input": true
                          }
                        ],
                        "width": 6,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 6
                      }
                    ],
                    "key": "columns",
                    "type": "columns",
                    "input": false,
                    "tableView": false
                  },
                  {
                    "label": "Container",
                    "tableView": false,
                    "key": "cron-enable-modules",
                    "type": "container",
                    "input": true,
                    "components": []
                  }
                ]
              }
            ]
          },
          {
            "label": "Smartschool",
            "tableView": false,
            "key": "smartschool",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Smartschool",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate1",
                "type": "panel",
                "label": "Smartschool",
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Teacher groupname",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "smartschool-teacher-group",
                    "type": "textfield",
                    "input": true,
                    "labelWidth": 20
                  },
                  {
                    "label": "WebAPI URL",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "smartschool-api-url",
                    "type": "textfield",
                    "input": true,
                    "labelWidth": 20
                  },
                  {
                    "label": "WebAPI Key",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "smartschool-api-key",
                    "type": "textfield",
                    "input": true,
                    "labelWidth": 20
                  }
                ],
                "collapsed": true
              }
            ]
          },
          {
            "label": "Cardpresso",
            "tableView": false,
            "key": "cardpresso",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Cardpresso",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate2",
                "type": "panel",
                "label": "Smartschool",
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Columns",
                    "columns": [
                      {
                        "components": [
                          {
                            "label": "Nieuw of aangepaste studenten krijgen nieuwe badge",
                            "tableView": false,
                            "defaultValue": false,
                            "key": "check-new-badges",
                            "type": "checkbox",
                            "input": true
                          }
                        ],
                        "width": 4,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 4
                      },
                      {
                        "components": [
                          {
                            "label": "Nieuw of aangepaste studenten krijgen nieuwe badge",
                            "showValidations": false,
                            "theme": "danger",
                            "tableView": false,
                            "key": "button-new-badges",
                            "conditional": {
                              "show": true,
                              "when": "cardpresso.check-new-badges",
                              "eq": "true"
                            },
                            "type": "button",
                            "saveOnEnter": false,
                            "input": true
                          }
                        ],
                        "width": 6,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 6
                      }
                    ],
                    "key": "columns",
                    "type": "columns",
                    "input": false,
                    "tableView": false
                  },
                  {
                    "label": "Columns",
                    "columns": [
                      {
                        "components": [
                          {
                            "label": "nieuwe RFID naar centrale database",
                            "tableView": false,
                            "defaultValue": false,
                            "key": "check-new-rfid",
                            "type": "checkbox",
                            "input": true
                          }
                        ],
                        "width": 4,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 4
                      },
                      {
                        "components": [
                          {
                            "label": "nieuwe RFID naar centrale database",
                            "showValidations": false,
                            "theme": "danger",
                            "tableView": false,
                            "key": "button-new-rfid",
                            "conditional": {
                              "show": true,
                              "when": "cardpresso.check-new-rfid",
                              "eq": "true"
                            },
                            "type": "button",
                            "saveOnEnter": false,
                            "input": true
                          }
                        ],
                        "width": 6,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 6
                      }
                    ],
                    "key": "columns1",
                    "type": "columns",
                    "input": false,
                    "tableView": false
                  },
                  {
                    "label": "Vsk startnummer",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "key": "cardpresso-vsk-startnumber",
                    "type": "textfield",
                    "input": true
                  },
                  {
                    "label": "Meldt veranderingen aan volgende adressen",
                    "tooltip": "één adres per rij\nEen adres wordt niet gebruikt als er een # voor staat",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "cardpresso-inform-emails",
                    "type": "textarea",
                    "input": true
                  }
                ],
                "collapsed": true
              }
            ]
          },
          {
            "label": "Active Directory",
            "tableView": false,
            "key": "active-directory",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Active Directory",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate4",
                "type": "panel",
                "label": "Cardpresso",
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "URL to server",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "ad-url",
                    "type": "textfield",
                    "input": true,
                    "labelWidth": 20
                  },
                  {
                    "label": "Server login",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "ad-login",
                    "type": "textfield",
                    "input": true,
                    "labelWidth": 20
                  },
                  {
                    "label": "Columns",
                    "columns": [
                      {
                        "components": [
                          {
                            "label": "Toon server wachtwoord",
                            "tableView": false,
                            "defaultValue": false,
                            "key": "ad-show-password",
                            "type": "checkbox",
                            "input": true
                          }
                        ],
                        "width": 2,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 2
                      },
                      {
                        "components": [
                          {
                            "label": "Server password",
                            "labelPosition": "left-left",
                            "spellcheck": false,
                            "tableView": true,
                            "persistent": false,
                            "key": "ad-password",
                            "conditional": {
                              "show": true,
                              "when": "active-directory.ad-show-password",
                              "eq": "true"
                            },
                            "type": "textfield",
                            "labelWidth": 20,
                            "input": true
                          }
                        ],
                        "width": 6,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 6
                      }
                    ],
                    "key": "columns",
                    "type": "columns",
                    "input": false,
                    "tableView": false
                  },
                  {
                    "label": "Reset studentenwachtwoord",
                    "tooltip": "Als de student nieuw is, maar toch al in AD zit, dan wordt het paswoord gereset (Student moet direct een nieuw paswoord ingeven).\nTijdens opstart (begin schooljaar) UNCHECK deze box",
                    "tableView": false,
                    "defaultValue": false,
                    "key": "ad-reset-student-password",
                    "type": "checkbox",
                    "input": true
                  },
                  {
                    "label": "Deactiveer verwijderde student",
                    "tooltip": "Studenten die niet meer aanwezig zijn in de database worden gedeactiveerd",
                    "tableView": false,
                    "key": "ad-deactivate-deleled-student",
                    "type": "checkbox",
                    "input": true,
                    "defaultValue": false
                  },
                  {
                    "label": "Verbose logging",
                    "tooltip": "Logging is gedetailleerd.\nNIET opzetten tijdens normaal gebruik, alleen voor testen",
                    "tableView": false,
                    "key": "ad-verbose-logging",
                    "type": "checkbox",
                    "input": true,
                    "defaultValue": false
                  },
                  {
                    "label": "Nieuw schooljaar?",
                    "disabled": true,
                    "tableView": false,
                    "key": "ad-schoolyear-changed",
                    "type": "checkbox",
                    "input": true,
                    "defaultValue": false
                  }
                ],
                "collapsed": true
              }
            ]
          },
          {
            "label": "Papercut",
            "tableView": false,
            "key": "papercut",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Papercut",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate6",
                "type": "panel",
                "label": "Active Directory",
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Server",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "papercut-server-url",
                    "type": "textfield",
                    "labelWidth": 20,
                    "input": true
                  },
                  {
                    "label": "Server port",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "papercut-server-port",
                    "type": "textfield",
                    "labelWidth": 20,
                    "input": true
                  },
                  {
                    "label": "Columns",
                    "columns": [
                      {
                        "components": [
                          {
                            "label": "Toon server token",
                            "tableView": false,
                            "defaultValue": false,
                            "key": "papercut-show-password",
                            "type": "checkbox",
                            "input": true
                          }
                        ],
                        "width": 2,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 2
                      },
                      {
                        "components": [
                          {
                            "label": "Server authentication token",
                            "labelPosition": "left-left",
                            "spellcheck": false,
                            "tableView": true,
                            "persistent": false,
                            "key": "papercut-auth-token",
                            "conditional": {
                              "show": true,
                              "when": "papercut.papercut-show-password",
                              "eq": "true"
                            },
                            "type": "textfield",
                            "labelWidth": 20,
                            "input": true
                          }
                        ],
                        "width": 6,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 6
                      }
                    ],
                    "key": "columns",
                    "type": "columns",
                    "input": false,
                    "tableView": false
                  },
                  {
                    "label": "Laad RFID van Personeel",
                    "theme": "danger",
                    "tooltip": "Haal uit Papercut de RFID code's van het personeel en bewaar in SDH",
                    "tableView": false,
                    "key": "papercut-load-rfid-event",
                    "type": "button",
                    "input": true,
                    "saveOnEnter": false
                  }
                ],
                "collapsed": true
              }
            ]
          },
          {
            "label": "Wisa",
            "tableView": false,
            "key": "wisa",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Wisa",
                "theme": "primary",
                "collapsible": true,
                "key": "RegistratieTemplate4",
                "type": "panel",
                "label": "Cardpresso",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "URL",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "wisa-url",
                    "type": "textfield",
                    "labelWidth": 20,
                    "input": true
                  },
                  {
                    "label": "Studenten query",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "wisa-student-query",
                    "type": "textfield",
                    "labelWidth": 20,
                    "input": true
                  },
                  {
                    "label": "Personeel query",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "persistent": false,
                    "key": "wisa-staff-query",
                    "type": "textfield",
                    "labelWidth": 20,
                    "input": true
                  },
                  {
                    "label": "Server login",
                    "labelPosition": "left-left",
                    "labelWidth": 20,
                    "tableView": true,
                    "persistent": false,
                    "key": "wisa-login",
                    "type": "textfield",
                    "input": true
                  },
                  {
                    "label": "Columns",
                    "columns": [
                      {
                        "components": [
                          {
                            "label": "Toon wachtwoord",
                            "tableView": false,
                            "key": "wisa-show-password",
                            "type": "checkbox",
                            "input": true,
                            "defaultValue": false
                          }
                        ],
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 2,
                        "width": 2
                      },
                      {
                        "components": [
                          {
                            "label": "Server password",
                            "labelPosition": "left-left",
                            "spellcheck": false,
                            "tableView": true,
                            "persistent": false,
                            "key": "wisa-password",
                            "conditional": {
                              "show": true,
                              "when": "wisa.wisa-show-password",
                              "eq": "true"
                            },
                            "type": "textfield",
                            "labelWidth": 20,
                            "input": true
                          }
                        ],
                        "width": 6,
                        "offset": 0,
                        "push": 0,
                        "pull": 0,
                        "size": "md",
                        "currentWidth": 6
                      }
                    ],
                    "key": "columns",
                    "type": "columns",
                    "input": false,
                    "tableView": false
                  },
                  {
                    "label": "Huidig schooljaar",
                    "labelPosition": "left-left",
                    "spellcheck": false,
                    "tableView": true,
                    "persistent": false,
                    "key": "wisa-schoolyear",
                    "type": "textfield",
                    "labelWidth": 20,
                    "input": true
                  },
                  {
                    "label": "Vorig schooljaar gebruiken?",
                    "tooltip": "In juli en augustus kan je geen studenten uit wisa halen.  Als je dit aanvinkt, dan worden de studenten eind vorig schooljaar opgehaald.  Anders de nieuwe van volgend schooljaar",
                    "tableView": false,
                    "key": "wisa-student-use-previous-schoolyear",
                    "type": "checkbox",
                    "input": true,
                    "defaultValue": false
                  }
                ]
              }
            ]
          },
          {
            "label": "Foto",
            "tableView": false,
            "key": "photo",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Foto",
                "theme": "primary",
                "collapsible": true,
                "key": "photo",
                "type": "panel",
                "label": "Cardpresso",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Verbose logging",
                    "tooltip": "Logging is gedetailleerd.\nNIET opzetten tijdens normaal gebruik, alleen voor testen",
                    "tableView": false,
                    "defaultValue": false,
                    "key": "photo-verbose-logging",
                    "type": "checkbox",
                    "input": true
                  }
                ]
              }
            ]
          },
          {
            "label": "API",
            "tableView": false,
            "key": "api",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "API",
                "theme": "primary",
                "collapsible": true,
                "key": "api",
                "type": "panel",
                "label": "Cardpresso",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Opslaan ",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "API sleutels",
                    "tooltip": "Een JSON lijst van sleutels",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "api-keys",
                    "type": "textarea",
                    "input": true
                  }
                ]
              }
            ]
          },
          {
            "label": "Emailserver",
            "tableView": false,
            "key": "emailserver",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "E-mail server instellingen",
                "theme": "primary",
                "collapsible": true,
                "key": "emailserver",
                "type": "panel",
                "label": "E-mail server settings",
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Submit",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Aantal keer dat een e-mail geprobeerd wordt te verzenden",
                    "labelPosition": "left-left",
                    "mask": false,
                    "spellcheck": false,
                    "tableView": false,
                    "delimiter": false,
                    "requireDecimal": false,
                    "inputFormat": "plain",
                    "key": "email-send-max-retries",
                    "type": "number",
                    "input": true
                  },
                  {
                    "label": "Tijd (seconden) tussen het verzenden van e-mails",
                    "labelPosition": "left-left",
                    "mask": false,
                    "spellcheck": true,
                    "tableView": false,
                    "persistent": false,
                    "delimiter": false,
                    "requireDecimal": false,
                    "inputFormat": "plain",
                    "key": "email-task-interval",
                    "type": "number",
                    "input": true
                  },
                  {
                    "label": "Max aantal e-mails per minuut",
                    "labelPosition": "left-left",
                    "mask": false,
                    "spellcheck": true,
                    "tableView": false,
                    "persistent": false,
                    "delimiter": false,
                    "requireDecimal": false,
                    "inputFormat": "plain",
                    "key": "emails-per-minute",
                    "type": "number",
                    "input": true
                  },
                  {
                    "label": "Basis URL",
                    "labelPosition": "left-left",
                    "tableView": true,
                    "key": "email-base-url",
                    "type": "textfield",
                    "input": true
                  },
                  {
                    "label": "E-mails mogen worden verzonden",
                    "tableView": false,
                    "persistent": false,
                    "key": "email-enable-send-email",
                    "type": "checkbox",
                    "input": true,
                    "defaultValue": false
                  }
                ],
                "collapsed": true
              }
            ]
          },
          {
            "label": "Test",
            "tableView": false,
            "key": "test",
            "type": "container",
            "input": true,
            "components": [
              {
                "title": "Test instellingen",
                "theme": "primary",
                "collapsible": true,
                "key": "test",
                "type": "panel",
                "label": "E-mail server settings",
                "collapsed": true,
                "input": false,
                "tableView": false,
                "components": [
                  {
                    "label": "Submit",
                    "showValidations": false,
                    "theme": "warning",
                    "tableView": false,
                    "key": "submit",
                    "type": "button",
                    "input": true
                  },
                  {
                    "label": "Test voorbereiden.  OPGELET, database wordt leeg gemaakt!!!",
                    "tooltip": "Maak de database leeg, wis huidig en vorig schooljaar,...",
                    "tableView": false,
                    "defaultValue": false,
                    "key": "test-prepare",
                    "type": "checkbox",
                    "input": true
                  },
                  {
                    "label": "Wisa testbestanden",
                    "tooltip": "Als de croncyclus wordt uitgevoerd, haal de wisa data uit onderstaande bestanden\nEen regel met # wordt genegeerd",
                    "autoExpand": false,
                    "tableView": true,
                    "key": "test-wisa-json-list",
                    "type": "textarea",
                    "input": true
                  },
                  {
                    "label": "Huidig wisa test bestand",
                    "labelPosition": "left-left",
                    "tooltip": "Bovenstaande lijst wordt continu van boven naar beneden doorlopen.\nHier wordt het huidige wisa testbestand weergegeven.",
                    "tableView": true,
                    "key": "test-wisa-current-json",
                    "type": "textfield",
                    "input": true
                  },
                  {
                    "label": "RFID start code",
                    "labelPosition": "left-left",
                    "tooltip": "hex code in the form '113ABC'\nIf the code is valid and there is no #, then this code is used as dummy RFID in the badges\nEach time the code is read, it is incremented by one",
                    "tableView": true,
                    "key": "test-rfid-start-code",
                    "type": "textfield",
                    "input": true
                  }
                ]
              }
            ]
          }
        ],
        "collapsed": true
      }
    ]
  }