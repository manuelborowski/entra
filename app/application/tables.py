from app.data.utils import raise_error



def prepare_item_config_for_view(table, action):
    try:
        item_config = table['item'][action]
        item_config['item_action'] = f'{table["view"]}.item_action'
        item_config['action'] = action
    except Exception as e:
        raise_error('Kan de itemconfiguratietabel niet ophalen', e)
    return item_config


