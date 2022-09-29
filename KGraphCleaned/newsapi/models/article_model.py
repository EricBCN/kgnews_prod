import datetime
from mongokit_ng.document import Document

__all__ = [
    'Article'
]


class Article(Document):
    __database__ = 'KGNews'
    __collection__ = 'news'

    structure = {
        'date': str,
        'timestamp': datetime.datetime,
        'published_at': datetime.datetime,
        'language': str,
        'status': str,
        'author': str,
        'title': str,
        'description': str,
        'url': str,
        'source': str,
        'source_type': str,
        'content': str,
        "entity": [],
        'tags': dict,
    }

    required_fields = [
        'date',
        'language',
        'status',
        'title',
        'url',
        'source',
        'source_type'
    ]

    default_values = {
        'date': datetime.datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S'),
        'status': 'raw'
    }
