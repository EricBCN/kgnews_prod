#! /usr/bin/env python

# IMPORTS
import schedule
import sys
import getopt
import time
from extractors.news_api import NewsAPI
from logger import logger
from nlp.tagger import spacy_ner_tagger
from scrapper.scrapper import scrapper


# LANGUAGE = 'en'
DAILY_TIME = "02:00"


extractor_list = list()
extractor_list.append(NewsAPI(language='es'))
extractor_list.append(NewsAPI(language='en'))


def launch():
    for extractor in extractor_list:
        logger.debug(f'Executing extractor {extractor.get_name()}')
        extractor.run()

    logger.debug('Parsing extracted content')
    scrapper.parse()

    logger.debug('Tagging parsed content')
    spacy_ner_tagger.tag()
    # end


# One for each day
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


def main(argv):
    time = None
    try:
        opts, args = getopt.getopt(argv, "ht:", ["time="])
    except getopt.GetoptError:
        print('scheduled_launcher.py  -t <time>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('scheduled_launcher.py -t <time>')
            print('Example: scheduled_launcher.py -l es -t 10:00')
            sys.exit()
        elif opt in ("-t", "--time"):
            time = arg

    if time == None:
       time = DAILY_TIME

    print("\n API NEWS Scheduled Launcher execution DAILY_TIME:", time)

    weekly_scheduler(time)


# #####   APP EXECUTION     ##### #


if __name__ == "__main__":
    main(sys.argv[1:])
