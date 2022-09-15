import datetime
from datetime import timedelta
from haystack_connector import QueryConnector
import json


DEFAULT_Q_CANDIDATES = 20
DEFAULT_Q_READERS = 3


def test_query():
    CFG_PATH = '../config/config.json'
    with open(CFG_PATH, encoding='utf-8-sig') as file:
        CONFIG = json.load(file)

    url = CONFIG['neo4j']['url']
    user = CONFIG['neo4j']['user']
    password = CONFIG['neo4j']['password']
    from_date = datetime.datetime.strptime("2022-01-01", '%Y-%m-%d')
    to_date = datetime.datetime.strptime("2022-09-30", '%Y-%m-%d') + timedelta(days=1)

    query = "How to implement SDG"
    results = 5
    query_connector = QueryConnector(url, user=user, password=password)
    result = query_connector.get_answers_th(query, date_from=from_date, to_date=to_date, readers=results)
    print(json.loads(result))


if __name__ == '__main__':
    test_query()


