import pandas as pd
import re
import datetime
import os
from neo4j_functions import *


def create_sdg_from_csv(filename, lang="en"):
    df = pd.read_csv(filename, sep=",")
    date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    for row in df.iterrows():
        ODS = row[1].values[0]
        relation = row[1].values[1]
        token = row[1].values[2]

        ODS_name, ODS_id = re.findall("{nombre:(.*),id:(.*)}", ODS)[0]
        weight = re.findall("{peso:(.*)}", relation)[0]
        concept, text = re.findall("{concept:(.*),text:(.*)}", token)[0]

        crea_ods_corpus(ODS_id, ODS_name, lang)
        add_token(text, concept, lang)
        insert_relation_token_ods_import_corpus(text, concept, ODS_id, weight, date, lang)


if __name__ == "__main__":
    filepath_ods = "./Corpus/"

    for filename in os.listdir(filepath_ods):
        if not os.path.isdir(filename):
            create_sdg_from_csv(filepath_ods + filename, "en")
            print(filename + " completed.")


