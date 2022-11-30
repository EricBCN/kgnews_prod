from neo4j import GraphDatabase
import mongo

# from . import mongo   # For backend Local Test

# url_neo4j = "bolt://192.168.75.134:7687"
# url_neo4j = "bolt://127.0.0.1:7687"
url_neo4j = "bolt://172.31.12.215:7687"
user_neo4j = "neo4j"
# password_neo4j = '12345678'
password_neo4j = "~~86*trust*SORRY*talk*55~~"
driver = GraphDatabase.driver(url_neo4j, auth=(user_neo4j, password_neo4j))


def crea_ods_corpus(session, id_ods, name_ods, lang):
    command = "MATCH (od:ODS_{0} {{id: {1}}}) RETURN od".format(lang, id_ods)
    result = session.run(command)
    valor = result.value()

    if not valor:
        tx = session.begin_transaction()
        command = "CREATE (ods0: ODS_{0} {{id:{1}, nombre:'{2}'}})".format(lang, id_ods, name_ods)
        tx.run(command)
        tx.commit()


def crea_ods(session, myid, lang):
    tx = session.begin_transaction()
    command = "CREATE (ods0: ODS_{0} {{id: '{1}', nombre:'Mi articulo'}})".format(lang, myid)
    tx.run(command)
    tx.commit()


def delete_article_ods(session, myid, lang):
    tx = session.begin_transaction()
    command = "MATCH (n:ODS_{0} {{id: '{1}'}}) DETACH DELETE n".format(lang, myid)
    tx.run(command)
    tx.commit()


def limpia_grafo(session, lang):
    tx = session.begin_transaction()
    command = "MATCH (n:ODS_{0}) " \
              "WHERE NOT n.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] DETACH DELETE n".format(lang)
    tx.run(command)
    tx.commit()
    borra_huerfanos(session, lang)


def insert_relation_token_ods(session, token_id, id_ods, num_token, date, lang):
    command = "MATCH (od:ODS_{0} {{id: '{1}'}})-[r:RELEVANCIA_{0}]->(to:Token_{0}) " \
              "WHERE ID(to)={2} " \
              "RETURN r.peso".format(lang, id_ods, token_id)
    result = session.run(command)
    value = result.value()

    if not value:
        tx = session.begin_transaction()
        command = "MATCH (to:Token_{0}) " \
                  "MATCH (od:ODS_{0} {{id: '{2}'}}) " \
                  "WHERE ID(to)={1} " \
                  "CREATE (od)-[:RELEVANCIA_{0} {{peso: {3}, date: '{4}'}}]->(to)".format(lang, token_id, id_ods,
                                                                                          1 / num_token, date)
        tx.run(command)
        tx.commit()
    else:
        weight = value[0] + 1
        tx = session.begin_transaction()
        command = "MATCH (od:ODS_{0} {{id: '{1}'}})-[r:RELEVANCIA_{0}]->(to:Token_{0}) " \
                  "WHERE ID(to)={2} " \
                  "SET r.peso = {3} RETURN r.peso".format(lang, id_ods, token_id, str(weight + (1 / num_token)))
        tx.run(command)
        tx.commit()


def consulta_similaridad(session, myid, lang):
    command = "CALL algo.nodeSimilarity.stream('ODS_{0} | Token_{0}', 'RELEVANCIA_{0}', {{topK:200}}) " \
              "YIELD node1, node2, similarity " \
              "WHERE algo.asNode(node1).id = '{1}' " \
              "AND algo.asNode(node2).id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] " \
              "RETURN algo.asNode(node1).id AS ID1, algo.asNode(node1).nombre AS ODS1, " \
              "algo.asNode(node2).id AS ID2, algo.asNode(node2).nombre AS ODS2, similarity " \
              "ORDER BY ID1 ASCENDING, similarity DESCENDING".format(lang, myid)
    result = session.run(command)
    values = result.values()

    return values


def similaridad_cosenos(session, myid, lang):
    command = "MATCH (o1:ODS_{0} {{id: '{1}'}})-[r1:RELEVANCIA_{0}]->(Token_{0}) " \
              "MATCH (o2:ODS_{0})-[r2:RELEVANCIA_{0}]->(Token_{0}) " \
              "WHERE o2.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]  " \
              "RETURN o1.id as Mi_Articulo, o2.id as Otro, o2.nombre as Nombre, " \
              "algo.similarity.cosine(collect(r1.peso), collect(r2.peso)) AS similarity " \
              "ORDER BY similarity DESC".format(lang, myid)
    result = session.run(command)
    values = result.values()

    return values


def similaridad_pearson(session, myid, lang):
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

    return values


