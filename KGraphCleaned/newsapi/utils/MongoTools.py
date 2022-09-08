import csv
import datetime
from utils import Constants
from utils.mongoConnector import MongoConnector
import re


mongo_connector = MongoConnector()
news_Collection = mongo_connector.get_news_collection()

"""
mydb_Old = mongo.myclient["admin"]
articlesCollection = mydb_Old["articles"]
print('Collection names', mydb_Old.list_collection_names())
"""


def print_cursor(cursor):
    counter = 0
    for element in cursor:
        counter += 1
        print(element)
    print('Total', counter)

# cursor = articlesCollection.find({"language":"en"}, {"_id":0}).sort([("date", 1)])
#cursor = news_Collection.find({"language":"en"}, {"url": 1, "_id": 0}).sort([("date", 1)])

no_content = news_Collection.find({"language": "es", "source_type": "newsAPI",
                                   "content": {"$exists": False}}).sort([("date", 1)])

print('no_content size', no_content.count())


#print('with_date size', with_date.count())

##########  REPLACE DATEs         ######################################################################################


# Transform input date to extractors format. "2020-02-12T00:00:00Z" to "26/03/2020 10:29:34"
def date_from_news_api(self, input_date):
    d1 = datetime.datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%SZ")
    return d1.strftime(Constants.DATE_FORMAT)

# Parse a String into a struct_time
def check_date (date, format):
    try:
        return datetime.datetime.strptime(date, format)
    except ValueError as err:
        print(err)
        return None


def replace_dates(cursor):
    total = 0
    origin_ok = 0
    replaced = 0
    wrong = 0

    for news_c in cursor:
        total += 1
        if 'date' in news_c:
            original_date = news_c["date"]
            #print('original date', original_date)
            date = check_date(original_date, Constants.DATE_FORMAT)
            if not date:
                date = check_date(original_date, "%Y-%m-%dT%H:%M:%SZ")
                #date = check_date(original_date, "%b %d, %Y %H:%M:%S %p")
                if date:
                    print('news format.', original_date)
                    news_c["date"] = date.strftime(Constants.DATE_FORMAT)
                    id = news_c['_id']
                    print('_id', id)
                    result = news_Collection.replace_one( {"_id": id } , news_c)
                    replaced += 1
                else:
                    print('Wrong format.', original_date)
                    wrong += 1
            else:
                origin_ok += 1

    print('Total', total, 'Wrong', wrong, 'replaced', replaced, 'origin_ok', origin_ok)


with_date = news_Collection.find({"language": "en",   "source_type": "newsAPI",  "date": {"$exists": True}}).sort([("date", 1)])
#replace_dates(with_date)



##########  INSERT published_at   ######################################################################################
def insert_pubished_at(cursor):
    total = 0
    replaced = 0
    for news_c in cursor:
        id = news_c['_id']
        print("_id:", id)
        total += 1
        if 'published_at' not in news_c:
            original_date = news_c["date"]
            print("_id:", id, ', original date', original_date)
            date = check_date(original_date, Constants.DATE_FORMAT)
            print('date', date)
            if date:
                # Añadir publication_time
                news_c['published_at'] = date
                result = news_Collection.replace_one( {"_id": id } , news_c)
                replaced += 1

    print('Total', total, 'inserted', replaced)


cursor = news_Collection.find({"language": "es",  "published_at": {"$exists": False},  "date": {"$exists": True}}).sort([("_id", 1)])
insert_pubished_at(cursor)

##########  DUPLICATED URLS !!!!   #####################################################################################

def print_duplicated_urls():
    print('DUPLICATED URLs')
    pipe = [ {"$group" : {"_id": "$url", "count": {"$sum": 1 }}} ,   {"$match": {"_id" :{ "$ne" : None}, "count" : {"$gt": 1}}} ,
             {"$project": {"url": "$_id", "count":1, "_id": 0}}]
    duplicated_urls = news_Collection.aggregate(pipeline=pipe)
    print_cursor(duplicated_urls)

