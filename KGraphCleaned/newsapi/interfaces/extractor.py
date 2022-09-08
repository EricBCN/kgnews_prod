import abc
import datetime
import concurrent.futures
from logger import logger
import utils.mongokit as mongokit
from utils.mongokit import news_collection

__all__ = [
    'Extractor'
]


class Extractor(metaclass=abc.ABCMeta):
    def run(self):
        if self.can_continue():
            dataset = self.get_dataset()
            dataset = self.reduce_dataset(dataset)
            self._mongodb_output(dataset)
        else:
            logger.debug('Extract: NONE')

    @abc.abstractmethod
    def get_name(self):
        pass

    def can_continue(self):
        return True

    @abc.abstractmethod
    def get_dataset(self):
        pass

    @abc.abstractmethod
    def reduce_dataset(self, dataset):
        pass

    def _mongodb_output(self, dataset):
        count = 0
        # Generate a list with the urls from the dataset
        urls = list(map(lambda art: art['url'], dataset))
        # Query the mongoDB to retrieve articles with those urls
        result = news_collection.find({'url': {'$in': urls}}, {'url': 1})

        # Generate a list with the urls existing in mongoDB
        stored_urls = list(map(lambda art: art['url'], result))

        # Remove the articles already stored on the database from the dataset
        filtered_dataset = list(filter(lambda art: self._find_url(art, stored_urls), dataset))

        # Store the dataset using a TPE to increase efficiency
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for article in filtered_dataset:
                article["_id"] = mongokit.get_next_id()
                article["timestamp"] = datetime.datetime.utcnow()
                executor.submit(self._store_article, article)
                count += 1

        logger.debug(f'Articles inserted in MongoDB: {count}')
        return count

    def _find_url(self, article, stored_urls):
        return False if article['url'] in stored_urls else True

    def _store_article(self, article):
        article.validate()
        article.save()
