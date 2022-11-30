# -*- coding:utf-8 -*-
from neo4j import GraphDatabase
from . import constants
# import constants
from datetime import timedelta
import json
import logging

# import sys
# sys.path.append()

__all__ = [
    'N4jConnector'
]

logger = logging.getLogger('apiLogger')


# WITH = " WITH {id:n.id, title:n.title, url:n.url , date:n.date, sentiment:n.sentiment, source:n.source } as json "


# utilities
def match_news(lang):
    return "MATCH (n:News_" + lang + " {isitODS : 1} ) "


# 将sentiment数值转换为正面（1）、中性（0）、负面（-1）
def get_emotion(sentiment):
    sentiment = float(sentiment)
    if sentiment > 0.25:
        return 1
    else:
        if sentiment < -0.25:
            return -1
        else:
            return 0


def convert_number_array_to_clause(arr):
    clause = ''
    for item in arr:
        clause += str(item) + ","

    return clause[:-1] if clause != '' else ''


def convert_string_array_to_clause(arr):
    clause = ''
    for item in arr:
        clause += "'" + item.replace("'", "\\'") + "',"

    return clause[:-1] if clause != '' else ''


# 创建查询语句中关于时间段的条件
def build_datetime_clause(field, date_from=None, date_to=None):
    clause = ''
    if date_from:
        clause += "WHERE datetime(" + field + ") >= datetime(\'" + date_from.strftime(constants.NEO4J_FORMAT) + "\') "
        if date_to:
            clause += " AND datetime(" + field + ") < datetime(\'" + date_to.strftime(constants.NEO4J_FORMAT) + "\') "
    else:
        if date_to:
            clause += "WHERE datetime(" + field + ") < datetime(\'" + date_to.strftime(constants.NEO4J_FORMAT) + "\') "
    return clause


# 将一条记录转换成JSON格式
def record_to_json(record):
    json = '{'
    if record:
        for key in record.keys():
            if len(json) > 1:
                json += ', '

            if key == "entity":
                json += '"' + key + '":' + create_list(record[key])
            else:
                json += '"' + key + '":"' + str(record[key]) + '"'

            if key == "sentiment":
                json += ', "emotion":' + str(get_emotion(record[key]))

    json += '}'
    return json


def create_list(output):
    json_output = '['
    for e in output:
        json_output += '"' + e + '",'

    if len(output) > 0:
        json_output = json_output[:-1]

    json_output += ']'
    return json_output


# 将记录集合转换为JSON格式，其中每条记录的转换由record_to_json函数负责
def create_list_from_records(records):
    json_output = '['
    first = True
    for record in records:
        if first:
            json_output += record_to_json(record)
            first = False
        else:
            json_output += ' , ' + record_to_json(record)

    json_output += ']'
    return json_output


# 过滤token。如果token是advertisement，则直接忽略
def filter_tokens(records, limit):  # 为何不放在查询语句里？
    new_records = []
    for record in records:
        if str(record['token']) == 'advertisement':
            print('quit advertisement')
        else:
            new_records.append(record)
            if len(new_records) == limit:
                break

    return new_records


