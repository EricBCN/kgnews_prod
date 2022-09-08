# Función Multiproceso
from neo4j_functions import * #id_in_graph, crea_ods, add_News, add_sentence, add_token
from spacy.lang.es.stop_words import STOP_WORDS
import spacy
from httpSessionWithTimeout import HttpSessionWithTimeout, HEADERS
from boilerpy3 import extractors
from tqdm import tqdm
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import wordnet
from newspaper import Article
sid = SentimentIntensityAnalyzer()
extractor = extractors.ArticleExtractor()
stopwords = list(STOP_WORDS)
valid_tags = ["ADJ", "ADP", "AUX", "CONJ", "NOUN", "NUM", "PROPN", "VERB"]


def takeSecond(elem):
    return elem[1]


def calcula(datos):
    url = datos["url"]
    fila = datos["fila"]
    lang = datos["lang"]
    _id = datos["_id"]
    date = datos["date"]
    source = datos["source"]
    title = datos["title"]
    myid = "fila" + str(fila) + "+" + str(_id)

    print(_id)
    print(myid)

    if id_in_graph(lang, _id):
        print("Ya está")
        return
    
    ODS = [0] * 18
    crea_ods(myid, lang)

    print("1. Extraemos texto de url " + url)
    try:
        session = HttpSessionWithTimeout()
        session.headers.update(HEADERS)
        resp = session.get(url)
        texto_extraido = extractor.get_content(resp.text).replace("\'", "").replace("\\", "")

        article = Article(url)
        article.download()
        article.parse()
        article_url = article.top_image
    except:
        print("Error. No puedo leer esa URL. Continúo." + url)
        borra_articulo(myid, lang)
        return
    else: 
        #Calculamos el sentimiento e insertamos la noticia
        #print("Longitud : " + str(len(texto_extraido)))
        #print(texto_extraido)
        
        if len(texto_extraido) < 250:
            borra_articulo(myid, lang)
            return
        ss = sid.polarity_scores(texto_extraido)
        
        print("2. Insertamos en grafo. " + url + str(fila) + myid )
        # Seleccionamos idioma en función de lang
        if (lang == "es"):        
            nlp = spacy.load("es_core_news_sm")
        else:
            nlp = spacy.load("en_core_web_md")

        try:
            frases = nlp(texto_extraido)
        except Exception as e:
            print(e)
            borra_articulo(myid, lang)
            return

        words = [token.text for token in frases if token.is_stop != True and token.is_alpha and len(token.lemma_) > 1]
        palabras = len(words)
        sostenibilidad = [0] * 18
        frase_anterior = 0
        
        if palabras < 1000:
            add_News(texto_extraido[:100], str(ss["compound"]), url, _id, date, source, title, article_url, lang)
            with tqdm(total=int(palabras)) as pbar:
                for texto in frases.sents:
                    frase = texto.text.replace("\n", "")
                    ss = sid.polarity_scores(frase)
                    frase_anterior2 = add_sentence(frase, str(ss["compound"]), frase_anterior, lang)
                    add_news_sentence_relation(texto_extraido[:100], frase, date, lang)
                    if frase_anterior2 == []:
                        frase_anterior = 0
                    else:
                        frase_anterior = frase_anterior2[0]
                
                    for t in texto:                
                        if t.is_alpha and not t.is_stop and len(t.lemma_) > 1:
                        #for x in valid_tags:
                        #    if x in t.tag_:
                            concept = ""
                            try:
                                syns = wordnet.synset(t.lemma_.lower().replace("\'", "").replace("\"", "") + ".n.01")
                                concept = syns.lemma_names()[0].lower().replace("\'", "").replace("\"", "")
                            except:
                                concept = t.lemma_.lower().replace("\'", "").replace("\"", "")

                            add_token(t.lemma_.lower().replace("\'", "").replace("\"", ""), concept, lang)
                            add_token_sentence_relation(t.lemma_.lower().replace("\'", "").replace("\"", ""), frase, t.tag_, date, lang)

                            # valores = peso_de_token(t.lemma_.lower().replace("\'", "").replace("\"", ""), myid, lang)
                            # palabras += 1
                            valores = peso_de_token(concept, lang)    # modify
                            if len(valores) > 0:
                                for x in valores:
                                #print(str(x))
                                    ODS[x[1]] += x[2]
                                    sostenibilidad[x[1]] += 1
                                #palabrasODS += 1

                            inserta_relacion_token_ODS(t.lemma_.lower().replace("\'", "").replace("\"", ""), myid,
                                                       palabras, date, lang)
                            pbar.update(1)

            ordenado = [0] * 17
            suma = 0
            ODS[0] = 0
            porcien = porcientos(lang)

            # for x in range(1,18):
            #     ordenado[x - 1] = (x, ODS[x] / porcien[x-1][1]) #* palabrasODS / palabras)
            #     suma += ODS[x] / porcien[x-1][1]

            ODS.pop(0)
            ODS2 = [0] * 17
            # item = 0
            maxValor = 0
            maxODS = 0

            for item in range(17):
            # for o in ordenado:
                valorODS = ODS[item] / porcien[item][1]
                ODS2[item] = valorODS * (1 + sostenibilidad[item + 1] / palabras)
                if ODS2[item] > maxValor:
                    maxValor = ODS2[item]
                    maxODS = item + 1
                # item += 1

            is_ods = 0

            print(str(ODS2))
            print(str(maxValor))
            print(str(maxODS))

            if maxValor > 0.55:
                is_ods = 1

            inserta_relacion_News_ODS(texto_extraido[:100], ODS2, date, maxODS, maxValor, is_ods, lang)
            actualiza_covid(texto_extraido[:100], lang)

        borra_articulo(myid, lang)
