# -*- coding:utf-8 -*-
# import sys
#
# print(sys.path)
import os.path

from flask import Flask, request, send_from_directory
from flask_restx import Api, Resource
from datetime import timedelta
import datetime
import time
import timeit
import json
from flask_cors import CORS

from utils.errors import errors, SchemaValidationError, WrongFormatFields, InternalServerError
from utils.importFunctions import *
from utils.haystack_connector import QueryConnector
# 修改 from utils.cdqa_connector import CdqaConnector

from utils.n4j_connector import N4jConnector
from werkzeug.utils import secure_filename


import logging

ODS_ARRAY = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]

DATE_FORMAT_COMPLETE = '%d/%m/%Y %H:%M:%S'
DATE_FORMAT = '%Y-%m-%d'
MONGO_FORMAT = '%d/%m/%Y'

CFG_PATH = './config/config.json'

topics_limit = None
news_limit = None
user = password = None
# user="neo4j"
# password="~~86*trust*SORRY*talk*55~~"

# Connectors
n4j_conn = None
query_connector = None

# LOGGING CONFIGURATION
# logging.basicConfig(filename='app.log', filemode='w', format='%(asctime)-15s  %(name)s - %(levelname)s - %(message)s')
logging.basicConfig(format='%(asctime)-15s  %(name)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('apiLogger')

UPLOAD_FOLDER = "upload" #os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}

flask_app = Flask(__name__)
flask_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
api = Api(app=flask_app, errors=errors)
CORS(flask_app)


# 在响应(response)之前做出响应，对于跨域请求权限进行设置
@flask_app.after_request
def after_request(response):
    header = response.headers
    # Access-Control-Allow-Origin的值是逗号分隔的一个具体的字符串或者*，表明服务器支持的所有跨域请求的方法。
    # * 表明，该资源可以被任意外域访问
    # 如果服务端仅允许来自https://foo.example的访问，则Access-Control-Allow-Origin的值应为https://foo.example
    header['Access-Control-Allow-Origin'] = '*'
    return response


# In namespace, the first variable defines the path and second defines the description for that space.
# 定义命名空间，作为后端网页展示的一级目录
name_space = api.namespace('news', description='News API')
ns_tokens = api.namespace('tokens', description='Tokens APIs')
ns_statistics = api.namespace('stats', description='Statistics')
ns_queries = api.namespace('queries', description='Queries')
ns_import = api.namespace('import', description='Generate News Graph')


# 输入url在neo4j中生成节点
@ns_import.route("/url")
class MainClass(Resource):
    @api.doc(params={'url': {'description': 'url of news', 'type': 'string', 'required': True}})
    def post(self):
        try:
            url = request.form['url']
            content, title, flag = get_content_from_url(url)
            result = import_document(flag, url, title, "en", content, "url")

            return result
        except Exception as error:
            return {"result": str(error)}


# @api.doc(params={'file': {'description': 'pdf file', 'type': 'file', 'required': True}})
@ns_import.route("/file")
class MainClass(Resource):
    @api.doc(params={'filename': {'description': 'name of file', 'type': 'string', 'required': True}})
    def get(self):
        directory_path = os.path.join(sys.path[0], flask_app.config['UPLOAD_FOLDER'])
        filename = request.args.get('filename')

        if os.path.isfile(os.path.join(directory_path, filename)):
            return send_from_directory(directory_path, filename, as_attachment=True)

        return None

    def post(self):
        try:
            if 'file' not in request.files:
                return {"result": "Fail to get the file"}

            file = request.files['file']

            if file.name == "":
                return {"result": "No selected file"}

            if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
                # filename = secure_filename(file.filename)
                filename = file.filename
                filepath = os.path.join(sys.path[0], flask_app.config['UPLOAD_FOLDER'], filename)

                if os.path.exists(filepath):
                    return {"result": "Error: This file has already existed in the database."}

                file.save(filepath)

                content, title, flag = get_content_from_pdf(filepath)
                result = import_document(flag, filename, title, "en", content, "pdf")
                # delete_file(filepath)

                return result
            else:
                return {"result": "Error: This file is not a PDF file. Please choose another one."}
        except Exception as error:
            return {"result": str(error)}


# 查询某一时间段内sentiment最positive的ODS新闻
@api.doc(params={'date_from': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True},
                 'date_to': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True},
                 'entity': {'description': 'Entity or Organization', 'type': 'string', 'required': False}})
@name_space.route("/positive")
class MainClass(Resource):
    @api.doc(params={'sdg': {'description': 'Specify the number of SDG', 'required': False, 'enum': ODS_ARRAY}})
    def get(self):
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        entity = request.args.get('entity')

        if not date_from or not date_to:
            return {"error": "Request is missing required fields", "status": 400}
        arg_sdg = request.args.get('sdg')
        sdg = 0

        if arg_sdg:
            sdg = int(arg_sdg)
        print('SDG:', sdg, 'from:', date_from, 'to', date_to)

        try:
            from_date = datetime.datetime.strptime(date_from, DATE_FORMAT)
            to_date = datetime.datetime.strptime(date_to, DATE_FORMAT)
            to_date = to_date + timedelta(days=1)
            news = n4j_conn.get_most_positive(from_date, to_date, sdg, entity)
            print('result', news)
            return json.loads(news)
        except ValueError as err:
            return {"error": "Wrong argument format", "status": 400, "detail": str(err)}