# ___________ CLASS DEFINITION ___________________
class N4jConnector:

    # 用url、user、password连接到neo4j，同时，打印目前所有用的英语新闻的条数
    def __init__(self, url, user=None, password=None):
        super().__init__()
        self.neo4j = GraphDatabase.driver(url, auth=(user, password))
        print('[DEBUG] neo4j connector initialized. Currently, there are ', self.count_news(), ' english news')

    # NUMERO TOTAL DE NOTICIAS EN INGLES
    # 返回英语新闻的条数
    def count_news(self):
        session = self.neo4j.session()
        results = session.run("MATCH (a:News_en) RETURN count(a)").single().value()
        session.close()
        return results

    # 执行query，查询新闻
    def get_news(self, query):
        print(' get_news', query)
        session = self.neo4j.session()
        results = session.run(query).values()
        session.close()
        return results

    ###  public methods

    ### Get news
    # 获取某一时间段内，某个ods或者所有ods的News信息，返回的News按照ODS权重由高到低排列
    def get_range_news(self, from_date=None, to_date=None, osd=None, limit=constants.LIMIT_NEWS, entity="", lang='en'):
        # Build query
        query = match_news(lang) + build_datetime_clause("n.date", from_date, to_date)

        if osd and len(osd) > 0:
            query += " AND n.odsID in [" + convert_number_array_to_clause(osd) + "] "

        if entity and len(entity) > 0 and entity[0].lower() != "all":
            # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
            query += " AND ("

            for ent in entity:
                query += "('{0}' in n.entity) OR ".format(ent.replace("'", "\\'"))

            query = query[0:-3] + ") "

        query += " RETURN distinct n.id as ID, n.title as title, n.url as url, n.date as date," \
                 " n.sentiment as sentiment, n.source as source, n.ODSweight as peso," \
                 " n.odsID as ODS_ID, n.entity as entity, '" + lang + "' as lang" \
                 " ORDER BY n.ODSweight DESC"

        if limit > 0:
            query += " LIMIT " + str(limit)

        print(query)

        session = self.neo4j.session()
        results = create_list_from_records(session.run(query))
        session.close()

        return results

    # 获取某一时间段内，某个ods或者所有ods的News信息，并返回sentiment最negative的News
    def get_most_negative(self, from_date=None, to_date=None, osd=None, entity="", lang='en'):
        print('get_most_negative')
        session = self.neo4j.session()

        query = match_news(lang) + build_datetime_clause("n.date", from_date, to_date)

        if osd and len(osd) > 0:
            query += " AND n.odsID in [" + convert_number_array_to_clause(osd) + "] "

        # if entity and entity != "" and entity.lower() != "all":
        #     # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
        #     query += " AND '{0}' in n.entity".format(entity.lower())
        #     # query += " AND '{0}' in n.entity".format(entity)
        if entity and len(entity) > 0 and entity[0].lower() != "all":
            # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
            query += " AND ("

            for ent in entity:
                query += "('{0}' in n.entity) OR ".format(ent.replace("'", "\\'"))

            query = query[0:-3] + ") "

        query += " RETURN distinct n.id as ID, n.title as title, n.url as url, n.date as date," \
                 " n.sentiment as sentiment, n.source as source, n.ODSweight as peso," \
                 " n.odsID as ODS_ID, n.entity as entity, '" + lang + "' as lang" \
                 " ORDER BY toFloat(sentiment) ASC, n.ODSweight DESC LIMIT 1"

        record = session.run(query).single()
        print(query)
        if not record:
            print('error with query:', query)

        result = record_to_json(record)
        session.close()
        return result

    # The most positive article from a time range
    # 获取某一时间段内，某个ods或者所有ods的News信息，并返回sentiment最positive的News
    def get_most_positive(self, from_date=None, to_date=None, osd=None, entity="", lang='en'):
        print('get_most_positive_range')
        session = self.neo4j.session()

        query = match_news(lang) + build_datetime_clause("n.date", from_date, to_date)

        if osd and len(osd) > 0:
            query += " AND n.odsID in [" + convert_number_array_to_clause(osd) + "] "

        # if entity and entity != "" and entity.lower() != "all":
        #     # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
        #     query += " AND '{0}' in n.entity".format(entity.lower())
        #     # query += " AND '{0}' in n.entity".format(entity)
        if entity and len(entity) > 0 and entity[0].lower() != "all":
            # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
            query += " AND ("

            for ent in entity:
                query += "('{0}' in n.entity) OR ".format(ent.replace("'", "\\'"))

            query = query[0:-3] + ") "

        query += " RETURN distinct n.id as ID, n.title as title, n.url as url, n.date as date," \
                 " n.sentiment as sentiment, n.source as source, n.ODSweight as peso," \
                 " n.odsID as ODS_ID, n.entity as entity, '" + lang + "' as lang" \
                 " ORDER BY toFloat(sentiment) DESC, n.ODSweight DESC LIMIT 1"

        print(query)
        record = session.run(query).single()
        if not record:
            print('error with query:', query)

        result = record_to_json(record)
        session.close()

        return result

    # profile MATCH (ne:News_en {isitODS: 1})-[r:NEWS_SENTENCE_en]-(s:Sentence_en)-[r2:TOKEN_BELONGS_TO_en]-(t:Token_en)
    # USING INDEX SEEK ne:News_en(isitODS)
    # WHERE datetime(ne.date) >= datetime('2020-02-02T00:00:00') AND datetime(ne.date) <= datetime('2020-05-13T00:00:00')
    # return t.text as token, count(distinct ne) as news , count(t) as total ORDER BY count(distinct ne) DESC, count(t) DESC LIMIT 5;

    #### The most common tokens

    # 获取某一时间段内，某个ods或者所有ods新闻的所有Token信息
    # 返回的token信息部分：token文本、token出现的新闻数（不同新闻）、token出现的次数
    # 排序：新闻数（降序）、token出现次数（降序）
    def get_tokens(self, date_from=None, date_to=None, osd=None, limit=constants.LIMIT_TOPICS, entity=None, lang='en'):
        print('get_tokens. Limit:', limit)
        session = self.neo4j.session()
        match_tokens = "profile MATCH (ne:News_{0} {{isitODS: 1}})-[r:NEWS_SENTENCE_{0}]-(s:Sentence_{0})-" \
                       "[r2:TOKEN_BELONGS_TO_{0}]-(t:Token_{0}) USING INDEX SEEK ne:News_{0}(isitODS) ".format(lang)

        query = match_tokens + build_datetime_clause("ne.date", date_from, date_to)

        if osd and len(osd) > 0:
            query += " AND ne.odsID in [" + convert_number_array_to_clause(osd) + "] "

        if entity and len(entity) > 0 and entity[0].lower() != "all":
            # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
            query += " AND ("

            for ent in entity:
                query += "('{0}' in ne.entity) OR ".format(ent.replace("'", "\\'"))

            query = query[0:-3] + ") "

        query += " return t.text as token, count(distinct ne) as news , count(t) as total" \
                 " ORDER BY count(distinct ne) DESC, count(t) DESC LIMIT " + str(limit + 1)

        print(query)
        results = session.run(query)
        logger.debug('Results: %s', results)
        results = filter_tokens(results, limit)
        logger.debug('Filtered results size: %i', len(results))
        results = create_list_from_records(results)
        print('closed')
        session.close()

        return results

    ### GRAFICO 1
    # 统计信息：获取某一时间段内，某个ods或者所有ods的News条数，按照ODS编号排序
    def get_news_per_sdg(self, date_from, date_to, osd=None, entity="", lang='en'):
        print('get_news_per_sdg')
        session = self.neo4j.session()

        query = match_news(lang) + build_datetime_clause("n.date", date_from, date_to)

        if osd and len(osd) > 0:
            query += " AND n.odsID in [" + convert_number_array_to_clause(osd) + "] "

        # if entity and entity != "" and entity.lower() != "all":
        #     # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
        #     query += " AND '{0}' in n.entity".format(entity.lower())
        #     # query += " AND '{0}' in n.entity".format(entity)
        if entity and len(entity) > 0 and entity[0].lower() != "all":
            # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
            query += " AND ("

            for ent in entity:
                query += "('{0}' in n.entity) OR ".format(ent.replace("'", "\\'"))

            query = query[0:-3] + ") "

        query += " RETURN n.odsID as ods, count(n) as total ORDER BY n.odsID"

        sdg_list = create_list_from_records(session.run(query))

        session.close()
        return sdg_list

    ### GRAFICO 2
    # 统计信息：获取某一时间段内，每天有最多News条数的ODS编号、News条数、日期
    def get_ods_per_day(self, date_from, date_to, osd=None, entity="", lang='en'):
        print('get_ods_per_day')

        # MATCH (n:News_en {isitODS : 1} ) WHERE datetime(n.date)  >= datetime('2020-05-18T00:00:00')  AND datetime(n.date) < datetime('2020-05-20T00:00:00')
        # AND not n.odsID = 0
        # with date(datetime(n.date)) as date, n.odsID as ODS, count(n.id) as total return date, ODS, total order by total desc, date desc
        session = self.neo4j.session()

        query = match_news(lang) + build_datetime_clause("n.date", date_from, date_to)

        if osd and len(osd) > 0:
            query += " AND n.odsID in [" + convert_number_array_to_clause(osd) + "] "

        # if entity and entity != "" and entity.lower() != "all":
        #     # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
        #     query += " AND '{0}' in n.entity".format(entity.lower())
        #     # query += " AND '{0}' in n.entity".format(entity)
        if entity and len(entity) > 0 and entity[0].lower() != "all":
            # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
            query += " AND ("

            for ent in entity:
                query += "('{0}' in n.entity) OR ".format(ent.replace("'", "\\'"))

            query = query[0:-3] + ") "

        query += " with date(datetime(n.date)) as day, n.odsID as ods, count(n.id) as total return day, ods, total order by day asc, total desc "

        # print('query', query)
        records = session.run(query)

        results = []
        days = set()
        for record in records:
            day = record['day']
            if not day in days:
                results.append(record)
                days.add(day)

        results = json.loads(create_list_from_records(results))
        session.close()

        return results

    ### GRAFICO
    # 统计信息：获取某一新闻的所有ODS分数
    def get_ods_scores(self, news_id, lang):
        print('get_ods_scores')
        session = self.neo4j.session()

        query = "MATCH (n:News_{0})-[r:NEWS_ODS_{0}]-(o:ODS_{0}) " \
                "WHERE n.id='{1}' " \
                "RETURN o.id as id, r.peso as peso ORDER BY peso desc".format(lang, news_id)

        results = json.loads(create_list_from_records(session.run(query)))

        session.close()
        return results

    ### GRAFICO
    # 统计信息：获取某一时间段内，某个entity或者所有entity的News条数，按照entity排序
    def get_news_per_entity(self, date_from, date_to, osd=None, entity=None, lang='en'):
        print('get_news_per_entity')
        session = self.neo4j.session()

        query = match_news(lang) + build_datetime_clause("n.date", date_from, date_to)

        if osd and len(osd) > 0:
            query += " AND n.odsID in [" + convert_number_array_to_clause(osd) + "] "

        # if entity and entity != "" and entity.lower() != "all":
        #     # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
        #     query += " AND '{0}' in n.entity".format(entity.lower())
        #     # query += " AND '{0}' in n.entity".format(entity)
        if entity and len(entity) > 0 and entity[0].lower() != "all":
            # query += " AND toLower(n.entity)='{0}'".format(entity.lower())
            query += " AND ("

            for ent in entity:
                query += "('{0}' in n.entity) OR ".format(ent.replace("'", "\\'"))

            query = query[0:-3] + ") "

        query += " RETURN n.entity as entity, count(n) as total ORDER BY n.entity"

        entity_list = create_list_from_records(session.run(query))

        session.close()
        return entity_list

# if __name__ == '__main__':
#     CFG_PATH = '../config/config.json'
#
#     with open(CFG_PATH, encoding='utf-8-sig') as file:
#         CONFIG = json.load(file)
#
#     user = CONFIG['neo4j']['user']
#     url = CONFIG['neo4j']['url']
#     password = CONFIG['neo4j']['password']
#     n4j_conn = N4jConnector(url, user=user, password=password)
#
#     import datetime
#     date_from = '2022-01-01'
#     date_to = '2022-12-31'
#     DATE_FORMAT = '%Y-%m-%d'
#     from_date = datetime.datetime.strptime(date_from, DATE_FORMAT)
#     to_date = datetime.datetime.strptime(date_to, DATE_FORMAT)
#     to_date = to_date + timedelta(days=1)
#
#     sdg = None
#     news_limit = CONFIG['news_limit']
#     entity = "World Bank"
#
#     news = n4j_conn.get_range_news(from_date, to_date, osd=sdg, limit=news_limit, entity=entity)
#     print(news)
#     output = json.loads(news)
#     print(output)

