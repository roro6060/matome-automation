


class Ng_Word_Ctrl(object):
    def __init__(self, ng_word_file_path=None) -> None:
        self.ng_word_file_path = ng_word_file_path
        self.ng_words = []
        self.load_ng_words()

    def load_ng_words(self):
        if self.ng_word_file_path is not None:
            with open(self.ng_word_file_path, mode='rt', encoding='utf-8') as f:
                self.ng_words.extend([l.rstrip('\n')
                                     for l in f.readlines() if l.rstrip('\n') != ''])
    
    def replace(self, text):
        if not self.ng_words:
            return text
        for ng_w in self.ng_words:
            if ng_w in text:
                text = text.replace(ng_w, self.filled_word(ng_w))
        return text

    def has_ng_word(self, text):
        if not self.ng_words:
            return False
        for ng_w in self.ng_words:
            if ng_w in text:
                return True
        return False

    def filled_word(self, word, key='○'):
        count = len(word)
        w = [key if i % 2 == 0 else w for i, w in zip(range(count), word)]
        return ''.join(w)