def delete_duplicated_urls():
    print('Deleting duplicated URLs')
    pipe = [ {"$group" : {"_id": "$url", "count": {"$sum": 1 }}} ,   {"$match": {"_id" :{ "$ne" : None}, "count" : {"$gt": 1}}} ,
         {"$project": {"url": "$_id", "count":1, "_id": 0}}]
    url_list = news_Collection.aggregate(pipeline=pipe)
    counter = 0
    for element in url_list:
        url = element['url']
        print(url)
        counter += 1
        delete_result = news_Collection.delete_one({"url": url})
        # print("Result", delete_result)
    return counter

print_duplicated_urls()
#print("Borrando urls. Total: ", delete_duplicated_urls())

########################################################################################################################

def addEmptyContent(cursor):
    counter = 0
    for news_c in cursor:
        #print('news_c', news_c)
        if 'content' in news_c:
            lastContent = news_c["content"]
            print('lastContent', lastContent)
        else:
            news_c["content"] = 'N/A'
            print('news_c', news_c)
            id = news_c['_id']
            print('_id', id)
            result = news_Collection.replace_one( {"_id": id } , news_c)
            print('result', result)
            counter += 1
            if counter == 2000:
                break
    #res = mongo.news_Collection.insert_one(news_c)
    print('news_c counter', counter)



#addEmptyContent(no_content)


def insertArticles (input_articles):
    inserted = 0
    for input in input_articles:
        mongo_connector.insertArticle(input)
        print('input article inserted')
        inserted = inserted + 1
    print(inserted, ' articles inserted.')



def write_csv(complete_path, csv_rows, language='es'):
    # Write the CSV file
    complete_path = complete_path + '_' + language + '.csv'
    # Excel no es capaz de determinar el encoding utf-8 automaticamente, usamos utf-16le
    with open(complete_path, 'w', encoding='UTF-16le') as f:
        writer = csv.writer(f, delimiter=';', dialect='excel', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for r in csv_rows:
            writer.writerow(r)
    print('CSV writed ')
# End function



def print_csv(cursor):
    csvRows = []
    for news_c in cursor:
        #news_c["_id"] = mongo.get_next_id()
        #news_c["source_type"] = "newsAPI"
        #res = mongo.news_Collection.insert_one(news_c)
        csvRows.append([news_c.get('url')])
        print('news_c inserted', news_c)
    PATH = 'C:/Temp/KGRAPH/'
    excelFileName = 'URLS'
    write_csv(PATH + excelFileName, csvRows, 'en')

#print_csv(cursor)






#insertArticles(newsletter_articles)


"""
newsletter_articles = []
with open('C:/Users/xe30000/IdeaProjects/datio-knowledge-graph/utils/newsletters.json',  encoding='utf-8') as file:
    newsletter_articles = json.load(file)

print('res:', newsletter_articles)
"""


"""
mongo_connector.insert_article(
    {
        "url": "https:QUIT_05",
        "title" : "Noticia con id contador de prueba",
        "date" : "2020-03-11T12:08:44Z",
        "source" : "Elespanol.com",
        "description" : "Hace unas semanas conocíamos que la Unión Europea estaba planeando un plan para aumentar la vida útil de los dispositivos móviles planeando que las baterías -....",
        "author" : "Ivan",
        "status" : "error",
        "language": "bad"
    }
)
"""

"""
url = "https://www.abc.es/espana/comunidad-valenciana/abci-coronavirus-mercadona-entrega-9200-kilos-alimentos-entidades-sociales-valencia-202004061038_noticia.html"
delete_result = news_Collection.delete_one({"url": url})
print("Result", delete_result)
"""

#query = {"language": "en", "status": "tags_extracted"}

# #print('total:', mongo_connector.news_Collection.count_documents(query))



#mongo_connector.news_Collection.delete_many(query)