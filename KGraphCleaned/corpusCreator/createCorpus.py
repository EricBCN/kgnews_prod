# import pandas as pd
# import re
from datetime import datetime
import os
from neo4j import GraphDatabase
import spacy
from pymongo import MongoClient
# import nltk
from nltk.corpus import wordnet
# from nltk.stem import WordNetLemmatizer
# from nltk.stem import PorterStemmer
from googletrans import Translator


url = "bolt://127.0.0.1"
user = "neo4j"
password = "~~86*trust*SORRY*talk*55~~"
filepath_ods = "./weights/"
dir_text = "./texts_es/"
driver = GraphDatabase.driver(url, auth=(user, password))
nlp = spacy.load("es_core_news_sm")
translator = Translator()


def create_spanish_sdg_nodes():
    sdg_info = {
        '1': 'Fin de la pobreza',
        '2': 'Hambre cero',
        '3': 'Salud y bienestar',
        '4': 'Educación de calidad',
        '5': 'Igualdad de género',
        '6': 'Agua limpia y saneamiento',
        '7': 'Energía asequible y no contaminante',
        '8': 'Trabajo decente y crecimiento económico',
        '9': 'Industria, innovación e infraestructuras',
        '10': 'Reducción de las desigualdades',
        '11': 'Ciudades y comunidades sostenibles',
        '12': 'Producción y consumo responsables',
        '13': 'Acción por el clima',
        '14': 'Vida submarina',
        '15': 'Vida de ecosistemas terrestres',
        '16': 'Paz, justicia e instituciones',
        '17': 'Alianzas para lograr los objetivos'
    }

    for item in sdg_info.items():
        sdg_id = int(item[0])
        sdg_name = item[1]

        add_sdg(sdg_id, sdg_name, 'es')


# Add sdg nodes
def add_sdg(id_sdg, name, lang):
    session = driver.session()
    command = "MATCH (od:ODS_{0} {{id: {1}}}) RETURN od".format(lang, id_sdg)
    result = session.run(command)
    valor = result.value()

    if not valor:
        tx = session.begin_transaction()
        command = "CREATE (ods0: ODS_{0} {{id:{1}, nombre:'{2}'}})".format(lang, id_sdg, name)
        tx.run(command)
        tx.commit()
        session.close()


# Add token nodes
def add_token(token, concept, lang):
    session = driver.session()

    command = "MATCH (to:Token_{0} {{concept: '{1}'}}) RETURN to.text".format(lang, concept)
    result = session.run(command)

    if result.single() is None:
        tx = session.begin_transaction()
        command = "CREATE (to:Token_{0} {{text: '{1}', concept: '{2}'}})".format(lang, token, concept)
        tx.run(command)
        tx.commit()

    session.close()


def insert_relation_token_sdg(concept, id_sdg, peso, date, lang):
    session = driver.session()
    command = "MATCH (od:ODS_{0} {{id:{1}}})-[r:RELEVANCIA_{0}]->(to:Token_{0} {{concept: '{2}'}}) " \
              "RETURN r.peso".format(lang, id_sdg, concept)
    result = session.run(command)
    value = result.value()

    if not value:
        tx = session.begin_transaction()
        command = "MATCH (to:Token_{0} {{concept: '{1}'}}) MATCH (od:ODS_{0} {{id: {2}}}) " \
                  "CREATE (od)-[:RELEVANCIA_{0} {{peso: {3}, date: '{4}'}}]->(to)".format(lang, concept, id_sdg,
                                                                                          peso, date)
        tx.run(command)
        tx.commit()

    session.close()


def create_sdg_from_text(filepath, id_sdg, encoding, lang):
    dictionary = get_dict_from_file(lang)   # get dictionary

    with open(filepath, "r", encoding=encoding) as f:
        text = f.read()
        sentences = nlp(text)   # analyze the text

        # get tokens
        words = [token.lemma_.lower() for token in sentences
                 if token.is_stop is False and token.is_alpha and len(token.lemma_) > 1]

        dict_weights = {}
        dict_text_concept = {}

        for word in words:
            concept = get_concept(word, lang=lang, dictionary=dictionary)

            if concept not in dict_text_concept:
                dict_text_concept[concept] = word

            if concept in dict_weights:
                dict_weights[concept] += 1 / len(words)
            else:
                dict_weights[concept] = 1 / len(words)

        for item in dict_weights.items():
            concept = item[0]
            weight = item[1]
            add_token(dict_text_concept[concept], concept, lang)
            insert_relation_token_sdg(concept, id_sdg, weight, datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), lang)

        save_dict(dictionary, lang)


