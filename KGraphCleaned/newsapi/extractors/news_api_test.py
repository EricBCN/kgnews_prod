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

    def __init__(self, language='es', path=DEFAULT_PATH):

        super().__init__()
        self.TODAY_DATE = date.today().strftime('%Y-%m-%d')
        # self.API_KEY = os.getenv('NEWS_API_KEY') or '1c714b6914ee4d6b81cb156511577bc7'
        self.API_KEY = os.getenv('NEWS_API_KEY') or '66f22d5add7b47c7b984db75104444b1' # Xin's key
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
        to_date = today.strftime('%Y-%m-%d')
        from_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')

        return self.get_dataset_dates(from_date, to_date)
        # End function


    # Gets a list of news
    def get_dataset_dates(self, from_date, to_date):
        news = list()
        cont = 0

        # 'domains': self.get_domains(self.DEFAULT_LANGUAGE),
        payload = {
            'language': self.DEFAULT_LANGUAGE,
            'to': to_date,
            'from': from_date,
            'apiKey': self.API_KEY,
            'excludeDomains': self.get_exclude_domains(self.DEFAULT_LANGUAGE),
            'sortBy': 'popularity',
            'pageSize': 100
        }

        kcore = self.CONFIG[self.DEFAULT_LANGUAGE]['queries']
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
                print(self.CONFIG[self.DEFAULT_LANGUAGE]['ods'][cont] + ': \t', total, ' news')

                if result.get('articles'):
                    for art in result.get('articles'):
                        article = self._create_article(art, self.DEFAULT_LANGUAGE)
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
            if art['url'] not in inserted_urls:
                filtered_dataset.append(art)
                inserted_urls.add(art['url'])

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
    def _create_article(self, art, language):

        if (art.get('publishedAt') is not None)  and len(art['publishedAt']) > 0:
            dt_utc = datetime.datetime.strptime(art.get('publishedAt'), "%Y-%m-%dT%H:%M:%SZ")
            published_at = dt_utc.strftime(Constants.DATE_FORMAT)
            #published_at = self.date_from_news_api(art.get('publishedAt'))
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
        return article

    # Transform input date to extractors format. "2020-02-12T00:00:00Z" to "26/03/2020 10:29:34"
    def date_from_news_api(self, input_date):
        d1 = datetime.datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%SZ")
        return d1.strftime(Constants.DATE_FORMAT)
