from pymongo import MongoClient
# ip = '192.168.75.134'
ip = '127.0.0.1'
port = 27017
# username = 'root'
# password = '$$52$verb$REALIZE$market$25$$'
username = ''
password = ''
client = MongoClient(ip, username=username, password=password, port=port)


def get_articles(min_id, lang):
    db = client.KGNews
    articles = db.news
    return articles.find({"$and": [{"_id": {"$gt": min_id}}, {"language": lang}]}).sort([("_id", 1)]).limit(3000)


def get_unprocessed_id(lang):
    return client.KGNews.ids.find({"language": lang})


def get_unprocessed_articles_by_ids(lang):
    articles_collection = client.KGNews.news
    ids = get_unprocessed_id(lang)
    articles = []

    for info in ids:
        arts = articles_collection.find({"_id": info["_id"]})
        for art in arts:
            articles.append(art)

    return articles


def get_entity_articles(lang):
    articles_collection = client.KGNews.news
    arts = articles_collection.find({"language": lang, "entity": {"$ne": []}})
    articles = [art for art in arts]

    return articles


def get_no_entity_articles(lang):
    articles_collection = client.KGNews.news
    arts = articles_collection.find({"language": lang, "entity": {"$eq": []}})
    articles = [art for art in arts]

    return articles


def get_article_by_id(_id):
    articles_collection = client.KGNews.news

    arts = articles_collection.find({"_id": _id})
    for art in arts:
        return art

    return None


def get_all_ids(lang):
    arts = client.KGNews.news.find({"language": lang})
    ids = []
    for art in arts:
        ids.append(art["_id"])

    return ids


def delete_unprocessed_id(_id, lang):
    ids_collection = client.KGNews.ids
    ids_collection.delete_many({
        "_id": _id,
        "language": lang
    })


if __name__ == "__main__":
    arts = get_unprocessed_articles_by_ids("en")
    print(arts)