# 查询某一时间段内sentiment最negative的ODS新闻
@api.doc(params={'date_from': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True},
                 'date_to': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True},
                 'entity': {'description': 'Entity or Organization', 'type': 'string', 'required': False}})
@name_space.route("/negative")
class MainClass(Resource):
    @api.doc(params={'sdg': {'description': 'Specify the number of SDG', 'required': False, 'enum': ODS_ARRAY}})
    def get(self):
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        entity = request.args.get('entity')

        if not date_from or not date_to:
            return {"error": "Request is missing required fields", "status": 400}

        arg_sdg = request.args.get('sdg')
        sdg = 0

        if arg_sdg:
            sdg = int(arg_sdg)
        print('SDG:', sdg, 'from:', date_from, 'to', date_to)

        try:
            from_date = datetime.datetime.strptime(date_from, DATE_FORMAT)
            to_date = datetime.datetime.strptime(date_to, DATE_FORMAT)
            to_date = to_date + timedelta(days=1)
            news = n4j_conn.get_most_negative(from_date, to_date, sdg, entity)
            return json.loads(news)
        except ValueError as err:
            print(err)
            return {"error": "Wrong argument format", "detail": str(err)}


# 查询某一时间段内的ODS新闻
@api.doc(params={'date_from': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True},
                 'date_to': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True},
                 'entity': {'description': 'Entity or Organization', 'type': 'string', 'required': False}})
@name_space.route("/")
class MainClass(Resource):
    @api.doc(params={'sdg': {'description': 'Specify the number of SDG', 'required': False, 'enum': ODS_ARRAY}})
    def get(self):
        sdg = None
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        entity = request.args.get('entity')

        if not date_from or not date_to:
            return {"error": "Request is missing required fields", "status": 400}
        arg_sdg = request.args.get('sdg')
        if arg_sdg:
            sdg = int(arg_sdg)

        print('SDG:', sdg, 'from:', date_from, 'to', date_to)

        try:
            from_date = datetime.datetime.strptime(date_from, DATE_FORMAT)
            to_date = datetime.datetime.strptime(date_to, DATE_FORMAT)
            to_date = to_date + timedelta(days=1)
            news = n4j_conn.get_range_news(from_date, to_date, osd=sdg, limit=news_limit, entity=entity)
            print(news)
            return json.loads(news)
        except ValueError as err:
            return {"error": "Wrong argument format", "status": 400, "detail": str(err)}


#### TOKENS #####
# 获取某一时间段内，ODS新闻的Token信息
@api.doc(params={'date_from': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True},
                 'date_to': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'default': None}})
@ns_tokens.route("/")
class MainClass(Resource):
    @api.doc(params={'sdg': {'description': 'Specify the number of SDG', 'required': False, 'enum': ODS_ARRAY}})
    def get(self):
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        if not date_from or not date_to:
            return {"error": "Request is missing required fields", "status": 400}

        arg_sdg = request.args.get('sdg')
        sdg = None
        if arg_sdg:
            logger.info("Get tokens from %s to %s ans SDG= %s", date_from, date_to, arg_sdg)
            sdg = int(arg_sdg)
        else:
            logger.info("Get tokens from %s to %s", date_from, date_to)

        try:
            from_date = datetime.datetime.strptime(date_from, DATE_FORMAT)
            to_date = datetime.datetime.strptime(date_to, DATE_FORMAT)
            to_date = to_date + timedelta(days=1)
            tokens = n4j_conn.get_tokens(from_date, to_date, sdg, topics_limit)
            logger.debug("Tokens result: %s", tokens)
            return json.loads(tokens)
        except ValueError as err:
            logger.error("Wrong argument format. Detail: %s", str(err))
            return {"error": "Wrong argument format", "status": 400, "detail": str(err)}


# News per SDG
# 统计信息：获取某一时间段内，某个ods或者所有ods的News条数，按照ODS编号排序
@api.doc(
    params={'date_from': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True, 'default': None},
            'date_to': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True, 'default': None},
            'entity': {'description': 'Entity or Organization', 'type': 'string', 'required': False}})
@ns_statistics.route("/news_sdg")
class MainClass(Resource):
    @api.doc(params={'sdg': {'description': 'Specify the number of SDG', 'required': False, 'enum': ODS_ARRAY}})
    def get(self):
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        entity = request.args.get('entity')

        if not date_from or not date_to:
            return {"error": "Request is missing required fields", "status": 400}
        sdg = request.args.get('sdg')
        if sdg:
            sdg = int(sdg)
        print('SDG:', sdg, 'from:', date_from, 'to', date_to)
        try:
            from_date = datetime.datetime.strptime(date_from, DATE_FORMAT)
            to_date = datetime.datetime.strptime(date_to, DATE_FORMAT)
            to_date = to_date + timedelta(days=1)
            tokens = n4j_conn.get_news_per_sdg(from_date, to_date, sdg, entity)
            print(tokens)
            return json.loads(tokens)
        except ValueError as err:
            return {"error": "Wrong argument format", "status": 400, "detail": str(err)}


