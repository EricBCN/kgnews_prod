from pymongo import MongoClient
ip = '192.168.75.132'
port = 27017
username = 'root'
password = '$$52$verb$REALIZE$market$25$$'
client = MongoClient(ip, username=username, password=password, port=port)


def get_articles(min_id, lang):
    db = client.KGNews
    articles = db.news
    return articles.find({ "$and": [ {"_id": {"$gt": min_id}}, {"language": lang} ] }).sort([("_id", 1)]).limit( 3000 )

