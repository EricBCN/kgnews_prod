import pymongo
import datetime

__all__ = [
    'MongoConnector'
]


"""
# LABORATORIO
PASSWORD = 'pass'
DATABASE = 'KGRAPH'
IP = '20.1.67.236'
PORT = 10000
DATABASE = 'KGRAPH'
"""


"""
# AWS
IP = '34.255.66.249'
IP ='ec2-34-255-66-249.eu-west-1.compute.amazonaws.com'
PORT = 27017
PASSWORD = '$$52$verb$REALIZE$market$25$$'
DATABASE = 'KGNews'
"""


class MongoConnector:
    def __init__(self):
        self.AUTH_MECHANISM = 'SCRAM-SHA-1'
        self.USERNAME = 'root'

        # AWS
        # self.IP = '172.31.12.215'
        # self.PORT = 27017
        # self.PASSWORD = '$$52$verb$REALIZE$market$25$$'
        # self.DATABASE = 'KGNews'

        # local
        self.USERNAME = ''
        self.IP = '127.0.0.1'
        self.PORT = 27017
        self.PASSWORD = ''
        self.DATABASE = 'KGNews'


        # CLIENT
        # print('Connecting to ', self.IP, ':', self.PORT, ' with user ', self.USERNAME)
        # self.myclient = pymongo.MongoClient('mongodb://' + self.IP + ':' + str(self.PORT) + '/', username=self.USERNAME, password=self.PASSWORD, authMechanism=self.AUTH_MECHANISM)
        # connString = 'mongodb://{0}:{1}@{2}:{3}/?authMechanism=SCRAM-SHA-1'.format(self.USERNAME, self.PASSWORD, self.IP, self.PORT)
        connString = 'mongodb://127.0.0.1'
        # print(connString)

        self.myclient = pymongo.MongoClient(connString)
        self.mydb = self.myclient[self.DATABASE]

        #print(self.myclient.list_database_names())

        """
        dblist = self.myclient.list_database_names()
        if self.DATABASE in dblist:
            print("The database exists.")
        """

        # COLLECTIONS
        self.news_Collection = self.mydb["news"]
        self.counter_collection = self.mydb["counters"]
        self.ids_collection = self.mydb["ids"]

        if not self.counter_collection.find_one({"_id": "news_id"}):
            self.counter_collection.insert_one({"_id": "news_id", "sequence_value": 0})


    def get_news_collection(self):
        return self.news_Collection

    def insert_article(self, article):
        url = article.get('url')
        inserted = False
        #print('insert', url)
        if url:
            art = self.news_Collection.find_one({"url": url})
            if not art:
                #else:
                article["_id"] = self.get_next_id()
                article["timestamp"] = datetime.datetime.utcnow()
                res = self.news_Collection.insert_one(article)
                #print('article inserted with result: ', res.inserted_id)
                inserted = True
            else:
                print('Url already exists. No replace')
        else:
            print('Article without url!')
        return inserted

    def insert_id(self, info):
        res = self.ids_collection.insert_one(
            {
                "_id": info["_id"],
                "language": info["language"]
            }
        )

        return res

    def get_next_id(self):
        doc = self.counter_collection.find_one_and_update(
            {"_id": "news_id"},
            {'$inc': {'sequence_value': 1}, '$set': {'done': True}}
        )
        return doc["sequence_value"]

    def delete_one(self, query):
        self.news_Collection.delete_one(query)

    def delete_many(self, query):
        result = self.news_Collection.delete_many(query)
        print(result.deleted_count, " documents deleted.")

    def delete_all(self, collection):
        result = collection.delete_many({})
        print(result.deleted_count, " documents deleted.")


mongo_connector = MongoConnector()
