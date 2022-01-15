from  spacy.lang.ja import stop_words
import nltk
import ginza
import spacy
import pke
import string
pke.base.lang_stopwords['ja_ginza'] = 'japanese'

stopwords = list(stop_words.STOP_WORDS)
nltk.corpus.stopwords.words_org = nltk.corpus.stopwords.words
nltk.corpus.stopwords.words = lambda lang: stopwords if lang == 'japanese' else nltk.corpus.stopwords.words_org(lang)


class Keyphrase_extractor(object):
    def __init__(self) -> None:
        super().__init__()
        self.language = 'ja_ginza'
        self.target_pos = ['NOUN']
        self.spacy_model = spacy.load('ja_ginza_electra')
       
    def __call__(self, text, keyphrase_num=10, model_type='MultipartiteRank', pos_limit=True, join=True, **args):
        if model_type == 'MultipartiteRank':
            n_best = self.multi_partite_rank(text, keyphrase_num, **args)
        elif model_type == 'YAKE':
            n_best = self.yake(text, keyphrase_num, **args)
        
        if pos_limit:
            n_best = self.pos_check(n_best)

        if join:
            n_best = [
                (''.join(k.split(' ')), s) for k, s in n_best
            ]

        return n_best

    def multi_partite_rank(self, text, keyphrase_num, threshold=0.74, method='average', alpha=1.1, **args):
        extractor = pke.unsupervised.MultipartiteRank()
        extractor.load_document(
            input=text, language=self.language, normalization=None, spacy_model=self.spacy_model)

        candidate_entity = {'NOUN', 'PROPN', 'ADJ'}
        jp_stoplist = list(string.punctuation)
        jp_stoplist += nltk.corpus.stopwords.words('japanese')

        extractor.candidate_selection(
            pos=candidate_entity, stoplist=jp_stoplist)
        extractor.candidate_weighting(
            threshold=threshold, method=method, alpha=alpha)
            
        return extractor.get_n_best(n=keyphrase_num)

    def yake(self, text, keyphrase_num, threshold=0.8, window=2, use_stems=False, **args):
        extractor = pke.unsupervised.YAKE()
        extractor.load_document(
            input=text, language=self.language, normalization=None, spacy_model=self.spacy_model)
        jp_stoplist = nltk.corpus.stopwords.words('japanese')
        extractor.candidate_selection(n=3, stoplist=jp_stoplist)
        extractor.candidate_weighting(window=window, stoplist=jp_stoplist, use_stems=use_stems)

        return extractor.get_n_best(n=keyphrase_num, threshold=threshold)

    def pos_check(self, n_best):
        new_n_best = []
        for kp, score in n_best:
            doc = self.spacy_model(kp)
            for pos in self.target_pos:
                if pos in [t.pos_ for t in doc]:
                    new_n_best.append((kp, score))
                    break
        return new_n_best
