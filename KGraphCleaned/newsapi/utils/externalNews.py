#! /usr/bin/env python

# IMPORTS
from logger import logger
import json
import os
import requests
import datetime

from utils import Constants
from requests.auth import HTTPProxyAuth
from datetime import date
from datetime import timedelta

from interfaces.extractor import Extractor
from utils.mongoConnector import MongoConnector
from logger import logger
from utils.mongokit import news_collection

# PATH = 'C:/Temp/KGRAPH/'
PATH = './output/'

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
BEFORE_YESTERDAY = TODAY - timedelta(days=2)

# FOR PROXIES:
# proxies = {"http": "http://IMM0632:GL080817@proxyvip.igrupobbva:8080", "https": "https://IMM0632:GL080817@proxyvip.igrupobbva:8080"}
proxies = False
auth = HTTPProxyAuth("IMM0632", "GL080817")


## ___________ CLASS DEFINITION ___________________
class NewsAPI(Extractor):
    """
     URL BASE: https://newsapi.org/v2/everything
     API KEY: 1c714b6914ee4d6b81cb156511577bc7
    """

    def __init__(self, language='es', path='./conf/news_api.json'):
        super().__init__()
        self.TODAY_DATE = date.today().strftime('%Y-%m-%d')
        self.API_KEY = '66f22d5add7b47c7b984db75104444b1'   # xin's key
        self.WRITE_CSV = False
        self.BASE_URL = 'https://newsapi.org/v2/everything'

        self.DEFAULT_LANGUAGE = language
        self.mongo_connector = MongoConnector()

        with open(path, encoding='utf-8-sig') as file:
            self.CONFIG = json.load(file)

        self.session = requests.Session()

        print('domains', self.CONFIG['es']['domains'])

    def get_name(self):
        return "newsAPI"

    def can_continue(self):
        return self.BASE_URL is not None \
               and self.API_KEY is not None


    # Gets a list of news
    def get_dataset(self, from_date=None, to_date=None, language=None):
        news = list()
        print('get_dataset FROM ', from_date, ' to ', to_date)
        cont = 0

        if not to_date:
            to_date = self.TODAY_DATE
        if not from_date:
            from_date = self.to_date
        if not language:
            language = self.DEFAULT_LANGUAGE

        payload = {
            'language': language,
            'to': to_date,
            'apiKey': self.API_KEY,
            'domains': self.get_domains(language),
            'sortBy': 'popularity',
            'pageSize': 100
        }
        if from_date:
            payload['from'] = from_date

        kcore = self.CONFIG[language]['queries']
        for k in kcore:
            payload['q'] = k
            # Result
            if proxies:
                result = self.session.get(self.BASE_URL, params=payload, proxies=proxies).json()
            else:
                result = self.session.get(self.BASE_URL, params=payload).json()

            if result.get('status') == 'error':
                print('Error Message:', result.get('message'))
            else:
                total = result.get('totalResults')
                print(self.CONFIG[language]['ods'][cont] + ': \t', total, ' news')

                if result.get('articles'):
                    for art in result.get('articles'):
                        article = self._create_article(art, language)
                        news.append(article)
            cont += 1

        logger.debug(f'Fetched {len(news)} articles from {from_date} to {to_date}')
        return news
        # End function

    def reduce_dataset(self, dataset):
        return dataset

    ##################################


    def get_domains(self, language):
        result = ''
        domains = self.CONFIG[language]['domains']
        print('get_domains(', language, ") ", domains)
        for s in domains:
            if len(result) == 0:
                result = s
            else:
                result = result + ',' + s
        print('get_domains(', language, ") ->", result)
        return result


    # Create Article
    def _create_article(self, art, language):

        if (art.get('publishedAt') is not None)  and len(art['publishedAt']) > 0:
            published_at = self.date_from_news_api(art.get('publishedAt'))
        else:
            dt_utc = datetime.datetime.utcnow()
            published_at = dt_utc.strftime(Constants.DATE_FORMAT)

        #article = mongokit_connector.KGNews.news.Article()
        article = news_collection.Article()
        article['url'] = art.get('url')
        article['title'] = art.get('title')
        article['date'] = published_at
        article['source'] = art.get('source').get('name')
        article['description'] = art.get('description')
        article['author'] = art.get('author')
        article['status'] = "raw"
        article['language'] = language
        article['source_type'] = self.get_name()
        article['tags'] = dict()
        article['content'] = 'N/A'
        return article

    # Transform input date to extractors format. "2020-02-12T00:00:00Z" to "26/03/2020 10:29:34"
    def date_from_news_api(self, input_date):
        d1 = datetime.datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%SZ")
        return d1.strftime(Constants.DATE_FORMAT)

    ##################################


    # WRITE in MONGO
    def write_in_mongo(self, art, language):
        article_i = {
            "url": art.get('url'),
            "title": art.get('title'),
            "date": art.get('publishedAt'),
            "source": art.get('source').get('name'),
            "description": art.get('description'),
            "author": art.get('author'),
            "status": "raw",
            "language": language,
            "source_type": "newsAPI"
        }
        return self.mongo_connector.insert_article(article_i)

    ##
    # Extracts the news from API News
    #
    def extract(self, fromDate, to_date, language='es'):
        print('Start extraction from ', fromDate, ' to ', to_date)

        csv_rows = [Constants.CSV_COLUMNS]
        cont = 0
        inserted_cont = 0

        if not to_date:
            to_date = self.TODAY_DATE

        payload = {
            'language': language,
            'to': to_date,
            'apiKey': self.API_KEY,
            'domains': self.get_domains(language),
            'sortBy': 'popularity',
            'pageSize': 100
        }
        if fromDate:
            payload['from'] = fromDate

        kcore = self.CONFIG[language]['queries']
        for k in kcore:
            payload['q'] = k
            # print(payload)
            # Result
            if proxies:
                result = self.session.get(self.BASE_URL, params=payload, proxies=proxies)
            else:
                result = self.session.get(self.BASE_URL, params=payload)

            smartResult = result.json()

            if smartResult.get('status') == 'error':
                print('Error Message:', smartResult.get('message'))
            else:
                total = smartResult.get('totalResults')
                print(self.CONFIG[language]['ods'][cont] + ': \t', total, ' news')

                if smartResult.get('articles'):
                    for art in smartResult.get('articles'):
                        csv_rows.append([art.get('publishedAt'), 'ODS-' + str(cont + 1), art.get('source').get('name'),
                                         art.get('url'), art.get('title'), art.get('description'), art.get('author')])
                        # WRITE in MONGO
                        res = self.write_in_mongo(art, language)
                        if res:
                            inserted_cont += 1

            cont = cont + 1

        if self.WRITE_CSV:
            excelFileName = PATH + 'News_' + TODAY.strftime('%Y-%m-%d')
            self.write_csv(excelFileName, csv_rows, language)

        print('Extraction from ', fromDate, ' to ', to_date, 'finished!.', inserted_cont, 'articles inserted in Mongo')

    # End function

  #  def extract_last_day(self, language='es'):
  #      self.extract(YESTERDAY.strftime('%Y-%m-%d'), TODAY.strftime('%Y-%m-%d'), language=language)


    def extract_last_day(self, language='es'):
        dataset = self.get_dataset(YESTERDAY.strftime('%Y-%m-%d'), TODAY.strftime('%Y-%m-%d'), language=language)
        result = self._mongodb_output(dataset)
        print (result, 'news inserted')
        #self.extract(YESTERDAY.strftime('%Y-%m-%d'), TODAY.strftime('%Y-%m-%d'), language=language)


    def extract_weekend(self, language='es'):
        print('Extract weekend...')
        self.extract(BEFORE_YESTERDAY.strftime('%Y-%m-%d'), TODAY.strftime('%Y-%m-%d'), language=language)





#extractor = NewsAPI(language='en', path='../conf/news_api.json')

#print('date', extractor.date_from_news_api("2020-02-12T00:00:00Z"))

#print('Dataset', extractor.get_dataset(language='es', from_date=YESTERDAY.strftime('%Y-%m-%d')))

#extractor.extract_last_day('en')
