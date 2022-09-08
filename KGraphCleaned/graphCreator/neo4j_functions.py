# Funciones Neo4J
import neo4j
from neo4j import GraphDatabase
from multiprocessing import Pool
import sys

url = "bolt://192.168.75.132:7687"
user = "neo4j"
password = "~~86*trust*SORRY*talk*55~~"

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


def crea_ods(myid, lang):
    session = driver.session()
    tx = session.begin_transaction()
    command = "CREATE (ods0: ODS_{0} {{id: '{1}', nombre:'Mi articulo'}})".format(lang, myid)
    tx.run(command)
    tx.commit()
    session.close()


def borra_articulo(myid, lang):
    session = driver.session()
    tx = session.begin_transaction()
    command = "MATCH (n:ODS_{0} {{id: '{1}'}}) DETACH DELETE n".format(lang, myid)
    tx.run(command)
    tx.commit()
    session.close()


def limpia_grafo(lang):
    session = driver.session()
    tx = session.begin_transaction()
    command = "MATCH (n:ODS_{0}) " \
              "WHERE NOT n.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] DETACH DELETE n".format(lang)
    tx.run(command)
    tx.commit()
    session.close()
    borra_huerfanos(lang)


# def add_token(text, tag, concept, lang):
#    neo4j = GraphDatabase.driver(url,auth=(user, password))
#    l.acquire()
#    session = neo4j.session()
#    #try:
#    result = session.run("MATCH (to:Token" + "_" + lang + " {text: '" + text + "'}) RETURN to.text")
#    if result.single() == None:
#        tx = session.begin_transaction()
#        tx.run("CREATE (to:Token" + "_" + lang + " {text: '" + text + "', tag: '" + tag + "', concept: '" + concept + "'})")
#        tx.commit()
#    session.close()
#    l.release()


def inserta_relacion_token_ODS(concept, id_ods, num_token, date, lang):
    session = driver.session()
    command = "MATCH (od:ODS_{0} {{id: '{1}'}})-[r:RELEVANCIA_{0}]->(to:Token_{0} {{concept: '{2}'}}) " \
              "RETURN r.peso".format(lang, id_ods, concept)
    result = session.run(command)
    value = result.value()

    if not value:
        tx = session.begin_transaction()
        command = "MATCH (to:Token_{0} {{concept: '{1}'}}) " \
                  "MATCH (od:ODS_{0} {{id: '{2}'}}) " \
                  "CREATE (od)-[:RELEVANCIA_{0} {{peso: {3}, date: '{4}'}}]->(to)".format(lang, concept, id_ods,
                                                                                          1 / num_token, date)
        tx.run(command)
        tx.commit()
    else:
        weight = value[0] + 1
        tx = session.begin_transaction()
        command = "MATCH (od:ODS_{0} {{id: '{1}'}})-[r:RELEVANCIA_{0}]->(to:Token_{0} {{concept: '{2}'}}) " \
                  "SET r.peso = {3} RETURN r.peso".format(lang, id_ods, concept, str(weight + (1 / num_token)))
        tx.run(command)
        tx.commit()
    session.close()


def consulta_similaridad(myid, lang):
    session = driver.session()
    command = "CALL algo.nodeSimilarity.stream('ODS_{0} | Token_{0}', 'RELEVANCIA_{0}', {{topK:200}}) " \
              "YIELD node1, node2, similarity " \
              "WHERE algo.asNode(node1).id = '{1}' " \
              "AND algo.asNode(node2).id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] " \
              "RETURN algo.asNode(node1).id AS ID1, algo.asNode(node1).nombre AS ODS1, " \
              "algo.asNode(node2).id AS ID2, algo.asNode(node2).nombre AS ODS2, similarity " \
              "ORDER BY ID1 ASCENDING, similarity DESCENDING".format(lang, myid)
    result = session.run(command)
    values = result.values()
    session.close()

    return values


