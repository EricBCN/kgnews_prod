import concurrent.futures
import datetime
import json

import feedparser

from interfaces.extractor import Extractor
from logger import logger
from utils.mongokit import news_collection
from utils import Constants

__all__ = [
    'RssFeed'
]


class RssFeed(Extractor):

    def __init__(self):
        super().__init__()
        # TODO: These can be stored on a MongoDB document, also tracking last fetch time
        # (relevant etags), last update time, etc...
        with open('./conf/sources.json', encoding='utf-8-sig') as file:
            self.FEEDS = json.load(file)

    def get_name(self):
        return 'RSSFEED_EXTRACTOR'

    def get_dataset(self):
        results = list()

        # Parallelize the requests using a TPE
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(feedparser.parse, url): url for url in self.FEEDS}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result()
                    # https://wiki.python.org/moin/RssLibraries
                    # https://pythonhosted.org/feedparser/index.html

                    # 1 if the feed is incorrect
                    # logger.debug(data['bozo'])

                    # https://pythonhosted.org/feedparser/http-etag.html
                    # If sent on subsequent requests, the feed will return 304
                    # if the feed hasn't changed. The etag is not featured by
                    # all of the feeds.
                    # logger.debug(data['etag'] if data.has_key('etag') else 'noetag')

                    # RSS update date
                    # logger.debug(data['updated'])

                    # RSS source
                    # logger.debug(data['href'])

                    feed = data['feed']
                    entries = data['entries']

                    results += map(lambda entry: self._create_article(feed, entry), entries)
                except Exception as exc:
                    logger.error(f'{url} generated an exception: {exc}')

        logger.debug(f'Fetched {len(results)} articles')
        return results

    def reduce_dataset(self, dataset):
        return dataset

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


    def _create_article(self, feed, rss_entry):
        if rss_entry.has_key('published_parsed') \
                and rss_entry['published_parsed'] is not None \
                and len(rss_entry['published_parsed']) > 0:
            t = rss_entry['published_parsed']
            tz = datetime.timezone(datetime.timedelta(seconds=t[-1]))
            dt = datetime.datetime(*t[0:6], tzinfo=tz)
            dt_utc = dt.astimezone(datetime.timezone.utc)
        else:
            dt_utc = datetime.datetime.utcnow()

        article = news_collection.Article()
        article['date'] = dt_utc.strftime(Constants.DATE_FORMAT)
        article['language'] = feed['language'][:2]
        article['author'] = rss_entry['author'] if rss_entry.has_key('author') else 'Unknown'
        article['title'] = rss_entry['title']
        article['description'] = rss_entry['summary'] if rss_entry.has_key('summary') else 'N/A'
        article['url'] = rss_entry['link']
        article['source'] = feed['title']
        article['source_type'] = self.get_name()
        article['tags'] = dict()
        article['content'] = 'N/A'
        article['published_at'] = dt_utc

        return article
