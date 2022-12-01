# -*- coding:utf-8 -*-
import nltk
from nltk.corpus import wordnet

from neo4j import GraphDatabase
from pathlib import Path
from haystack.pipelines import ExtractiveQAPipeline
from haystack.nodes import FARMReader
from itertools import combinations

import spacy
import json
import glob
import datetime
import logging
import gc
import os
from . import constants
from . import common
# import constants

# For Ubuntu Server
import sys


# For Windows Local Test
# from graphCreator.utils import *


DEFAULT_PATH = './conf/workfile.txt'

logger = logging.getLogger('apiLogger')

__all__ = [
    'QueryConnector'
]


# ___________ CLASS DEFINITION ___________________
class QueryConnector:
    def __init__(self, url, user=None, password=None):
        super().__init__()
        self.neo4j = GraphDatabase.driver(url, auth=(user, password))

        # Import 'wordnet' corpus if needed
        nltk.download('wordnet')

        self.language = 'en'
        self.dict = None

        logger.info('load spacy...')

        self.nlp = spacy.load("en_core_web_md")

        print ('spacy loaded')
        logger.info('spacy loaded')

        print('[DEBUG] Create Farm Reader...')

        # Con num_processes limito el número de procesos
        NUM_PROCESSES = 5
        self.reader = FARMReader(model_name_or_path="deepset/roberta-base-squad2", use_gpu=False,
                                 num_processes=NUM_PROCESSES, top_k_per_candidate=3)
        print('[DEBUG] Farm Reader created.')

        logger.info('Farm reader has been created with number of processes: %i', NUM_PROCESSES)
        print('QueryConnector initialized.')

    # Get sentences
    def sentences_for_tokens_v2(self, tokens):
        session = self.neo4j.session()
        clause1 = ""
        i = 1

        for token in tokens[:5]:
            concept = ""
            try:
                print('token', token)
                syns = wordnet.synset(token + ".n.01")
                concept = syns.lemma_names()[0].lower()
            except LookupError as err:
                concept = token.lower()
                print('LookupError in token: ', token)
            except:
                concept = token.lower()

            if (i == 1):
                clause1 += "MATCH (t1:Token_en {concept: '" + concept + "'})-[r1:TOKEN_BELONGS_TO_en]-(s:Sentence_en)-[r1bis:NEWS_SENTENCE_en]-(n:News_en) "
            else:
                clause1 += "MATCH (t" + str(i) + ":Token_en {concept: '" + concept + "'})-[r" + str(i) + ":TOKEN_BELONGS_TO_en]-(s:Sentence_en) "

            #clause1 += "MATCH (n" + str(i) + ":Token_en {concept: '" + concept + "'})-[:TOKEN_BELONGS_TO_en]-(s)-[NEWS_SENTENCE_en]-(n) "

            i += 1

        #clause1 = clause1[:-2]
        #print(clause1 + " return distinct n.title, s.text, n.url")
        result = session.run(clause1 + " return distinct n.title, s.text, n.url, n.source")    #result = session.run(clause1 + " RETURN distinct n.title, s.text, n.url ORDER BY n.title")
        session.close()
        return result.values()

    # Get sentences
    def sentences_for_tokens_v3(self, tokens, date_from=None, to_date=None):
        session = self.neo4j.session()
        clause1 = ""
        i = 1

        for token in tokens[:5]:
            # try:
            #     print('token', token)
            #     syns = wordnet.synset(token + ".n.01")
            #     concept = syns.lemma_names()[0].lower()
            # except LookupError as err:
            #     concept = token.lower()
            #     print('LookupError in token: ', token)
            # except:
            #     concept = token.lower()

            concept = common.get_concept(token, self.language, self.dict)

            if i == 1:
                clause1 += "MATCH (t1:Token_{0} {{concept: '{1}'}})-[r1:TOKEN_BELONGS_TO_{0}]-(s:Sentence_{0})-" \
                           "[r1bis:NEWS_SENTENCE_{0}]-(n:News_{0}) ".format(self.language, concept)
            else:
                clause1 += "MATCH (t{0}:Token_{1} {{concept: '{2}'}})-[r{0}:TOKEN_BELONGS_TO_{1}]-" \
                           "(s:Sentence_{1}) ".format(str(i), self.language, concept)

            #clause1 += "MATCH (n" + str(i) + ":Token_en {concept: '" + concept + "'})-[:TOKEN_BELONGS_TO_en]-(s)-[NEWS_SENTENCE_en]-(n) "

            i += 1

        query = clause1 + " return distinct n.title, s.text, n.url, n.source, n.date"

        print("query:", query)
        result = session.run(query)
        values = result.values()
        session.close()

        return values

    # Get answers in a separate thread
    def get_answers_th(self, question, readers=3,  candidates=40, date_from=None, to_date=None, lang='en'):
        if lang == "es":
            self.nlp = spacy.load("es_core_news_sm")
        else:
            self.nlp = spacy.load("en_core_web_md")

        self.language = lang
        self.dict = common.get_dict_from_file(lang)

        print('get_answers_thread')
        from multiprocessing.pool import ThreadPool
        pool = ThreadPool(processes=1)
        async_result = pool.apply_async(self.get_answers, (question, date_from, to_date, readers, candidates))
        # do some other stuff in the main process
        return_value = async_result.get()
        pool.close()
        pool.terminate()

        return return_value

    # Get answers
    def get_answers(self, question,  date_from=None, to_date=None, readers=3, candidates=40):
        print('get answers:', question, ', from: ', date_from, ', to: ', to_date)
        logger.info('get answers: ' + question)

        # Get all tokens except stopwords
        frases = self.nlp(question)
        words = [token.lemma_.lower() for token in frases if token.is_stop is not True and token.is_alpha and len(token.lemma_) > 1]
        texts = []

        print('words:', str(words))

        if len(words) > 1:
            for i in range(len(words), 1, -1):
                comb = combinations(words, i)

                # Print the obtained combinations
                for i in list(comb):
                    print(i)
                    texts += self.sentences_for_tokens_v3(i, date_from, to_date)
                if len(texts) > 1:
                    break
        else:
            texts = self.sentences_for_tokens_v3(words, date_from, to_date)

        if len(texts) == 0:
            print("TEXTS are empty!")
            print('words:', str(words))
            return "[]"
        else:
            print('total texts_en: ' + str(len(texts)))

        print("creando directorio temporal....")
        temp_path = '../datos/temporal/' + datetime.datetime.now().strftime("temp%H%M-%S-%f")
        Path(temp_path).mkdir(parents=True, exist_ok=True)

        i = 0
        files = 0
        for text in texts:
            if text[0] is not None:
                # check date
                if check_date(text[4], date_from, to_date):
                    f = open(temp_path + '/workfile' + str(i) + '.txt', 'w', encoding='utf-8')
                    f.write(text[1] + "\n")
                    f.close()
                    files += 1
                else:
                    print('date ', text[4], ' does not pass the filter')
                    logging.debug('date does not pass filter')
            i += 1

        if files == 0:
            logging.warning('no texts_en found in dates!')
            # Remove temporal path:
            remove_dir(temp_path)
            return "[]"

        # In-Memory Document Store
        print("[DEBUG] In-Memory Document Store")
        from haystack.document_stores.memory import InMemoryDocumentStore
        document_store = InMemoryDocumentStore()

        # Let´s write data to db
        write_documents_to_db(document_store=document_store, document_dir=temp_path + "/", only_empty_db=True,
                              split_paragraphs=True)

        # An in-memory TfidfRetriever based on Pandas dataframes
        from haystack.nodes.retriever import TfidfRetriever
        retriever = TfidfRetriever(document_store=document_store)

        print('[DEBUG] Create Finder...')
        pipe = ExtractiveQAPipeline(self.reader, retriever)

        print('[DEBUG] get_answers. Candidates number: ', candidates)
        # You can configure how many candidates the reader and retriever shall return
        # The higher top_k_retriever, the better (but also the slower) your answers.
        #respuestas = finder.get_answers(question=question, top_k_retriever=10, top_k_reader=5)
        answers = pipe.run(
            query=question, params={"Retriever": {"top_k": candidates}, "Reader": {"top_k": readers}}
        )

        results = []

        contexts = set()

        for answer in answers['answers']:
            context = answer.context
            if context not in contexts:
                for text in texts:
                    if text[0] is not None:
                        if context.replace("\n", "") in text[1]:
                            answer.title = text[0]
                            answer.url = text[2]
                            answer.source = text[3]
                            answer.date = text[4]
                            break

                to_dict = answer.__dict__
                to_dict['offset_start_in_doc'] = to_dict['offsets_in_document'][0].start
                to_dict['offset_end_in_doc'] = to_dict['offsets_in_document'][0].end
                to_dict['offset_start'] = to_dict['offsets_in_context'][0].start
                to_dict['offset_end'] = to_dict['offsets_in_context'][0].end
                to_dict.pop('__initialised__')
                to_dict.pop('offsets_in_document')
                to_dict.pop('offsets_in_context')

                to_json = json.dumps(to_dict)
                results.append(to_json)
                contexts.add(context)
            else:
                print('context already exits:', context, '  in ', contexts)

        # Remove temporal path:
        remove_dir(temp_path)

        gc.collect()

        return create_list_from_records(results)


