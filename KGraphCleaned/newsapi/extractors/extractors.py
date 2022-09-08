import logging

from .custom_extractor import CustomExtractor
from .news_api import NewsAPI
from .rss_feeds import RssFeed

__all__ = [
    'extractor_list'
]

logging.debug('Creating extractors list')
extractor_list = list()
#extractor_list.append(CustomExtractor())
#extractor_list.append(RssFeed())
#extractor_list.append(NewsAPI(language='es'))
extractor_list.append(NewsAPI(language='en'))

