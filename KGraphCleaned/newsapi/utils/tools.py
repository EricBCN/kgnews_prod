import json
import os


def get_entities(lang):
    config_filepath = os.path.join(os.path.split(os.path.dirname(__file__))[0], "conf/news_api.json")

    with open(config_filepath, encoding='utf-8-sig') as file:
        entities = json.load(file)[lang]['entities']

    return entities