def peso_de_token(session, sentence_id, lang):
    command = "MATCH (to:Token_{0})-[r:RELEVANCIA_{0}]-(o:ODS_{0}) " \
              "WHERE ID(to)={1} AND o.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] " \
              "RETURN DISTINCT to.text, o.id, r.peso ORDER BY o.id ASC".format(lang, sentence_id)
    result = session.run(command)

    # result = session.run("MATCH (o:ODS" + "_" + lang + ")-[r:RELEVANCIA" + "_" + lang + "]->(to:Token" + "_" + lang +
    #                      " {text: '" + token + "'}) WHERE o.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] RETURN DISTINCT to.text, o.id, r.peso ORDER BY o.id ASC")
    values = result.values()

    return values


def borra_huerfanos(session, lang):
    result = session.run("MATCH (n) WHERE size((n)--())=0 DELETE (n)")
    values = result.values()

    return values


def get_ods_all_tokens_weights(session, lang):
    command = "match (o:ODS_{0})-[r:RELEVANCIA_{0}]-(t:Token_{0}) " \
              "WHERE o.id IN [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] " \
              "RETURN o.id, sum(r.peso) ORDER BY o.id".format(lang)
    result = session.run(command)
    values = result.values()

    return values


# Funciones para insertar las noticias en el grafo
def add_sentence(session, text, sentiment, previous_sentence, lang):
    text = process_quotation_mark(text)

    command = "CREATE (a:Sentence_{0} {{text: {1}, sentiment: '{2}'}}) RETURN ID(a)".format(lang, text, sentiment)
    result = session.run(command)
    value = result.value()

    sentence_id = -1

    if value:
        sentence_id = value[0]

        if previous_sentence >= 0:
            tx = session.begin_transaction()
            command = "MATCH (se1:Sentence_{0}) " \
                      "MATCH (se2:Sentence_{0}) WHERE ID(se1)={1} AND ID(se2)={2} " \
                      "CREATE (se1)-[:PREVIOUS_SENTENCE_{0}]->(se2)".format(lang, sentence_id, previous_sentence)
            tx.run(command)
            tx.commit()

    return sentence_id


def add_token(session, token, concept, lang):
    command = "MATCH (to:Token_{0} {{concept: '{1}'}}) RETURN ID(to)".format(lang, concept)
    result = session.run(command)

    token_id = -1
    value = result.value()

    if value:
        token_id = value[0]
    else:
        tx = session.begin_transaction()
        command = "CREATE (to:Token_{0} {{text: '{1}', concept: '{2}'}}) RETURN ID(to)".format(lang, token, concept)
        result = tx.run(command)

        if result:
            token_id = result.value()[0]

        tx.commit()

    return token_id


def process_quotation_mark(text):
    return "'" + text.replace("'", "\\'") + "'"


def add_news(session, text, sentiment, _url, _id, date, source, title, image_url, lang, entity):
    _url = process_quotation_mark(_url)
    command = "MATCH (ne:News_{0} {{url: {1}}}) RETURN ne.text".format(lang, _url)
    result = session.run(command)
    value = result.value()
    news_id = -1

    if value:
        news_id = value[0]
    else:
        tx = session.begin_transaction()

        text = process_quotation_mark(text)
        sentiment = process_quotation_mark(sentiment)
        image_url = process_quotation_mark(image_url)
        source = process_quotation_mark(source)
        title = process_quotation_mark(title)
        entity = [ent.replace("'", "\\'").lower() for ent in entity]

        command = "CREATE (n:News_{0} {{text: {1}, sentiment: {2}, url: {3}, image_url: {4}, id: '{5}', " \
                  "date: '{6}', source: {7}, title: {8}, entity: {9}, covid: 0, odsID: 0}}) " \
                  "RETURN ID(n)".format(lang, text, sentiment, _url, image_url, _id, date, source, title, entity)
        result = tx.run(command)

        if result:
            news_id = result.value()[0]

        tx.commit()
        # print(command)

    return news_id


def add_news_sentence_relation(session, news_id, sentence_id, date, lang):
    tx = session.begin_transaction()

    # print("url: " + _url)
    date = process_quotation_mark(date)

    command = "MATCH (ne:News_{0}) " \
              "MATCH (se:Sentence_{0}) WHERE ID(ne)={1} AND ID(se)={2} " \
              "CREATE (se)-[:NEWS_SENTENCE_{0} {{date: {3}}}]->(ne)".format(lang, news_id, sentence_id, date)
    tx.run(command)
    tx.commit()


