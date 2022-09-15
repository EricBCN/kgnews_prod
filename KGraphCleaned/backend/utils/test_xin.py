# from flask import Flask
# from flask_restx import Resource, Api
import datetime
from datetime import timedelta
from haystack_connector import QueryConnector
from n4j_connector import N4jConnector
import json
import time
import timeit

# app = Flask(__name__)
# api = Api(app)


# @api.route('/hello')
# class HelloWorld(Resource):
#     def get(self):
#         return {'hello': 'world'}

DEFAULT_Q_CANDIDATES = 20
DEFAULT_Q_READERS = 3


def test_query():
    query = "what is clean water"
    results = 5
    query_connector = QueryConnector(user=user, password=password)
    result = query_connector.get_answers_th(query, date_from=from_date, to_date=to_date, readers=results)
    print(json.loads(result))



if __name__ == '__main__':
    # app.run(debug=True)

    CFG_PATH = '../config/config.json'
    with open(CFG_PATH, encoding='utf-8-sig') as file:
        CONFIG = json.load(file)

    user = CONFIG['neo4j']['user']
    url = CONFIG['neo4j']['url']
    password = CONFIG['neo4j']['password']
    topics_limit = CONFIG['topics_limit']
    news_limit = CONFIG['news_limit']

    n4j_conn = N4jConnector(url, user=user, password=password)

    DATE_FORMAT = '%Y-%m-%d'
    date_from = "2022-01-01"
    date_to = "2022-06-30"
    sdg = 5
    from_date = datetime.datetime.strptime(date_from, DATE_FORMAT)
    to_date = datetime.datetime.strptime(date_to, DATE_FORMAT) + timedelta(days=1)
    tokens = n4j_conn.get_news_per_sdg(from_date, to_date, sdg)
    print(tokens)

    tokens = n4j_conn.get_most_positive(from_date, to_date, sdg)
    print(tokens)

    test_query()


