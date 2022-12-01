# Función Multiproceso
import datetime
import spacy
from boilerpy3 import extractors
from tqdm import tqdm
from newspaper import Article

from neo4j_functions import *
from mongo import *
from httpSessionWithTimeout import HttpSessionWithTimeout, HEADERS
from utilities import *

# from .httpSessionWithTimeout import HttpSessionWithTimeout, HEADERS  # For backend local test
# from .neo4j_functions import *  # For backend local test
# from .mongo import *  # For backend local test
# from .utils import *

extractor = extractors.ArticleExtractor()


def calculate(data):
    _url = data["url"]
    lang = data["lang"]
    _id = int(data["_id"])
    date = data["date"]
    source = data["source"]
    title = data["title"].replace("\\", " ")
    art_ods_id = "fila" + str(_id)

    entity = []
    if "entity" in data.keys():
        entity = data["entity"]

    session_neo4j = driver.session()

    if id_in_graph(session_neo4j, lang, _id):
        print("This article has already existed in the database.")
        delete_unprocessed_id(_id, lang)
        session_neo4j.close()
        return "Error: This article has already existed in the database."

    ods = [0] * 18
    crea_ods(session_neo4j, art_ods_id, lang)

    print("1. Extract text from: " + _url)
    try:
        if "content" in data.keys():
            text_extracted = data["content"].replace("\'", "").replace("\\", "")
            _url = _url.replace("\\", "\\\\")
            article_url = ""
        else:
            session = HttpSessionWithTimeout()
            session.headers.update(HEADERS)
            resp = session.get(_url)
            text_extracted = extractor.get_content(resp.text).replace("\'", "").replace("\\", "")

            article = Article(_url)
            article.download()
            article.parse()
            article_url = article.top_image
    except Exception as error:
        print("Error. Cannot get text from this url." + _url)
        delete_article_ods(session_neo4j, art_ods_id, lang)
        delete_unprocessed_id(_id, lang)
        session_neo4j.close()
        return "Error: Fail to read the article.\n" + str(error)
    else:
        if len(text_extracted) < 250:
            delete_article_ods(session_neo4j, art_ods_id, lang)
            delete_unprocessed_id(_id, lang)
            session_neo4j.close()
            return "Error: The article is too short (<250) to determine its SDG."

        print("2. Insert into the graph: " + _url)

        # Select model according to the language
        if lang == "es":
            nlp = spacy.load("es_core_news_sm")
        else:
            nlp = spacy.load("en_core_web_md")

        try:
            frases = nlp(text_extracted)
        except Exception as e:
            print(e)
            delete_article_ods(session_neo4j, art_ods_id, lang)
            delete_unprocessed_id(_id, lang)
            session_neo4j.close()
            return "Error: Fail to analyze the article."

        words = [token.text for token in frases if
                 token.is_stop is not True and token.is_alpha and len(token.lemma_) > 1]
        palabras = len(words)
        sustainability = [0] * 18
        previous_sentence = -1

        if palabras < 2000:
            sent_score = get_sentiment_score(text_extracted, lang)
            news_id = add_news(session_neo4j, text_extracted[:100], str(sent_score), _url, _id, date, source, title,
                               article_url, lang, entity)

            with tqdm(total=int(palabras)) as pbar:
                for texto in frases.sents:
                    sentence = texto.text.replace("\n", "")

                    # no necessary to determine the sentiment score of the sentence
                    # sent_score = get_sentiment_score(sentence, lang)

                    sent_score = 0
                    sentence_id = add_sentence(session_neo4j, sentence, str(sent_score), previous_sentence, lang)
                    add_news_sentence_relation(session_neo4j, news_id, sentence_id, date, lang)
                    previous_sentence = sentence_id

                    dictionary = get_dict_from_file(lang)   # get es-en dictionary

                    for t in texto:
                        if t.is_alpha and not t.is_stop and len(t.lemma_) > 1:
                            concept = get_concept(t.lemma_.lower().replace("\'", "").replace("\"", ""),
                                                  lang, dictionary)
                            token_id = add_token(session_neo4j, t.lemma_.lower().replace("\'", "").replace("\"", ""),
                                                 concept, lang)
                            add_token_sentence_relation(session_neo4j, token_id, sentence_id, t.tag_, date, lang)
                            values = peso_de_token(session_neo4j, token_id, lang)  # modify

                            if len(values) > 0:
                                for x in values:
                                    ods[x[1]] += x[2]
                                    sustainability[x[1]] += 1

                            pbar.update(1)

            ods[0] = 0
            all_token_weights = get_ods_all_tokens_weights(session_neo4j, lang)

            ods.pop(0)
            ods2 = [0] * 17
            max_value = 0
            max_value_ods = 0

            for item in range(17):
                ods_value = ods[item] / all_token_weights[item][1]
                ods2[item] = ods_value * (1 + sustainability[item + 1] / palabras)
                if ods2[item] > max_value:
                    max_value = ods2[item]
                    max_value_ods = item + 1

            is_ods = 0

            if max_value > 0.55:
                is_ods = 1

            insert_relation_news_ods(session_neo4j, news_id, ods2, date, max_value_ods, max_value, is_ods, lang)
            update_covid(session_neo4j, _url, lang)
        else:
            delete_article_ods(session_neo4j, art_ods_id, lang)
            delete_unprocessed_id(_id, lang)
            session_neo4j.close()
            return "Error: The article is too long (more than 2000 words)."

        delete_article_ods(session_neo4j, art_ods_id, lang)
        delete_unprocessed_id(_id, lang)
        session_neo4j.close()

        message = "The article has been created correctly in the database!"

        if is_ods == 0:
            message += " But the article is not a SDG news."

        return message


if __name__ == "__main__":
    print("Start execution...")
    n_id = 581
    art = get_article_by_id(n_id)

    if art["title"] is None:
        art_title = ""
    else:
        art_title = art["title"]

    published_date = art["published_at"]

    art_data = {
        "url": art["url"],
        "fila": art["_id"],
        "_id": int(art["_id"]),
        "date": published_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": art["source"],
        "title": art_title.replace('"', '').replace("'", ''),
        "lang": art["language"],
        "entity": art["entity"]
    }

    result = calculate(art_data)
    print(result)