def add_token_sentence_relation(session, token_id, sentence_id, entity_type, date, lang):
    # try:
    tx = session.begin_transaction()

    entity_type = process_quotation_mark(entity_type)

    command = "MATCH (to:Token_{0}) " \
              "MATCH (se:Sentence_{0}) WHERE ID(to) = {1} and ID(se) = {2} " \
              "CREATE (to)-[:TOKEN_BELONGS_TO_{0} {{entity_type: {3}, date: '{4}'}}]->(se)".format(lang, token_id,
                                                                                                   sentence_id,
                                                                                                   entity_type, date)
    tx.run(command)
    tx.commit()


def insert_relation_news_ods(session, news_id, pesos, date, maxODS, maxValor, esODS, lang):
    i = 1
    for peso in pesos:
        tx = session.begin_transaction()

        command = "MATCH (ne:News_{0}) MATCH (od:ODS_{0} {{id: {2}}}) WHERE ID(ne)={1} " \
                  "CREATE (od)-[:NEWS_ODS_{0} {{peso: {3}, date: '{4}'}}]->(ne)".format(lang, news_id, str(i),
                                                                                        str(peso), date)
        tx.run(command)
        i += 1
        tx.commit()

    tx = session.begin_transaction()
    command = "MATCH (ne:News_{0}) WHERE ID(ne)={1} " \
              "SET ne.odsID = {2}, ne.ODSweight = {3}, ne.isitODS = {4}".format(lang, news_id, maxODS, maxValor, esODS)
    tx.run(command)
    tx.commit()


def last_id(session, lang):
    command = "MATCH (n:News_{0}) RETURN max(toInteger(n.id))".format(lang)
    result = session.run(command)
    value = result.value()

    return value


def id_in_graph(session, lang, id):
    command = "MATCH (n:News_{0}) WHERE n.id = '{1}' RETURN n".format(lang, int(id))
    result = session.run(command)

    if result.single() is None:
        return False
    else:
        return True


def get_unprocessed_articles_in_graph(lang):
    ids = mongo.get_all_ids(lang)
    articles_unprocessed = []

    for _id in ids:
        if id_in_graph(lang, _id) is False:
            articles_unprocessed.append(mongo.get_article_by_id(_id))

    return articles_unprocessed


def get_unprocessed_entity_articles_in_graph(lang):
    arts = mongo.get_entity_articles(lang)
    articles_unprocessed = []

    count = 0
    for art in arts:
        if id_in_graph(lang, art["_id"]) is False:
            articles_unprocessed.append(art)
        count += 1

    print("Get {0} articles with entity.".format(count))
    print("Get {0} articles with entity not in the graph".format(len(articles_unprocessed)))

    return articles_unprocessed


def get_unprocessed_no_entity_articles_in_graph(lang):
    arts = mongo.get_no_entity_articles(lang)
    articles_unprocessed = []

    count = 0
    for art in arts:
        if id_in_graph(lang, art["_id"]) is False:
            articles_unprocessed.append(art)
        count += 1

    print("Get {0} articles with no entity.".format(count))
    print("Get {0} articles with entity not in the graph".format(len(articles_unprocessed)))

    return articles_unprocessed


def update_covid(session, _url, lang):
    _url = process_quotation_mark(_url)

    command = "MATCH (n:News_{0})-[r]-(s:Sentence_{0})-[]-(t:Token_{0}) " \
              "WHERE t.text in ['covid', 'coronavirus', 'pandemic', 'pandemia', 'covid-19', 'covid 19'] " \
              "AND n.url = {1} " \
              "RETURN distinct n".format(lang, _url)
    result = session.run(command)

    if result.single() is not None:
        print("La noticia es sobre covid. URL : " + _url)

        tx = session.begin_transaction()
        command = "MATCH (ne:News_{0} {{url: {1}}}) SET ne.covid = 1".format(lang, _url)
        tx.run(command)
        tx.commit()


def delete_news(session, command):
    tx = session.begin_transaction()
    tx.run(command)
    tx.commit()


def delete_isolated_nodes(session, ):
    tx = session.begin_transaction()
    tx.run("MATCH (n) WHERE NOT (n)--() delete n")
    tx.commit()


def update_entity(session, lang):
    command = "MATCH (n:News_{0}) RETURN n".format(lang)
    result = session.run(command)

    for news in result.values():
        _id = news[0]['id']
        doc = mongo.get_article_by_id(int(_id))
        entity = doc['entity']
        command = "MATCH (n:News_{0}) WHERE n.id = '{1}' SET n.entity = {2}".format(lang, _id, entity)
        tx = session.begin_transaction()
        tx.run(command)
        tx.commit()


if __name__ == "__main__":
    # command = "match (n:News_en) where n.date >= '2022-09-01' detach delete n"
    # delete_news(command)
    # delete_isolated_nodes()
    update_entity("en")
