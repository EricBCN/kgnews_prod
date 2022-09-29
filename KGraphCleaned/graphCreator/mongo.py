from pymongo import MongoClient
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


def get_unprocessed_articles(lang):
    articles_collection = client.KGNews.news
    ids = get_unprocessed_id(lang)
    articles = []

    for info in ids:
        arts = articles_collection.find({"_id": info["_id"]})
        for art in arts:
            articles.append(art)

    return articles


def get_article_by_id(_id):
    articles_collection = client.KGNews.news

    arts = articles_collection.find({"_id": _id})
    for art in arts:
        return art

    return None


def delete_unprocessed_id(_id, lang):
    ids_collection = client.KGNews.ids
    ids_collection.delete_many({
        "_id": _id,
        "language": lang
    })


if __name__ == "__main__":
    data = get_unprocessed_articles("en")
    print(data)