# haystack旧版本函数
def write_documents_to_db(document_store, document_dir, clean_func=None, only_empty_db=False, split_paragraphs=False):
    """
    Write all text files(.txt) in the sub-directories of the given path to the connected database.
    :param document_dir: path for the documents to be written to the database
    :param clean_func: a custom cleaning function that gets applied to each doc (input: str, output:str)
    :param only_empty_db: If true, docs will only be written if db is completely empty.
                              Useful to avoid indexing the same initial docs again and again.
    :return: None
    """
    file_paths = Path(document_dir).glob("**/*.txt")

    # check if db has already docs
    if only_empty_db:
        n_docs = document_store.get_document_count()
        if n_docs > 0:
            logger.info(f"Skip writing documents since DB already contains {n_docs} docs ...  "
                        "(Disable `only_empty_db`, if you want to add docs anyway.)")
            return None

    # read and add docs
    docs_to_index = []
    doc_id = 1
    for path in file_paths:
        with open(path, encoding="utf-8") as doc:
            text = doc.read()
            if clean_func:
                text = clean_func(text)

            if split_paragraphs:
                for para in text.split("\n\n"):
                    if not para.strip():  # skip empty paragraphs
                        continue
                    docs_to_index.append(
                        {
                            "content": para,
                            "meta": {
                                'filepath': path.name
                            }
                        }
                    )
                    doc_id += 1
            else:
                docs_to_index.append(
                    {
                        "content": text,
                        "meta": {
                            'filepath': path.name
                        }
                    }
                )
    document_store.write_documents(docs_to_index)
    logger.info(f"Wrote {len(docs_to_index)} docs to DB")


