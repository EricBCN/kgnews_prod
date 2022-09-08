import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import pyLDAvis
import spacy
from bokeh.plotting import figure, show
from gensim.corpora import Dictionary
from gensim.models import LdaModel, Phrases, CoherenceModel
from pyLDAvis import gensim
from sklearn.manifold import TSNE

from logger import logger
from utils import mongokit_connector


def get_documents():
    result = mongokit_connector.KGNews.test_news.find({'source_type': {'$in': ['ODS_EXTRACTOR', 'CUSTOM_EXTRACTOR']}})
    logger.debug(f'Allocated {result.count()} articles')
    return result


def preprocess_data(documents):
    # nlp = spacy.load('es_core_news_sm')
    nlp = spacy.load('en_core_web_sm')

    tokenized_docs = list()
    for doc in documents:
        # Lower case the text
        doc = doc.lower()
        # Tokenize the text
        doc = nlp(doc)

        tokenized_docs.append(doc)

    # Remove words that are only one character or stop words.
    #  Also use spaCy's lemma_ attribute to extract the token lemma.
    tokenized_docs = [[token.lemma_ for token in doc if len(token) > 1 and not token.is_stop] for doc in
                      tokenized_docs]

    logger.debug('Tokenized and lemmatized articles')

    # NOTE: We add the bigrams and trigrams because we want to keep both the original and the
    # chunked data. If we only wanted the chunks, we'd need to replace the original content.
    # Add bigrams and trigrams to docs (only ones that appear 5 times or more)
    # higher threshold fewer phrases.
    bigram = Phrases(tokenized_docs, min_count=5, threshold=100)
    trigram = Phrases(bigram[tokenized_docs], threshold=100)

    for idx in range(len(tokenized_docs)):
        for token in bigram[tokenized_docs[idx]]:
            if '_' in token:
                logger.debug(f'- Bigram {token}')
                # Token is a bigram, add to document.
                tokenized_docs[idx].append(token)

    """
    for idx in range(len(tokenized_docs)):
        for token in trigram[tokenized_docs[idx]]:
            if token.count('_') > 1:
                logger.debug(f'- Trigram {token}')
                # Token is a trigram, add to document.
                tokenized_docs[idx].append(token)
    """

    logger.debug('Added bigrams and trigrams')

    # Remove rare and common tokens.
    # Create a dictionary representation of the documents.
    dictionary = Dictionary(tokenized_docs)

    # Filter out words that occur less than 5 documents, or more than 30% of the documents.
    dictionary.filter_extremes(no_below=10, no_above=0.5)

    logger.debug('Removed rare and common tokens')

    # Bag-of-words representation of the documents.
    corpus = [dictionary.doc2bow(doc) for doc in tokenized_docs]

    logger.debug('Created BoW representation:')
    logger.debug(f'\tNumber of unique tokens: {len(dictionary)}')
    logger.debug(f'\tNumber of documents: {len(corpus)}')
    return dictionary, corpus, tokenized_docs


def train(dictionary, corpus, tokenized_docs, no_topics):
    # Set training parameters.
    num_topics = no_topics
    chunksize = 10
    passes = 20
    iterations = 4000
    # Don't evaluate model perplexity, takes too much time.
    eval_every = None

    logger.debug('Training LDA model')

    # Make a index to word dictionary.
    # This is only to "load" the dictionary.
    # temp = dictionary[0]
    #  id2word = dictionary.id2token

    model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        chunksize=chunksize,
        alpha='auto',
        eta='auto',
        iterations=iterations,
        num_topics=num_topics,
        passes=passes,
        # By providing a random state we avoid the issue with recurrent executions generating different models
        random_state=1,
        eval_every=eval_every
    )

    top_topics = model.top_topics(corpus)  # , num_words=20)

    # Average topic coherence is the sum of topic coherences of all topics, divided by the number of topics.
    avg_topic_coherence = sum([t[1] for t in top_topics]) / num_topics
    logger.debug(f'Average topic coherence: {avg_topic_coherence}')
    logger.debug(f'Perplexity: {model.log_perplexity(corpus)}')
    coherence_model_lda = CoherenceModel(model=model, texts=tokenized_docs, dictionary=dictionary, coherence='c_v')
    coherence_lda = coherence_model_lda.get_coherence()
    logger.debug(f'Coherence Score: {coherence_lda}')

    from pprint import pprint
    pprint(top_topics)

    return model


def show_pyldavis(model, corpus):
    vis = gensim.prepare(model, corpus, model.id2word)
    logger.debug(vis)

    '''
    FIXME: visualization with complex objects fails because the numpy enconder within pyLDAvis doesn't work well.
    The following LOCs have to be added to utils.py
    
        if np.iscomplexobj(obj):
            return abs(obj)
            
    https://github.com/bmabey/pyLDAvis/issues/69
    '''
    pyLDAvis.show(vis)


def show_tsne_clustering_chart(model, corpus, no_topics):
    # 1. Calculate topic weights
    topic_weights = []
    for i, row_list in enumerate(model[corpus]):
        topic_weights.append([w for i, w in row_list])

    # Generate an array of topic weights
    arr = pd.DataFrame(topic_weights).fillna(0).values

    # Keep the well separated points (optional)
    arr = arr[np.amax(arr, axis=1) > 0.35]

    # Mark the dominant topic in each document
    topic_num = np.argmax(arr, axis=1)

    # tSNE dimension reduction
    tsne_model = TSNE(n_components=2, verbose=1, random_state=0, angle=.99, init='pca')
    tsne_lda = tsne_model.fit_transform(arr)

    # Plot the clusters using Bokeh
    my_colors = np.array([color for name, color in mcolors.TABLEAU_COLORS.items()])
    plot = figure(title=f't-SNE Clustering of {no_topics} LDA Topics', plot_width=900, plot_height=700)
    plot.scatter(x=tsne_lda[:, 0], y=tsne_lda[:, 1], color=my_colors[topic_num])
    show(plot)


def main():
    NO_TOPICS = 17

    # 1. Extract the documents
    docs = list(map(lambda doc: doc['content'], get_documents()))

    # 2. Preprocess and vectorize the docs
    dictionary, corpus, tokenized_docs = preprocess_data(docs)

    # 3. Train the LDA model
    model = train(dictionary, corpus, tokenized_docs, NO_TOPICS)

    # 4. Visualize the LDA model weights
    show_tsne_clustering_chart(model, corpus, NO_TOPICS)
    show_pyldavis(model, corpus)


if __name__ == '__main__':
    main()
