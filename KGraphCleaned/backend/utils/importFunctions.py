import datetime
import os
from boilerpy3 import extractors
from PyPDF2 import PdfFileReader
import langdetect

# For Ubuntu Server
import sys
path = os.path.abspath(os.path.dirname(__file__))
projectPath = os.path.split(path)[0]
projectPath = os.path.split(projectPath)[0]
sys.path.append(projectPath)
sys.path.append(os.path.join(projectPath, "newsapi"))
sys.path.append(os.path.join(projectPath, "graphCreator"))

import newsapi.utils.mongokit as mongokit
from newsapi.utils.httpSessionWithTimeout import *
from newsapi.utils.tools import *
from graphCreator import calculate
from mongo import get_article_by_id


# For Windows Local Test
# from graphCreator.graphCreator import calculate
# from graphCreator.mongo import get_article_by_id
# import newsapi.utils.mongokit as mongokit
# from newsapi.utils.httpSessionWithTimeout import *
# from newsapi.utils.tools import *


def _create_article(url, title, language, content, source_type):
    dt_utc = datetime.datetime.utcnow()
    published_at = dt_utc.strftime('%d/%m/%Y %H:%M:%S')

    article = mongokit.news_collection.Article()
    article['url'] = url
    article['title'] = title if title != "" else url
    article['date'] = published_at
    article['source'] = ""
    article['description'] = ""
    article['author'] = ""
    article['status'] = "raw"
    article['language'] = language
    article['source_type'] = source_type
    article['tags'] = dict()
    article['content'] = content
    article['published_at'] = dt_utc

    article['entity'] = []
    entities = get_entities(language)

    for ent in entities:
        if ent.lower() in content.lower() or ent.lower() in title.lower():
            article['entity'].append(ent.lower())

    return article


def get_lang(text):
    try:
        result = langdetect.detect_langs(text)
        result = str(result[0])[:2]
    except:
        result = 'unknown'

    return result


def get_content_from_url(url):
    session = HttpSessionWithTimeout()
    session.headers.update(HEADERS)
    extractor = extractors.ArticleExtractor()

    content = ""
    title = ""
    content_flag = True
    title_flag = True

    try:
        doc = extractor.get_doc_from_url(url)
        content = doc.content
        title = doc.title
    except Exception:
        title_flag = False

    if not title_flag:
        try:
            resp = session.get(url)
            content = extractor.get_content(resp.text)
        except Exception as error:
            content = "Error: Fail to get article's content.\n" + str(error)
            content_flag = False

    return content, title, content_flag


def get_content_from_pdf(filepath):
    with open(filepath, "rb") as f:
        pdf = PdfFileReader(f, "rb")

        title = os.path.split(filepath)[1] if pdf.getDocumentInfo().title is None else pdf.getDocumentInfo().title
        content = ""
        content_flag = True

        for i in range(pdf.getNumPages()):
            page_text = pdf.getPage(i).extractText()
            content += page_text + "\n"

        if content == "":
            content = "Error: Fail to read the file."
            content_flag = False

    return content, title, content_flag


def store(doc):
    # Generate a list with the urls from the dataset
    url = doc['url']
    # Query the mongoDB to retrieve articles with those urls
    result = mongokit.news_collection.find({'url': url}, {'url': 1})
    stored_urls = list(map(lambda art: art['url'], result))

    if (url not in stored_urls) or (url == ""):
        try:
            doc["_id"] = mongokit.get_next_id()
            doc["timestamp"] = datetime.datetime.utcnow()
            doc.validate()
            doc.save()
        except Exception as error:
            return {"result": "Error: Fail to store the article.\n" + str(error)}
    else:
        if doc["source_type"] == "pdf":
            return {"result": "Error: This file has already existed in the database."}
        else:
            return {"result": "Error: This url has already existed in the database."}

    return {"result": "The article has been stored correctly!", "_id": doc["_id"]}


def import_document(flag, url, title, content, source_type):
    if flag:
        language = get_lang(content)

        if language not in ['en', 'es']:
            result = {"result": "Error: Cannot determine article's language."}
            return result

        doc = _create_article(url=url, title=title, language=language, content=content, source_type=source_type)
        result = store(doc)

        if "error" in result["result"].lower():
            return result

        article = get_article_by_id(result["_id"])

        if article is None:
            result = {"result": "Error: Cannot find the article in the database."}
            return result

        post = {
            "url": article["url"],
            "_id": article["_id"],
            "date": article["published_at"].strftime("%Y-%m-%dT%H:%M:%S"),
            "source": article["source"],
            "title": "" if article["title"] is None else article["title"].replace('"', '').replace("'", ''),
            "lang": article["language"],
            "entity": article["entity"],
            "content": content
        }

        message = calculate(post)
        result = {"result": message}
    else:
        result = {"result": content}

    return result


def delete_file(filepath):
    if os.path.isfile(filepath):
        os.remove(filepath)
        print("File deleted successfully")


if __name__ == '__main__':
    # print(mongokit.news_collection)  # path test

    text_en = 'Beijing - a city of more than 21 million - reported 316 new Covid cases to 15:00 on Monday, according to Reuters news agency. Amongst the three deaths reported since Sunday afternoon was an 87-year-old man.\n' \
              'Liu Xiaofeng - the deputy director of Beijing\'s municipal Centre for Disease Control and Prevention - described the situation as the most complex and severe yet seen in the city, the news agency added.'
    text_es = 'Mover el torneo al invierno local fue parte de la respuesta. Pero la rica naci??n des??rtica promete dejar adem??s un legado radical: avances en tecnolog??a que permitir??n la celebraci??n de grandes eventos deportivos durante todo el a??o, incluso en los pa??ses m??s c??lidos. Hajar Saleh, futbolista de Qatar, dice que el calor y la humedad hacen que jugar en la regi??n sea un gran desaf??o.'
    get_lang(text_en)
    get_lang(text_es)

    # url = "https://japantoday.com/category/world/sri-lanka-has-an-imf-deal-now-it-courts-china-and-india1"
    # content, title, flag = get_content_from_url(url)
    # result = import_document(flag, url, title, "en", content, "url")
    # print(result)

    # filepath = "C:\\Users\\xin.huang\\Documentos\\Proyectos\\BBVA Herramienta clasificacion noticias " \
    #            "sostenibilidad\\Sustainable Fashion Week challenging industry's footprint - BBC News.pdf"
    # content, title, flag = get_content_from_pdf(filepath)
    # result = import_document(flag, "", title, "en", content, "pdf")
    # print(result)
