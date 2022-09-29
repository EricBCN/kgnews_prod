from neo4j_functions import last_id
from graphCreator import calcula
from mongo import *
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

    articles = get_unprocessed_articles(lang)

    for post in articles:
        if post["title"] is None:
            title = ""
        else:
            title = post["title"]

        date = post["published_at"]
        datos.append({
            "url": post["url"],
            "fila": post["_id"],
            "_id": post["_id"],
            "date": date.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": post["source"],
            "title": title.replace('"', '').replace("'", ''),
            "lang": post["language"]
        })

    print('Get {0} articles.'.format(len(datos)))

    # for dato in datos:
    #     calcula(dato)

    p = Pool(6)
    try:
        p.map(calcula, datos)
    except TypeError:
        print(str(sys.exc_info()))

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
