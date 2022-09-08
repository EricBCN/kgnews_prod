import json

from interfaces.extractor import Extractor
from logger import logger
from utils import mongokit_connector


class CustomExtractor(Extractor):
    def __init__(self):
        with open('./conf/urls.json') as file:
            self.content = json.load(file)

    def get_name(self):
        return 'CUSTOM_EXTRACTOR'

    def get_dataset(self):
        results = list(map(self._create_article, self.content))
        logger.debug(f'Fetched {len(results)} articles')
        return results

    def reduce_dataset(self, dataset):
        return dataset

    def _create_article(self, article_url):
        article = mongokit_connector.KGNews.test_news.Article()
        article['language'] = 'es'
        article['author'] = 'N/A'
        article['title'] = 'N/A'
        article['description'] = 'N/A'
        article['url'] = article_url
        article['source'] = 'N/A'
        article['source_type'] = self.get_name()
        article['tags'] = dict()
        article['content'] = 'N/A'

        return article
