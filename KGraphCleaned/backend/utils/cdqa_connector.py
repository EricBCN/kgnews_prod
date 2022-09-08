import datetime
import logging
import spacy
import json
import re
import pandas as pd
import utils.constants as constants
import nltk
from nltk.corpus import wordnet
from neo4j import GraphDatabase
from cdqa.pipeline import QAPipeline
from itertools import combinations


logger = logging.getLogger('apiLogger')

__all__ = [
    'CdqaConnector'
]


## ___________ CLASS DEFINITION ___________________
class CdqaConnector:

    def __init__(self, user=None, password=None, url=None):
        super().__init__()

        self.neo4j = GraphDatabase.driver(url, auth=(user, password))

        # Import 'wordnet' corpus if needed
        nltk.download('wordnet')

        logger.info('load spacy...')
        self.nlp = spacy.load("en_core_web_md")
        logger.info('spacy loaded')

        logger.info('load pipeline...')
        self.cdqa_pipeline = QAPipeline(reader='./models/bert_qa.joblib')

        logger.info('pipeline loaded')
        logger.info('CdqaConnector initialized.')



    # Get sentences
    def sentences_for_tokens_v2(self, tokens, lang=None):
        #neo4j = GraphDatabase.driver(url,auth=(user, password))
        session = self.neo4j.session()
        clause1 = ""
        i = 1

        for token in tokens[:5]:
            try:
                syns = wordnet.synset(token + ".n.01")
                concept = syns.lemma_names()[0].lower()
            except:
                concept = token.lower()
            #clause1 += "MATCH (n" + str(i) + ":Token_en {concept: '" + concept + "'})-[:TOKEN_BELONGS_TO_en]-(s)-[NEWS_SENTENCE_en]-(n) "
            if (i == 1):
                clause1 += "MATCH (t" + str(i) + ":Token_en {concept: '" + concept + "'})-[r" + str(i) + ":TOKEN_BELONGS_TO_en]-(s:Sentence_en)-[r" + str(i) + "bis:NEWS_SENTENCE_en]-(n:News_en) "
            else:
                clause1 += "MATCH (t" + str(i) + ":Token_en {concept: '" + concept + "'})-[r" + str(i) + ":TOKEN_BELONGS_TO_en]-(s:Sentence_en) "
            #clause2 += "n" + str(i) + ".text = '" + token + "' and "
            i += 1

        #clause2 = "' OR n.text= '".join(token for token in tokens)
        result = session.run(clause1 + " return distinct n.title, s.text, n.url, n.source, n.date")    #result = session.run(clause1 + " RETURN distinct n.title, s.text, n.url ORDER BY n.title")
        session.close()
        return result.values()


    # Get sentences
    def sentences_for_tokens_v3(self, tokens):

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

        query = clause1 + " return distinct n.title, s.text, n.url, n.source, n.date"

        print("query:", query)
        result = session.run(query)
        session.close()
        return result.values()



    # Get answers in a separate thread
    def get_answers_th(self, question, date_from=None, to_date=None, predictions=constants.DEFAULT_QUERY_RESULTS):
        print('get_answers_thread')
        from multiprocessing.pool import ThreadPool
        pool = ThreadPool(processes=1)
        async_result = pool.apply_async(self.get_answers, (question, date_from, to_date, predictions))
        # do some other stuff in the main process
        return_value = async_result.get()
        pool.close()
        pool.terminate()

        return return_value



    def get_answers(self, question, date_from=None, to_date=None, predictions=constants.DEFAULT_QUERY_RESULTS):
        # Get all tokens except stopwords
        frases = self.nlp(question)
        words = [token.lemma_.lower() for token in frases if token.is_stop != True and token.is_alpha and len(token.lemma_) > 1]

        texts = []

        print(str(words))

        if (len(words) > 1):
            for i in range(len(words), 1, -1):
                comb = combinations(words, i)

                # Print the obtained combinations
                for i in list(comb):
                    print(i)
                    texts += self.sentences_for_tokens_v2(i)
                if len(texts) > 2:
                    break
        else:
            texts = self.sentences_for_tokens_v2(words)

        #texts = sentences_for_tokens(words, lang)

        print('texts number', str(len(texts)))

        ready_texts = []
        regex = re.compile('[^a-z A-Z]')

        for texto in texts:
            if check_date(texto[4], date_from, to_date):
                ready_texts.append([regex.sub('', texto[0]), [regex.sub('', texto[1])], texto[2]])


        #print("\n" + str(ready_texts) + "\n")

        #textos = ". ".join(list( dict.fromkeys(str(texts).split(". "))))
        #print(texts)

        print('Ready texts number', str(len(ready_texts)))

        if len(ready_texts) == 0:
            return json.dumps([])

        # Download data and models
        #download_model(model='bert-squad_1.1', dir='./models')

        # Loading data and filtering / preprocessing the documents
        #df = pd.read_csv('data/bnpp_newsroom_v1.1/bnpp_newsroom-v1.1.csv', converters={'paragraphs': literal_eval})
        df = pd.DataFrame(ready_texts, columns=['title', 'paragraphs', 'url'])
        #df['paragraphs'] = df['paragraphs'].apply(lambda x: [x])
        #print(df)

        # Loading QAPipeline with CPU version of BERT Reader pretrained on SQuAD 1.1
        #cdqa_pipeline = QAPipeline(reader='./models/bert_qa.joblib')

        # Fitting the retriever to the list of documents in the dataframe
        self.cdqa_pipeline.fit_retriever(df=df)

        # Sending a question to the pipeline and getting prediction
        #prediction = self.cdqa_pipeline.predict(query=question,  n_predictions=predictions+2)
        prediction = self.cdqa_pipeline.predict(query=question,  n_predictions=predictions+7)
        logger.debug('Prediction: %s',  str(prediction))
        answer = []
        urls = set()

        for predict in prediction:
            resultado = [text for text in texts if predict[2] == regex.sub('', text[1])]

            url = resultado[0][2]
            #context = predict[2]

            if url not in urls:
                answer.append({
                    'answer': predict[0],
                    'score': predict[3],
                    'probability': predict[3],
                    'context':  predict[2],
                    'title': resultado[0][0],
                    'url': url,
                    'source': resultado[0][3],
                    'date': resultado[0][4]
                })
                urls.add(url)
                if len(answer) == predictions:
                    print('break')
                    break
            else:
                logger.debug('news URL already exits: %s', url)

        print(answer)
        #logger.debug('Answer: %s', str(answer))
        return json.dumps(answer)


###
def check_date(input_date, from_date, to_date):
    result = True
    if from_date and to_date:
        #logger.debug('check date ' + input_date + ' from ' +  from_date.strftime(constants.NEO4J_FORMAT) + ' to ' + to_date.strftime(constants.NEO4J_FORMAT))
        date = datetime.datetime.strptime(input_date, constants.NEO4J_FORMAT)
        result = from_date <= date <= to_date
    return result



"""
qconn = QueryConnector(user, password)
#print_answers(get_answers("en", "What contaminates more?"), details="all")

print("sentences", qconn.sentences_for_tokens_v2(['coronavirus', 'sostenibilidad', 'Madrid']))
"""