def similaridad_cosenos(myid, lang):
    session = driver.session()
    command = "MATCH (o1:ODS_{0} {{id: '{1}'}})-[r1:RELEVANCIA_{0}]->(Token_{0}) " \
              "MATCH (o2:ODS_{0})-[r2:RELEVANCIA_{0}]->(Token_{0}) " \
              "WHERE o2.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]  " \
              "RETURN o1.id as Mi_Articulo, o2.id as Otro, o2.nombre as Nombre, " \
              "algo.similarity.cosine(collect(r1.peso), collect(r2.peso)) AS similarity " \
              "ORDER BY similarity DESC".format(lang, myid)
    result = session.run(command)
    values = result.values()
    session.close()

    return values


def similaridad_pearson(myid, lang):
    session = driver.session()
    command = "MATCH (o1:ODS_{0} {{id: '{1}'}})-[r:RELEVANCIA_{0}]->(Token_{0}) " \
              "WITH o1, algo.similarity.asVector(Token, r.peso) AS p1Vector " \
              "MATCH (o2:ODS_{0})-[r:RELEVANCIA_{0}]->(Token_{0}) " \
              "WHERE (o2.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]) " \
              "WITH o1, o2, p1Vector, algo.similarity.asVector(Token, r.peso) AS p2Vector " \
              "RETURN o1.id AS from, o2.id AS to, o2.nombre AS toODS, " \
              "algo.similarity.pearson(p1Vector, p2Vector, {{vectorType: 'maps'}}) AS similarity " \
              "ORDER BY similarity DESC".format(lang, myid)
    result = session.run(command)
    values = result.values()
    session.close()

    return values


def peso_de_token(concept, lang):
    session = driver.session()
    command = "MATCH (to:Token_{0} {{concept: '{1}'}})-[r:RELEVANCIA_{0}]-(o:ODS_{0}) " \
              "WHERE o.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] " \
              "RETURN DISTINCT to.text, o.id, r.peso ORDER BY o.id ASC".format(lang, concept)
    result = session.run(command)

    # result = session.run("MATCH (o:ODS" + "_" + lang + ")-[r:RELEVANCIA" + "_" + lang + "]->(to:Token" + "_" + lang +
    #                      " {text: '" + token + "'}) WHERE o.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] RETURN DISTINCT to.text, o.id, r.peso ORDER BY o.id ASC")
    values = result.values()
    session.close()

    return values


def borra_huerfanos(lang):
    session = driver.session()
    result = session.run("MATCH (n) WHERE size((n)--())=0 DELETE (n)")
    values = result.values()
    session.close()

    return values


def porcientos(lang):
    session = driver.session()
    command = "match (o:ODS_{0})-[r:RELEVANCIA_{0}]-(t:Token_{0}) " \
              "WHERE o.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] " \
              "RETURN o.id, sum(r.peso) ORDER BY o.id".format(lang)
    result = session.run(command)
    values = result.values()
    session.close()

    return values


# Funciones para insertar las noticias en el grafo
def add_sentence(text, sentiment, frase_anterior, lang):
    session = driver.session()
    command = "MATCH (se:Sentence_{0} {{text: '{1}'}}) RETURN ID(se)".format(lang, text)
    result = session.run(command)

    if result.single() is None:
        # tx = session.begin_transaction()
        command = "CREATE (a:Sentence_{0} {{text: '{1}', sentiment: '{2}'}}) RETURN ID(a)".format(lang, text, sentiment)
        session.run(command)
        # tx.commit()
    session.close()

    session = driver.session()
    tx2 = session.begin_transaction()
    command = "MATCH (se1:Sentence_{0} {{text: '{1}'}}) " \
              "MATCH (se2:Sentence_{0}) WHERE id(se2)={2} " \
              "CREATE (se1)-[:PREVIOUS_SENTENCE_{0}]->(se2)".format(lang, text, frase_anterior)
    tx2.run(command)
    tx2.commit()
    value = result.value()
    session.close()

    return value


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


def add_News(text, sentiment, _url, _id, date, source, title, image_url, lang):
    session = driver.session()
    command = "MATCH (ne:News_{0} {{text: '{1}'}}) RETURN ne.text".format(lang, text)
    result = session.run(command)

    if result.single() is None:
        tx = session.begin_transaction()
        command = "CREATE (n:News_{0} {{text: '{1}', sentiment: '{2}', url: '{3}', image_url: '{4}', id: '{5}', " \
                  "date: '{6}', source: '{7}', title: '{8}', covid: 0, odsID: 0}})".format(lang, text, sentiment, _url,
                                                                                           image_url, _id, date, source,
                                                                                           title)
        tx.run(command)
        tx.commit()
    session.close()


