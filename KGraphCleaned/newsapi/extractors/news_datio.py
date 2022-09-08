
import json
from logger import logger
from utils.mongoConnector import MongoConnector
from interfaces.extractor import Extractor


PATH_FILE = 'C:/Desarrollo/Innovacion/Knowledge Graph/Datio/MonitoringNews/monitoringnews_20200327_001.dat'
SOURCE_TYPE = "DATIO"


class NewsDatio(Extractor):


    def __init__(self):
        super().__init__()
        self.FILE_PATH = None
        self.DEFAULT_LANGUAGE = 'UNDEF'
        self.mongo_connector = MongoConnector()


    def set_file_path(self, file_path):
        self.FILE_PATH = file_path


    def get_name(self):
        return SOURCE_TYPE

    def can_continue(self):
        return self.FILE_PATH is not None

    # Extract data
    def get_dataset(self):
        logger.debug(f'extract Datio news from file: {self.FILE_PATH}')
        print('extract Datio news from file:', self.FILE_PATH)

        json_file = None
        with open(self.FILE_PATH, encoding='utf-8-sig') as file:
            json_file = json.load(file)

        logger.debug(f'Date: {json_file["date"]}')
        print('alerts: ', json_file['alerts'])
        news = list()

        count = 0
        for alert in json_file['alerts']:
            for article in alert['articles']:
                count += 1
                url = None
                if article.get('url'):
                    url = article['url']
                else:
                    url = article.get('urlPdf')

                source = article.get('source')


                if (url is not None) and (source != 'BORME'):
                    article_json = {
                        "url": url,
                        "title": article.get('title'),
                        "date": article.get('publicationDate'),
                        "source": source,
                        "description": article.get('text'),
                        "author": article.get('author'),
                        "status": "raw",
                        "source_type": SOURCE_TYPE
                    }
                    # Language
                    if article.get('languageCode'):
                        article_json['language'] = article['languageCode']
                    else:
                        if article.get('language'):
                            article_json['language'] = article['language']
                            print('No language code. Transform?')
                        else:
                            article_json['language'] = self.DEFAULT_LANGUAGE

                    news.append(article_json)
                else:
                    print('Article without URL or has invalid source: ', source)


        logger.debug(f'Fetched {len(news)} articles of {count}')
        return news

    # Quit som URLs ???
    def reduce_dataset(self, dataset):
        news_list = list(filter(self._find_in_whitelist, dataset))
        logger.debug(f'Dataset filtered. {len(news_list)} remaining')
        return news_list


    # WRITE in MONGO
    def write_in_mongo(self, list):
        count = 0
        for art in list:
            inserted = self.mongo_connector.insert_article(art)
            if inserted:
                count += 1
        print(count, 'articles inserted in Mongo')


"""
extractor = NewsDatio()
extractor.set_file_path(PATH_FILE)
dataset = extractor.get_dataset()
print("Dataset size",len(dataset))
extractor.write_in_mongo(dataset)
"""