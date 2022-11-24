import requests
import json
import datetime
from boilerpy3 import extractors
import concurrent.futures

from logger import logger
from interfaces.extractor import Extractor
from utils.mongokit import news_collection
from utils import Constants
from utils.httpSessionWithTimeout import HttpSessionWithTimeout, HEADERS


__all__ = [
    'TwitterAPI'
]

DEFAULT_PATH = './conf/news_api.json'


# ___________ CLASS DEFINITION ___________________
class TwitterAPI(Extractor):
    def __init__(self, language='es', path=DEFAULT_PATH):
        super().__init__()
        self.TODAY_DATE = datetime.date.today().strftime('%Y-%m-%d')
        self.BEARER_TOKEN = 'AAAAAAAAAAAAAAAAAAAAAHCVjgEAAAAAgfqWXVJEf5GD5WZLNVsdEuOSA9A%3De0wLxKnnfanFOOERkxyZadSwsmaBfuJCVBD0OzdcZxjux7tv1C'
        self.SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
        self.DEFAULT_LANGUAGE = language

        with open(path, encoding='utf-8-sig') as file:
            self.CONFIG = json.load(file)

        self.session = requests.Session()

    @staticmethod
    def get_name():
        return "twitterAPI"

    def can_continue(self):
        return self.SEARCH_URL is not None \
               and self.BEARER_TOKEN is not None \
               and self.CONFIG is not None

    # Gets a list of news
    def get_dataset(self):
        today = datetime.date.today()
        from_date = today.strftime('%Y-%m-%d') + "T00:00:00Z"
        to_date = today.strftime('%Y-%m-%d') + "T23:59:59Z"

        return self.get_dataset_dates(from_date, to_date)
        # End function

    # Gets a list of news
    def get_dataset_dates(self, from_date, to_date):
        news = list()
        entities = self.CONFIG[self.DEFAULT_LANGUAGE]['entities']

        for entity in entities:
            print(entity)
            entity = 'CaixaBank'

            try:
                # data = self.search_twitters(entity=entity,
                #                             from_date=from_date,
                #                             to_date=to_date)
                data = self.load_json("results.txt")

                for tweet in data:
                    arts = self.analyze_twitters(tweet)

                    for art in arts:
                        article = self._create_article(art=art, language=self.DEFAULT_LANGUAGE, entity=entity)
                        news.append(article)

                logger.debug(f'Fetched {len(news)} articles from {from_date} to {to_date}')
                return news
            except Exception as err:
                print('Error Message: ' + str(err))

        return None
        # End function

    def bearer_oauth(self, r):
        r.headers["Authorization"] = f"Bearer {self.BEARER_TOKEN}"
        r.headers["User-Agent"] = "v2RecentSearchPython"
        return r

    def search_twitters(self, entity, from_date, to_date):
        params = {'query': entity,
                  'tweet.fields': 'id,author_id,lang,created_at,entities,geo,text',
                  'start_time': from_date,
                  'end_time': to_date,
                  'max_results': '100'}

        response = requests.get(self.BASE_URL, auth=self.bearer_oauth, params=params)
        print(response.status_code)

        if response.status_code != 200:
            raise Exception(response.status_code, response.text)

        json_response = response.json()
        data = json_response['data']
        next_token = json_response['meta']['next_token']

        while next_token:
            params = {
                'query': entity,
                'tweet.fields': 'id,author_id,lang,created_at,entities,geo,text',
                'max_results': '100',
                'next_token': next_token
            }

            response = requests.get(self.BASE_URL, auth=self.bearer_oauth, params=params)

            if response.status_code != 200:
                raise Exception(response.status_code, response.text)

            json_response = response.json()
            data.extend(json_response['data'])
            next_token = json_response['meta']['next_token']

        return json.dumps(data, indent=4, sort_keys=True)

    @staticmethod
    def store_json(filepath, data):
        with open(filepath, 'w') as f:
            f.write(data)

    @staticmethod
    def load_json(filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
            return data

    @staticmethod
    def analyze_twitters(tweet):
        articles = list()

        try:
            if 'lang' in tweet and tweet['lang'] == 'es':
                if 'entities' in tweet and 'urls' in tweet['entities']:
                    for link in tweet['entities']['urls']:
                        if 'url' in link and 'title' in link:
                            art = {
                                'title': link['title'],
                                'description': link['description'] if 'description' in link else '',
                                'url': link['url'],
                                'publishedAt': tweet['created_at']
                            }

                            articles.append(art)
        except Exception as e:
            print(e)

        return articles

    # Remove duplicated news:
    def reduce_dataset(self, dataset):
        parsed_entries = list()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_entry = {executor.submit(self.update_content, data): data for data in dataset[:100]}

            for future in concurrent.futures.as_completed(future_to_entry):
                entry = future_to_entry[future]
                parsed_entries.append(entry)
                print(len(parsed_entries))

        filtered_dataset = []
        inserted_urls = set()

        for art in parsed_entries:
            entity = art['entity'][0].lower()

            if entity not in art['title'].lower() and entity not in art['content'].lower():
                continue
            elif art is not None and art['url'] not in inserted_urls:
                filtered_dataset.append(art)
                inserted_urls.add(art['url'])

            # print(len(filtered_dataset))

        # Remove the articles already stored on the database from the dataset
        print('dataset size: ', len(filtered_dataset))
        return filtered_dataset

    @staticmethod
    def update_content(article):
        try:
            extractor = extractors.ArticleExtractor()
            session = HttpSessionWithTimeout()

            resp = session.head(article['url'], allow_redirects=True)
            url = resp.url

            session.headers.update(HEADERS)
            response = session.get(url)
            article['content'] = extractor.get_content(response.text)
            article['url'] = url if len(url) > 0 else article['url']
        finally:
            return article

    # Create Article
    def _create_article(self, art, language, entity):
        if (art.get('publishedAt') is not None) and len(art['publishedAt']) > 0:
            dt_utc = datetime.datetime.strptime(art.get('publishedAt'), "%Y-%m-%dT%H:%M:%S.%fZ")
            published_at = dt_utc.strftime(Constants.DATE_FORMAT)
        else:
            dt_utc = datetime.datetime.utcnow()
            published_at = dt_utc.strftime(Constants.DATE_FORMAT)

        article = news_collection.Article()
        article['url'] = art.get('url')
        article['title'] = art.get('title')
        article['date'] = published_at
        article['source'] = 'twitter'
        article['description'] = art.get('description')
        article['author'] = ''
        article['status'] = "raw"
        article['language'] = language
        article['source_type'] = self.get_name()
        article['tags'] = dict()
        article['content'] = 'N/A'
        article['published_at'] = dt_utc
        article['entity'] = [entity.lower()] if entity != "" else []

        return article
