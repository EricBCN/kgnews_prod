import abc

from logger import logger
from utils import mongokit_connector
from utils.mongokit import news_collection

__all__ = [
    'Scrapper'
]


class Scrapper(metaclass=abc.ABCMeta):
    def parse(self):
        entries = self.allocate_entries()
        entries = self.process_entries(entries)
        self._update_mongodb_entries(entries)

    @abc.abstractmethod
    def allocate_entries(self):
        pass

    @abc.abstractmethod
    def process_entries(self, entries):
        pass

    def _update_mongodb_entries(self, entries):
        no_updated = 0
        for entry in entries:
            result = news_collection.update_one(
                {'_id': entry['_id']},
                {
                    '$set': {
                        'content': entry['content'],
                        'status': 'content_extracted'
                    }
                }
            )
            no_updated += result.modified_count
        logger.debug(f'Updated {no_updated} articles')
