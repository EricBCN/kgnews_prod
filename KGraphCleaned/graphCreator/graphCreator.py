# Función Multiproceso
import datetime
from spacy.lang.es.stop_words import STOP_WORDS
import spacy
from boilerpy3 import extractors
from tqdm import tqdm
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import wordnet
from newspaper import Article

from neo4j_functions import *  # id_in_graph, crea_ods, add_News, add_sentence, add_token
from mongo import *
from httpSessionWithTimeout import HttpSessionWithTimeout, HEADERS

# from .httpSessionWithTimeout import HttpSessionWithTimeout, HEADERS  # For backend local test
# from .neo4j_functions import *  # For backend local test
# from .mongo import *  # For backend local test

sid = SentimentIntensityAnalyzer()
extractor = extractors.ArticleExtractor()
stopwords = list(STOP_WORDS)
valid_tags = ["ADJ", "ADP", "AUX", "CONJ", "NOUN", "NUM", "PROPN", "VERB"]


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

    if id_in_graph(lang, _id):
        print("This article has already existed in the database.")
        delete_unprocessed_id(_id, lang)
        return "Error: This article has already existed in the database."

    ods = [0] * 18
    crea_ods(art_ods_id, lang)

    print("1. Extract text from: " + _url)
    try:
        start_time = datetime.datetime.now()  # 纪录运行时间
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

        end_time = datetime.datetime.now()  # 纪录运行时间
        print("1. 获取文章内容: " + str((end_time - start_time).microseconds))  # 显示运行时间

    except Exception as error:
        print("Error. Cannot get text from this url." + _url)
        delete_article_ods(art_ods_id, lang)
        delete_unprocessed_id(_id, lang)
        return "Error: Fail to read the article.\n" + str(error)
    else:
        # Calculate the sentiment and insert the news
        # print("Length : " + str(len(text_extracted)))
        # print(text_extracted)

        if len(text_extracted) < 250:
            delete_article_ods(art_ods_id, lang)
            delete_unprocessed_id(_id, lang)
            return "Error: The article is too short (<250) to determine its SDG."

        start_time = datetime.datetime.now()  # 纪录运行时间
        ss = sid.polarity_scores(text_extracted)
        end_time = datetime.datetime.now()  # 纪录运行时间
        print("2. 情绪分析: " + str((end_time - start_time).microseconds))  # 显示运行时间

        print("2. Insert into the graph: " + _url)
        start_time = datetime.datetime.now()  # 纪录运行时间

        # Select model according to the language
        if lang == "es":
            nlp = spacy.load("es_core_news_sm")
        else:
            nlp = spacy.load("en_core_web_md")

        end_time = datetime.datetime.now()  # 纪录运行时间
        print("3. 加载spaCy模型: " + str((end_time - start_time).microseconds))  # 显示运行时间

        try:
            start_time = datetime.datetime.now()  # 纪录运行时间
            frases = nlp(text_extracted)
            end_time = datetime.datetime.now()  # 纪录运行时间
            print("4. 对文章做自然语言处理并获取句子: " + str((end_time - start_time).microseconds))  # 显示运行时间
        except Exception as e:
            print(e)
            delete_article_ods(art_ods_id, lang)
            delete_unprocessed_id(_id, lang)
            return "Error: Fail to analyze the article."

        words = [token.text for token in frases if
                 token.is_stop is not True and token.is_alpha and len(token.lemma_) > 1]
        palabras = len(words)
        sustainability = [0] * 18
        previous_sentence = -1

        polarity_sentence_time = 0  # 纪录运行时间
        get_concept_time = 0  # 纪录运行时间
        add_sentence_time = 0  # 纪录运行时间
        add_news_sentence_relation_time = 0  # 纪录运行时间
        add_token_time = 0  # 纪录运行时间
        add_token_sentence_relation_time = 0  # 纪录运行时间
        get_token_weight = 0  # 纪录运行时间
        add_token_ods_relation_time = 0  # 纪录运行时间

        # print("Start: " + _url)
        if palabras < 2000:
            news_id = add_news(text_extracted[:100], str(ss["compound"]), _url, _id, date, source, title,
                               article_url, lang, entity)

            with tqdm(total=int(palabras)) as pbar:
                for texto in frases.sents:
                    sentence = texto.text.replace("\n", "")

                    start_time = datetime.datetime.now()  # 纪录运行时间
                    ss = sid.polarity_scores(sentence)
                    end_time = datetime.datetime.now()  # 纪录运行时间
                    polarity_sentence_time += (end_time - start_time).microseconds  # 纪录运行时间

                    start_time = datetime.datetime.now()  # 纪录运行时间
                    sentence_id = add_sentence(sentence, str(ss["compound"]), previous_sentence, lang)
                    end_time = datetime.datetime.now()  # 纪录运行时间
                    add_sentence_time += (end_time - start_time).microseconds  # 纪录运行时间

                    # print("Insert relation (url): " + _url)
                    start_time = datetime.datetime.now()  # 纪录运行时间
                    add_news_sentence_relation(news_id, sentence_id, date, lang)
                    end_time = datetime.datetime.now()  # 纪录运行时间
                    add_news_sentence_relation_time += (end_time - start_time).microseconds  # 纪录运行时间

                    previous_sentence = sentence_id

                    for t in texto:
                        if t.is_alpha and not t.is_stop and len(t.lemma_) > 1:
                            # for x in valid_tags:
                            #    if x in t.tag_:
                            start_time = datetime.datetime.now()  # 纪录运行时间
                            try:
                                syns = wordnet.synset(t.lemma_.lower().replace("\'", "").replace("\"", "") + ".n.01")
                                concept = syns.lemma_names()[0].lower().replace("\'", "").replace("\"", "")
                            except Exception:
                                concept = t.lemma_.lower().replace("\'", "").replace("\"", "")
                            end_time = datetime.datetime.now()  # 纪录运行时间
                            get_concept_time += (end_time - start_time).microseconds  # 纪录运行时间

                            start_time = datetime.datetime.now()  # 纪录运行时间
                            token_id = add_token(t.lemma_.lower().replace("\'", "").replace("\"", ""), concept, lang)
                            end_time = datetime.datetime.now()  # 纪录运行时间
                            add_token_time += (end_time - start_time).microseconds  # 纪录运行时间

                            start_time = datetime.datetime.now()  # 纪录运行时间
                            add_token_sentence_relation(token_id, sentence_id,
                                                        t.tag_, date, lang)
                            end_time = datetime.datetime.now()  # 纪录运行时间
                            add_token_sentence_relation_time += (end_time - start_time).microseconds  # 纪录运行时间

                            start_time = datetime.datetime.now()  # 纪录运行时间
                            values = peso_de_token(token_id, lang)  # modify
                            end_time = datetime.datetime.now()  # 纪录运行时间
                            get_token_weight += (end_time - start_time).microseconds  # 纪录运行时间

                            if len(values) > 0:
                                for x in values:
                                    ods[x[1]] += x[2]
                                    sustainability[x[1]] += 1

                            start_time = datetime.datetime.now()  # 纪录运行时间
                            insert_relation_token_ods(token_id, art_ods_id, palabras, date, lang)
                            end_time = datetime.datetime.now()  # 纪录运行时间
                            add_token_ods_relation_time += (end_time - start_time).microseconds  # 纪录运行时间

                            pbar.update(1)

            print("5. 对句子做情感分析总时间: " + str(polarity_sentence_time))  # 显示运行时间
            print("6. 获取concept总时间: " + str(get_concept_time))  # 显示运行时间
            print("7. 添加句子总时间: " + str(add_sentence_time))  # 显示运行时间
            print("8. 添加文章与句子关系总时间: " + str(add_news_sentence_relation_time))  # 显示运行时间
            print("9. 添加token总时间: " + str(add_token_time))  # 显示运行时间
            print("10. 添加token与句子关系总时间: " + str(add_token_sentence_relation_time))  # 显示运行时间
            print("11. 获取token权重总时间: " + str(get_token_weight))  # 显示运行时间
            print("12. 添加token与ods关系总时间: " + str(add_token_ods_relation_time))  # 显示运行时间

            start_time = datetime.datetime.now()
            ods[0] = 0
            all_token_weights = get_ods_all_tokens_weights(lang)

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

            # print(str(ods2))
            # print(str(max_value))
            # print(str(max_value_ods))

            if max_value > 0.55:
                is_ods = 1

            insert_relation_news_ods(news_id, ods2, date, max_value_ods, max_value, is_ods, lang)
            actualiza_covid(_url, lang)

            end_time = datetime.datetime.now()  # 纪录运行时间
            print("13. 确定文章ODS: " + str((end_time - start_time).microseconds))  # 显示运行时间
        else:
            delete_article_ods(art_ods_id, lang)
            delete_unprocessed_id(_id, lang)
            return "Error: The article is too long (more than 2000 words)."

        delete_article_ods(art_ods_id, lang)
        delete_unprocessed_id(_id, lang)

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
