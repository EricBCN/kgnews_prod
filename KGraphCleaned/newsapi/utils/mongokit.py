from mongokit_ng.connection import Connection

from models.article_model import Article
from logger import logger

__all__ = [
    'connection',
    'news_collection'
]

# AWS
# CONSTANTS = {
#     'HOST': 'ec2-34-255-66-249.eu-west-1.compute.amazonaws.com',
#     'PORT': 27017,
#     'USERNAME': 'root',
#     'PASSWORD': '$$52$verb$REALIZE$market$25$$',
#     'AUTH_MECHANISM': 'SCRAM-SHA-1',
#     'DATABASE': 'KGNews',
#     'COLLECTION': 'news'
# }

# Local
CONSTANTS = {
    'HOST': '192.168.75.132',
    'PORT': 27017,
    'USERNAME': 'root',
    'PASSWORD': '$$52$verb$REALIZE$market$25$$',
    'AUTH_MECHANISM': 'SCRAM-SHA-1',
    'DATABASE': 'KGNews',
    'COLLECTION': 'news'
}

logger.debug('Initializing MongoKit connection')
connection = Connection(
    host=CONSTANTS['HOST'],
    port=CONSTANTS['PORT'],
    username=CONSTANTS['USERNAME'],
    password=CONSTANTS['PASSWORD'],
    authMechanism=CONSTANTS['AUTH_MECHANISM']
)

logger.debug('Registering models')
connection.register([Article])
news_collection = connection.KGNews.news


def get_next_id():
    doc = connection.KGNews.counters.find_one_and_update(
        {"_id": "news_id"},
        {'$inc': {'sequence_value': 1}, '$set': {'done': True}}
    )
    return doc["sequence_value"]