def add_news_sentence_relation(text, sentence, date, lang):
    # try:
    session = driver.session()
    tx = session.begin_transaction()
    command = "MATCH (ne:News_{0} {{text: '{1}'}}) " \
              "MATCH (se:Sentence_{0} {{text: '{2}'}}) " \
              "CREATE (se)-[:NEWS_SENTENCE_{0} {{date: '{3}'}}]->(ne)".format(lang, text, sentence, date)
    tx.run(command)
    tx.commit()
    session.close()


def add_token_sentence_relation(concept, sentence, entity_type, date, lang):
    # try:
    session = driver.session()
    tx = session.begin_transaction()
    command = "MATCH (en:Token_{0} {{concept: '{1}'}}) " \
              "MATCH (se:Sentence_{0} {{text: '{2}'}}) " \
              "CREATE (en)-[:TOKEN_BELONGS_TO_{0} {{entity_type: '{3}', date: '{4}'}}]->(se)".format(lang, concept,
                                                                                                     sentence,
                                                                                                     entity_type, date)
    tx.run(command)
    tx.commit()
    session.close()


# def add_token_sentence_relation(text, sentence, tag, date, lang):
#     # try:
#     session = driver.session()
#     tx = session.begin_transaction()
#     command = "MATCH (to:Token_{0} {{text: '{1}'}}) " \
#               "MATCH (se:Sentence_{0} {{text: '{2}'}}) " \
#               "CREATE (to)-[:TOKEN_BELONGS_TO_{0} {{semantics: '{3}', date: '{4}'}}]->(se)".format(lang, text, sentence,
#                                                                                                    tag, date)
#     tx.run(command)
#     tx.commit()
#     session.close()


def inserta_relacion_News_ODS(news, pesos, date, maxODS, maxValor, esODS, lang):
    # try:
    session = driver.session()

    i = 1
    for peso in pesos:
        tx = session.begin_transaction()
        command = "MATCH (ne:News_{0} {{text: '{1}'}}) MATCH (od:ODS_{0} {{id: {2}}}) " \
                  "CREATE (od)-[:NEWS_ODS_{0} {{peso: {3}, date: '{4}'}}]->(ne)".format(lang, news, str(i),
                                                                                        str(peso), date)
        tx.run(command)
        i += 1
        tx.commit()

    tx = session.begin_transaction()
    command = "MATCH (ne:News_{0} {{text: '{1}'}}) " \
              "SET ne.odsID = {2}, ne.ODSweight = {3}, ne.isitODS = {4}".format(lang, news, maxODS, maxValor, esODS)
    tx.run(command)
    tx.commit()

    session.close()


def last_id(lang):
    session = driver.session()
    command = "MATCH (n:News_{0}) RETURN max(toInteger(n.id))".format(lang)
    result = session.run(command)
    value = result.value()
    session.close()

    return value


def id_in_graph(lang, id):
    session = driver.session()
    command = "MATCH (n:News_{0}) WHERE n.id = '{1}' RETURN n".format(lang, str(id))
    result = session.run(command)

    if result.single() is None:
        session.close()
        return False
    else:
        session.close()
        return True


def actualiza_covid(news, lang):
    session = driver.session()
    command = "MATCH (n:News_{0})-[r]-(s:Sentence_{0})-[]-(t:Token_{0}) " \
              "WHERE t.text in ['covid', 'coronavirus', 'pandemic', 'covid-19', 'covid 19'] and n.text = '{1}' " \
              "RETURN distinct n".format(lang, news)
    result = session.run(command)

    if result.single() is not None:
        print("La noticia es sobre covid. Texto : " + news)

        tx = session.begin_transaction()
        command = "MATCH (ne:News_{0} {{text: '{1}'}}) SET ne.covid = 1".format(lang, news)
        tx.run(command)
        tx.commit()

    session.close()