# 统计信息：获取某一时间段内，每天有最多News条数的ODS编号、News条数、日期
@api.doc(
    params={'date_from': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True, 'default': None},
            'date_to': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': True, 'default': None},
            'entity': {'description': 'Entity or Organization', 'type': 'string', 'required': False}})
@ns_statistics.route("/ods_day")
class MainClass(Resource):
    @api.doc(params={'sdg': {'description': 'Specify the number of SDG', 'required': False, 'enum': ODS_ARRAY}})
    def get(self):
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        entity = request.args.get('entity')

        if not date_from or not date_to:
            return {"error": "Request is missing required fields", "status": 400}
        arg_sdg = request.args.get('sdg')
        sdg = None
        if arg_sdg:
            sdg = int(arg_sdg)
        print('SDG:', sdg, 'from:', date_from, 'to', date_to)

        try:
            from_date = datetime.datetime.strptime(date_from, DATE_FORMAT)
            to_date = datetime.datetime.strptime(date_to, DATE_FORMAT)
            to_date = to_date + timedelta(days=1)
            odss = n4j_conn.get_ods_per_day(from_date, to_date, sdg, entity)
            print(odss)
            return odss
        except ValueError as err:
            return {"error": "Wrong argument format", "status": 400, "detail": str(err)}


#### QUERIES ####

# 查找所提问题的答案
DEFAULT_Q_CANDIDATES = 20
DEFAULT_Q_READERS = 3


@api.doc(params={'date_from': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': False},
                 'date_to': {'description': 'format: YYYY-MM-DD', 'type': 'string', 'required': False}})
@ns_queries.route("/")
class MainClass(Resource):
    @api.doc(params={'query': {'description': 'Do your question', 'required': True, 'type': 'string'},
                     'results': {'description': 'number of results', 'type': 'int', 'default': DEFAULT_Q_READERS}})
    def get(self):
        query = request.args.get('query')
        if not query:
            return {"error": "Request is missing required fields", "status": 400}

        date_from = request.args.get('date_from', None)
        to_date = request.args.get('date_to', None)

        results = get_int_arg(request.args, 'results', DEFAULT_Q_READERS)

        if date_from and to_date:
            logger.info('Execution of query: %s from %s to %s. Number of results required: %i', query, date_from,
                        to_date, results)
        else:
            logger.info('Execution of query: %s.  Number of results required: %i', query, results)

        try:
            if date_from:
                date_from = datetime.datetime.strptime(date_from, DATE_FORMAT)
            if to_date:
                to_date = datetime.datetime.strptime(to_date, DATE_FORMAT)
                to_date = to_date + timedelta(days=1)
                # next day
        except ValueError as err:
            logger.error("Wrong argument format. Detail: %s", str(err))
            return {"error": "Wrong argument format", "status": 400, "detail": str(err)}

        if query_connector:
            cpu_start = time.process_time()
            start = timeit.default_timer()
            result = query_connector.get_answers_th(query, date_from=date_from, to_date=to_date, readers=results)
            cpu_stop = time.process_time()
            stop = timeit.default_timer()
            logger.debug('Quering time: %i.  Quering process execution time: %i', stop - start, cpu_stop - cpu_start)
            logger.debug('Query result: %s', result)
            return json.loads(result)
        else:
            return {"error": "El gestor de queries no está disponible en esta versión", "status": 400}


# 获取results参数信息（返回值数量）
def get_int_arg(args, name, default=None):
    value = args.get(name, default)
    if value:
        try:
            value = int(value)
        except ValueError as err:
            print('argument error using default ', name, ':', default)
            value = DEFAULT_Q_CANDIDATES
    else:
        print('else default')
        value = default
    return value


def validate_args(d_from, d_to):
    if not d_from:
        raise SchemaValidationError
    if not d_to:
        raise SchemaValidationError


if __name__ == '__main__':
    with open(CFG_PATH, encoding='utf-8-sig') as file:
        CONFIG = json.load(file)

    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler('kg_news.log', 'a')

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    # add Handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)

    logger.info('\nApi logging started!')

    user = CONFIG['neo4j']['user']
    url = CONFIG['neo4j']['url']
    password = CONFIG['neo4j']['password']
    topics_limit = CONFIG['topics_limit']
    news_limit = CONFIG['news_limit']

    # logger.info('Configuration: %s', str(CONFIG))
    logger.info('CONFIGURATION: news limit: %i , topics limit: %i ', news_limit, topics_limit)

    # Connectors

    n4j_conn = N4jConnector(url, user=user, password=password)
    query_connector = QueryConnector(url, user=user, password=password)

    # 修改 query_connector = CdqaConnector(user, password, url=url)

    dev = False

    if dev:
        # Funciona en local:
        flask_app.run()
    else:
        # Funciona en AWS:
        # from utils.haystack_connector import QueryConnector
        # query_connector = QueryConnector(user, password)
        flask_app.run(host='0.0.0.0', port=5000)
