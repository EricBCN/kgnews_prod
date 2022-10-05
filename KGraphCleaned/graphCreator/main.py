from graphCreator import calcula
from mongo import *
from neo4j_functions import *
import schedule
from multiprocessing import Pool
import sys
import time


DAILY_TIME = "03:00"
lang = "en"


def launch():
    print(f'Executing graph creator')
    datos = []

    # print("Ultimo ID: " + str(last_id(lang)[0]))
    # modify: if last_id(lang)[0] is None:

    # if len(last_id(lang)) == 0 or last_id(lang)[0] is None:
    #     articulos = get_articles(0, lang)
    # else:
    #     articulos = get_articles(int(last_id(lang)[0]), lang)

    articles = get_articles(-1, "en")
    # articles = get_unprocessed_articles_by_ids(lang)  # 所有id在mongodb的ids集合中的文章
    # articles = get_unprocessed_articles_in_graph(lang)    # 所有不在graph中的文章
    # articles = get_unprocessed_no_entity_articles_in_graph(lang)    # 所有不在graph中且entity为空的文章
    # articles = get_unprocessed_entity_articles_in_graph(lang)   # 只挑有entity的文章
    print("Get {0} unprocessed articles.".format(len(articles)))

    for post in articles:
        if post["title"] is None:
            title = ""
        else:
            title = post["title"]

        date = post["published_at"]
        datos.append({
            "url": post["url"],
            "fila": post["_id"],
            "_id": int(post["_id"]),
            "date": date.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": post["source"],
            "title": title.replace('"', '').replace("'", ''),
            "lang": post["language"],
            "entity": post["entity"]
        })

    print('Get {0} articles.'.format(len(datos)))

    for dato in datos:
        result = calcula(dato)
        print(result)

    # p = Pool(6)
    # try:
    #     p.map(calcula, datos)
    # except TypeError:
    #     print(str(sys.exc_info()))

    # end


def weekly_scheduler(at_time):
    print("** Start weekly scheduler! **")
    print("Time execution", at_time)
    schedule.every().monday.at(at_time).do(launch)
    schedule.every().tuesday.at(at_time).do(launch)
    schedule.every().wednesday.at(at_time).do(launch)
    schedule.every().thursday.at(at_time).do(launch)
    schedule.every().friday.at(at_time).do(launch)
    schedule.every().saturday.at(at_time).do(launch)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    # weekly_scheduler(DAILY_TIME)
    launch()
