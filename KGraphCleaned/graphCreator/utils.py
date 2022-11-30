from nltk.sentiment.vader import SentimentIntensityAnalyzer
from pysentimiento import create_analyzer   # currently only support english and spanish
from googletrans import Translator  # Google translator
from nltk.corpus import wordnet
import os


sid = SentimentIntensityAnalyzer()
translator = Translator()


def get_sentiment_score(text, lang):
    if lang == 'en':
        sent_score = sid.polarity_scores(text)["compound"]
    else:
        analyzer = create_analyzer(task="sentiment", lang=lang)
        sentiment = analyzer.predict(text).output.lower()

        if sentiment == 'neu':
            sent_score = 0
        elif sentiment == 'pos':
            sent_score = 1
        else:
            sent_score = -1

    return sent_score


def get_dict_path(lang='en'):
    current_path = os.path.dirname(__file__)
    parent_path = os.path.dirname(current_path)

    return parent_path + "/dict/dict_{0}.txt".format(lang)


# Get dictionary from .txt file
def get_dict_from_file(lang):
    if lang != 'en':
        dictionary = {}
        dict_filepath = get_dict_path(lang)

        with open(dict_filepath, 'r', encoding='latin-1') as f:
            for line in f.readlines():
                line = line.strip()
                k = line.split(';')[0]
                v = line.split(';')[1]
                dictionary[k] = v

            f.close()
            return dictionary
    else:
        return None


def get_concept(word, lang, dictionary=None):
    if word[-3:] == ' él':
        word = word[:-3]

    if lang == 'en':
        word_en = word.replace("\'", "").replace("\\", "")
    else:
        if dictionary is not None and word in dictionary:
            return dictionary[word]     # find the concept of the word in the dictionary
        else:
            word_en = translator.translate(word, src=lang).text.replace("\'", "").replace("\\", "")

    try:
        syns = wordnet.synset(word_en + ".n.01")
        concept = syns.lemma_names()[0]
    except:
        concept = word_en

    return concept.lower().replace("\'", "").replace("\\", "")
