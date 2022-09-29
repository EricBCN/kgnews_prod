import json
import os
import datetime
from datetime import date
from datetime import timedelta
from logger import logger

import requests
from requests.auth import HTTPProxyAuth

from interfaces.extractor import Extractor
from utils.mongokit import news_collection
from utils import Constants

__all__ = [
    'NewsAPI'
]


DEFAULT_PATH = './conf/news_api.json'

# FOR PROXIES:
# proxies = {"http": "http://IMM0632:GL080817@proxyvip.igrupobbva:8080", "https": "https://IMM0632:GL080817@proxyvip.igrupobbva:8080"}
proxies = False
auth = HTTPProxyAuth("IMM0632", "GL080817")


## ___________ CLASS DEFINITION ___________________
class NewsAPI(Extractor):

    def __init__(self, language='en', path=DEFAULT_PATH):

        super().__init__()
        self.TODAY_DATE = date.today().strftime('%Y-%m-%d')
        # self.API_KEY = os.getenv('NEWS_API_KEY') or '66f22d5add7b47c7b984db75104444b1' # Xin's key
        # self.API_KEY = os.getenv('NEWS_API_KEY') or 'c9c775e2bfcf4537aca5429864f0f3ee'
        self.API_KEY = os.getenv('NEWS_API_KEY') or 'f461eac24b794c38b77506686f72652d'
        self.WRITE_CSV = False
        self.BASE_URL = os.getenv('NEWS_API_URL_BASE') or 'https://newsapi.org/v2/everything'
        self.DEFAULT_LANGUAGE = language

        with open(path, encoding='utf-8-sig') as file:
            self.CONFIG = json.load(file)

        self.session = requests.Session()

    def get_name(self):
        return "newsAPI"

    def can_continue(self):
        return self.BASE_URL is not None \
               and self.API_KEY is not None \
               and self.CONFIG is not None

    # def reduce_dataset(self, dataset):
    #     return dataset


    # Gets a list of news
    def get_dataset(self):
        today = date.today()
        #to_date = today.strftime('%Y-%m-%d')
        to_date = '2022-09-29'
        # Is Monday?
        from_date = '2022-09-01'
        # if today.isoweekday() == 1:
        #     # from_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        #     from_date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
        # else:
        #     from_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')

        return self.get_dataset_dates(from_date, to_date)
        # End function

    # Gets a list of news
    def get_dataset_dates(self, from_date, to_date):
        news = list()

        # 'domains': self.get_domains(self.DEFAULT_LANGUAGE),
        payload = {
            'language': self.DEFAULT_LANGUAGE,
            'to': to_date,
            'from': from_date,
            'apiKey': self.API_KEY,
            'excludeDomains': self.get_exclude_domains(self.DEFAULT_LANGUAGE),
            'sortBy': 'popularity'
            # 'pageSize': 100
        }

        queries = self.CONFIG[self.DEFAULT_LANGUAGE]['queries']
        entities = self.CONFIG[self.DEFAULT_LANGUAGE]['entities']
        entities.append("")

        for entity in entities:
            print(entity)
            cont = 0

            for query in queries:
                payload['q'] = query + " AND " + "(\"" + entity + "\")" if entity != "" else query

                # Result
                if proxies:
                    result = self.session.get(self.BASE_URL, params=payload, proxies=proxies).json()
                else:
                    result = self.session.get(self.BASE_URL, params=payload).json()

                if result.get('status') == 'error':
                    print('Error Message:', result.get('message'))
                else:
                    total = result.get('totalResults')
                    print(self.CONFIG[self.DEFAULT_LANGUAGE]['ods'][cont] + ': \t', total, ' news')

                    if result.get('articles'):
                        for art in result.get('articles'):
                            article = self._create_article(art=art, language=self.DEFAULT_LANGUAGE, entity=entity)
                            news.append(article)
                cont += 1

        logger.debug(f'Fetched {len(news)} articles from {from_date} to {to_date}')
        return news
        # End function

    # Remove duplicated news:
    def reduce_dataset(self, dataset):
        filtered_dataset = []
        inserted_urls = set()
        for art in dataset:
            url = art['url'] if len(art['entity']) == 0 else art['entity'][0] + art['url']
            if url not in inserted_urls:
                filtered_dataset.append(art)
                inserted_urls.add(url)

        # Remove the articles already stored on the database from the dataset
        print('dataset size: ', len(filtered_dataset))
        return filtered_dataset

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
        #print('get_domains(', language, ") ->", result)
        return result


    def get_exclude_domains(self, language):
        result = ''
        domains = self.CONFIG[language]['exclude_domains']
        print('get_domains(', language, ") ", domains)
        for s in domains:
            if len(result) == 0:
                result = s
            else:
                result = result + ',' + s
        #print('get_domains(', language, ") ->", result)
        return result


    # Create Article
    def _create_article(self, art, language, entity):
        if (art.get('publishedAt') is not None)  and len(art['publishedAt']) > 0:
            dt_utc = datetime.datetime.strptime(art.get('publishedAt'), "%Y-%m-%dT%H:%M:%SZ")
            published_at = dt_utc.strftime(Constants.DATE_FORMAT)
        else:
            dt_utc = datetime.datetime.utcnow()
            published_at = dt_utc.strftime(Constants.DATE_FORMAT)

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
        article['published_at'] = dt_utc
        # article['entity'] = [entity] if entity != "" else []
        article['entity'] = [entity.lower()] if entity != "" else []

        return article
