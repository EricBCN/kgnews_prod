import pandas as pd
import re
import datetime
import os
from neo4j import GraphDatabase


url = "bolt://192.168.75.132:7687"
user = "neo4j"
password = "~~86*trust*SORRY*talk*55~~"
filepath_ods = "./corpus/"
driver = GraphDatabase.driver(url, auth=(user, password))


def crea_ods_corpus(id_ods, name_ods, lang):
    session = driver.session()
    command = "MATCH (od:ODS_{0} {{id: {1}}}) RETURN od".format(lang, id_ods)
    result = session.run(command)
    valor = result.value()

    if not valor:
        tx = session.begin_transaction()
        command = "CREATE (ods0: ODS_{0} {{id:{1}, nombre:'{2}'}})".format(lang, id_ods, name_ods)
        tx.run(command)
        tx.commit()
        session.close()


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


def insert_relation_token_ods_import_corpus(text, concept, id_ods, peso, date, lang):
    session = driver.session()
    # command = "MATCH (od:ODS_{0} {{id:{1}}})-[r:RELEVANCIA_{0}]->(to:Token_{0} {{concept: '{2}'}}) " \
    #           "RETURN r.peso".format(lang, id_ods, concept)
    command = "MATCH (od:ODS_{0} {{id:{1}}})-[r:RELEVANCIA_{0}]->(to:Token_{0} {{text: '{2}'}}) " \
              "RETURN r.peso".format(lang, id_ods, text)
    result = session.run(command)
    value = result.value()

    if not value:
        tx = session.begin_transaction()
        # command = "MATCH (to:Token_{0} {{concept: '{1}'}}) MATCH (od:ODS_{0} {{id: {2}}}) " \
        #           "CREATE (od)-[:RELEVANCIA_{0} {{peso: {3}, date: '{4}'}}]->(to)".format(lang, concept, id_ods,
        #                                                                                   peso, date)
        command = "MATCH (to:Token_{0} {{text: '{1}'}}) MATCH (od:ODS_{0} {{id: {2}}}) " \
                  "CREATE (od)-[:RELEVANCIA_{0} {{peso: {3}, date: '{4}'}}]->(to)".format(lang, text, id_ods,
                                                                                          peso, date)
        tx.run(command)
        tx.commit()
    # else:
    #     weight = value[0]
    #     print("Existed: ODS: {0}, Concept: {1}, Text: {2}, Weight: {3}".format(id_ods, concept, text, weight))
    #     print("New: ODS: {0}, Concept: {1}, Text: {2}, Weight: {3}".format(id_ods, concept, text, peso))
    #
    #     tx = session.begin_transaction()
    #     command = "MATCH (od:ODS_{0} {{id: {1}}})-[r:RELEVANCIA_{0}]->(to:Token_{0} {{concept: '{2}'}}) " \
    #               "SET r.peso = {3} RETURN r.peso".format(lang, id_ods, concept, str(weight + float(peso)))
    #     tx.run(command)
    #     tx.commit()
    #
    #     print("After adjusted: ODS: {0}, Concept: {1}, Weight: {2}".format(id_ods, concept, weight + float(peso)))

    session.close()


def create_sdg_from_csv(filename, lang="en"):
    df = pd.read_csv(filename, sep=",")
    date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    for row in df.iterrows():
        ODS = row[1].values[0]
        relation = row[1].values[1]
        token = row[1].values[2]

        ODS_name, ODS_id = re.findall("{nombre:(.*),id:(.*)}", ODS)[0]
        weight = re.findall("{peso:(.*)}", relation)[0]
        concept, text = re.findall("{concept:(.*),text:(.*)}", token)[0]

        crea_ods_corpus(ODS_id, ODS_name, lang)
        add_token(text, concept, lang)
        insert_relation_token_ods_import_corpus(text, concept, ODS_id, weight, date, lang)


if __name__ == "__main__":
    for filename in os.listdir(filepath_ods):
        if not os.path.isdir(filename):
            create_sdg_from_csv(filepath_ods + filename, "en")
            print(filename + " completed.")


