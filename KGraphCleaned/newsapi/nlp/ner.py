import concurrent.futures

import spacy

from interfaces.tagger import Tagger
from logger import logger
from utils import mongokit_connector

__all__ = [
    'SpacyNerTagger'
]


class SpacyNerTagger(Tagger):
    def __init__(self):
        # python -m spacy download en_core_web_sm
        # python -m spacy download es_core_news_sm
        # https://spacy.io/usage/models
        logger.debug('Initializing spaCy NER')
        self.nlp = {
            'en': spacy.load('en_core_web_sm'),
            'es': spacy.load('es_core_news_sm')
        }
        self.INCLUDED_LABELS = ['LOC', 'ORG', 'PER']

    def allocate_data(self):
        return mongokit_connector.Article.find({'tags': dict(), 'content': {'$ne': 'ERROR'}})

    def find_entities(self, documents):
        tagged_docs = list()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_doc = {executor.submit(self.nlp[doc['language'].lower()], doc['content']): doc for doc in documents}

            count = 0
            for future in concurrent.futures.as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    tagged_content = future.result()

                    tag_map = {
                        'LOC': list(),
                        'ORG': list(),
                        'PER': list()
                    }

                    for entity in tagged_content.ents:
                        if entity.label_ in self.INCLUDED_LABELS:
                            tag_map[entity.label_].append(entity.text)

                    """
                    # Statistical purposes only :)
                    labels = [x.label_ for x in doc.ents]
                    logger.debug(f'Extracted labels: {Counter(labels)}')
            
                    items = [x.text for x in doc.ents]
                    logger.debug(f'Most common entities: {Counter(items).most_common(5)}')
                    """

                    doc['tags'] = tag_map
                    count += 1
                    print("successful to get tags")
                    print(count)
                except Exception as error:
                    doc['tags'] = dict({'error': error})
                finally:
                    tagged_docs.append(doc)

        logger.debug(f'Tagged {len(tagged_docs)}/{documents.count()} articles')
        return tagged_docs
