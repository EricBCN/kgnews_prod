import concurrent.futures
from boilerpy3 import extractors
from interfaces.scrapper import Scrapper
from logger import logger
from utils import mongokit_connector
from utils.httpSessionWithTimeout import HttpSessionWithTimeout, HEADERS

__all__ = [
    'BoilerpipeScrapper'
]


class BoilerpipeScrapper(Scrapper):
    def allocate_entries(self):
        logger.debug('Finding entries')
        return mongokit_connector.Article.find({'content': 'N/A'})

    def process_entries(self, entries):
        extractor = extractors.ArticleExtractor()
        parsed_entries = list()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # future_to_entry = {executor.submit(extractor.get_content_from_url, entry['url']): entry for entry in entries}

            session = HttpSessionWithTimeout()
            session.headers.update(HEADERS)
            future_to_entry = {executor.submit(session.get, entry['url']): entry for entry in entries}

            for future in concurrent.futures.as_completed(future_to_entry):
                entry = future_to_entry[future]
                try:
                    # entry['content'] = future.result()
                    if future.result().ok:
                        entry['content'] = extractor.get_content(future.result(timeout=5).text)
                    else:
                        logger.error(f'Unable to parse {entry["_id"]}')
                        continue
                except Exception as error:
                    entry['content'] = 'ERROR'
                    logger.error(f'Unable to parse {entry["_id"]}: {error}')
                finally:
                    parsed_entries.append(entry)

        logger.debug(f'Parsed {len(parsed_entries)}/{entries.count()} articles.')
        return parsed_entries