def create_list_from_records(records):
    json_output ='['
    first = True
    for record in records:
        if first:
            json_output += str(record)
            first = False
        else:
            json_output += ' , ' + str(record)

    json_output += ']'
    return json_output


def remove_dir(path):
    print('Remove temporal path: ', path)
    files = glob.glob(path + '/*')
    for f in files:
        os.remove(f)
    Path(path).rmdir()


def check_date(input_date, from_date, to_date):
    result = True
    if from_date and to_date:
        logger.debug('check date ' + input_date + ' from ' +  from_date.strftime(constants.NEO4J_FORMAT) + ' to ' + to_date.strftime(constants.NEO4J_FORMAT))
        date = datetime.datetime.strptime(input_date, constants.NEO4J_FORMAT)
        result = from_date <= date <= to_date
    return result

"""
qconn = QueryConnector(user, password)
#print_answers(get_answers("en", "What contaminates more?"), details="all")

print("sentences", qconn.sentences_for_tokens_v2(['coronavirus', 'sostenibilidad', 'Madrid']))
"""

if __name__ == '__main__':
    question = 'Qué es ODS'
    date_from = '2020-01-01'
    to_date = '2023-01-01'
    DATE_FORMAT = '%Y-%m-%d'
    lang = 'es'

    date_from = datetime.datetime.strptime(date_from, DATE_FORMAT)
    to_date = datetime.datetime.strptime(to_date, DATE_FORMAT)
    to_date = to_date + datetime.timedelta(days=1)

    # user = password = None
    CFG_PATH = '../config/config.json'

    with open(CFG_PATH, encoding='utf-8-sig') as file:
        CONFIG = json.load(file)

    user = CONFIG['neo4j']['user']
    password = CONFIG['neo4j']['password']
    url = CONFIG['neo4j']['url']

    query_connector = QueryConnector(url, user=user, password=password)
    result = query_connector.get_answers_th(question, date_from=date_from, to_date=to_date, readers=3, lang=lang)
    print(result)
    
