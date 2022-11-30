from logger import logger
from nlp.tagger import spacy_ner_tagger
from scrapper.scrapper import scrapper
from extractors.news_api import NewsAPI
from extractors.twitter_api import TwitterAPI


def main():
    """
    logger.debug('Clearing previously stored data')
    result = mongokit_connector.KGNews.test_news.delete_many({})
    logger.debug(f'Removed {result.deleted_count} elements')
    """

    extractor = NewsAPI(language='es')
    # extractor = TwitterAPI(language='es')

    logger.debug(f'Executing extractor {extractor.get_name()}')
    extractor.run()

    extractor = NewsAPI(language='en')

    logger.debug(f'Executing extractor {extractor.get_name()}')
    extractor.run()

    logger.debug('Parsing extracted content')
    scrapper.parse()

    logger.debug('Tagging parsed content')
    spacy_ner_tagger.tag()


if __name__ == '__main__':
    # mongokit.set_entity_empty()
    main()
