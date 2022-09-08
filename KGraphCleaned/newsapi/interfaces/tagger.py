import abc

from logger import logger
from utils import mongokit_connector
from utils.mongokit import news_collection

__all__ = [
    'Tagger'
]


class Tagger(metaclass=abc.ABCMeta):
    def tag(self):
        data = self.allocate_data()
        tagged_data = self.find_entities(data)
        self._store_mongodb_results(tagged_data)

    @abc.abstractmethod
    def allocate_data(self):
        pass

    @abc.abstractmethod
    def find_entities(self, entries):
        pass

    def _store_mongodb_results(self, data):
        no_updated = 0
        for article in data:
            result = news_collection.update_one(
                {'_id': article['_id']},
                {
                    '$set': {
                        'tags': article['tags'],
                        'status': 'tags_extracted'
                    }
                }
            )
            no_updated += result.modified_count
        logger.debug(f'Updated {no_updated} articles')