def get_concept(word, lang, dictionary=None):
    if word[-3:] == ' él':
        word = word[:-3]

    if lang == 'en':
        word_en = word.replace("\'", "").replace("\\", "")
    else:
        if dictionary is not None and word in dictionary:
            return dictionary[word]     # find the concept of the word in the dictionary
        else:
            word_en = translator.translate(word, src=lang).text.replace("\'", "").replace("\\", "")

    try:
        syns = wordnet.synset(word_en + ".n.01")
        concept = syns.lemma_names()[0]
    except:
        concept = word_en

    dictionary[word] = concept.lower().replace("\'", "").replace("\\", "")  # update dictionary

    return concept.lower().replace("\'", "").replace("\\", "")


# Get dictionary from .txt file
# parameter: language
# result: dictionary
def get_dict_from_file(lang):
    dict_filepath = '../dict/dict_{0}.txt'.format(lang)
    dictionary = {}

    with open(dict_filepath, 'r', encoding='latin-1') as f:
        for line in f.readlines():
            line = line.strip()
            k = line.split(';')[0]
            v = line.split(';')[1]
            dictionary[k] = v

        f.close()
        return dictionary


# Save the updated dictionary
# parameter: dictionary, language
def save_dict(dictionary, lang):
    dict_filepath = '../dict/dict_{0}.txt'.format(lang)
    with open(dict_filepath, 'w', encoding='latin-1') as f:
        items = sorted(dictionary.items(), key=lambda item: item[0])

        for k, v in items:
            try:
                f.write(str(k) + ';' + str(v) + '\n')
            except Exception as e:
                print(e)

        f.close()


def train_dictionary(lang):
    ip = '127.0.0.1'
    port = 27017
    client = MongoClient(ip, port=port)

    db = client.KGNews
    articles = db.news.find({"language": lang}).sort([("_id", 1)])

    count = 0
    for art in articles:
        dictionary = get_dict_from_file(lang)   # get dictionary
        sentences = nlp(art["content"])

        words = [token.lemma_.lower() for token in sentences
                 if token.is_stop is False and token.is_alpha and len(token.lemma_) > 1]

        for word in words:
            get_concept(word, lang=lang, dictionary=dictionary)

        save_dict(dictionary, lang)     # save updated dictionary

        count += 1
        print("{0} articles finished.".format(str(count)))


def update_text_es():
    dictionary = get_dict_from_file('es')

    session = driver.session()
    command = "MATCH (n:Token_es) WHERE n.text = n.concept RETURN n"
    result = session.run(command)

    for value in result.values():
        concept = value[0]['concept']

        for t, c in dictionary.items():
            if c == concept and c != t:
                tx = session.begin_transaction()
                command = "MATCH (n:Token_es) WHERE n.concept = '{0}' SET n.text = '{1}'"\
                          .format(c.replace("\'", "").replace("\\", ""), t.replace("\'", "").replace("\\", ""))
                tx.run(command)
                tx.commit()

    session.close()


def show_example():
    texto = 'abogados abordamos Pese a que la tasa de pobreza mundial se ha reducido a ' \
            'la mitad desde el año 2000, en las regiones en desarrollo ' \
            'aún una de cada diez personas, y sus familias, sigue subsistiendo ' \
            'con 1,90 dólares diarios y hay millones más que ganan poco más que esta cantidad diaria.'

    sentences = nlp(texto)  # analyze the text

    # get tokens
    words = [token.lemma_.lower() for token in sentences if
             token.is_stop is False and token.is_alpha and len(token.lemma_) > 1]

    # tokens = [token for token in sentences if token.is_stop is False and token.is_alpha and len(token.lemma_) > 1]

    print(words)

    concepts = []

    dict_weights = {}
    dictionary = get_dict_from_file('es')  # get dictionary

    for word in words:
        concept = get_concept(word, lang='es', dictionary=dictionary)

        if concept in dict_weights:
            dict_weights[concept] += 1 / len(words)
        else:
            dict_weights[concept] = 1 / len(words)

        concepts.append(concept)

    print(concepts)

    for item in dict_weights.items():
        concept = item[0]
        weight = item[1]
        print('{0} : {1}'.format(concept, weight))


if __name__ == "__main__":
    # create_spanish_sdg_nodes()

    for sdg_number in list(range(1, 18)):
        for filename in os.listdir(dir_text):
            if filename == "ODS" + str(sdg_number) + ".txt":
                create_sdg_from_text(dir_text + filename, sdg_number, encoding="latin-1", lang="es")
                print(sdg_number)

    # train_dictionary('es')

    # update_text_es()


