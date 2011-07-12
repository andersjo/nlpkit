import codecs
import universal
import re
from nlpkit.paths import data_path

class Ukb(universal.Wordnet):
    @classmethod
    def load(cls, dict_filename, rels_filename):
        return UkbLoader(Ukb(), dict_filename, rels_filename).load()


class UkbLoader(object):
    def __init__(self, wordnet, dict_filename, rels_filename):
        self._wordnet = wordnet
        self._G = wordnet.G
        self._dict_filename = data_path(dict_filename)
        self._rels_filename = data_path(rels_filename)

    def load(self):
        self._load_dict()
        self._load_rels()
        return self._wordnet

    def _load_dict(self):
        with codecs.open(self._dict_filename, encoding='utf-8') as dict_file:
            for line in dict_file:
                space_at = line.index(" ")
                lemma = line[:space_at]
                for synset_id in re.findall("[^-\s]+-\w", line[space_at+1:-1]):
                    self._add_synset(synset_id, synset_id.split("-")[1])
                    self._add_lemma(synset_id, lemma)


    def _load_rels(self):
        rel_re = re.compile(r"u:([^:\s]+)\sv:([^:\s]+)")
        with codecs.open(self._rels_filename, encoding='utf-8') as rels_file:
            for line in rels_file:
                m = rel_re.match(line)
                self._G.add_edge(m.group(1), m.group(2), type='unknown')

    def _add_lemma(self, synset_id, lemma):
        lex_units = self._G.node[synset_id]['lex_units']
        if len(lex_units):
            last_key = sorted(lex_units.keys())[-1]
            next_key = last_key + 1
        else:
            next_key = 0
        lex_units[next_key] = {'lemma': lemma}

    def _add_synset(self, synset_id, pos):
        if not synset_id in self._G:
            self._G.add_node(synset_id, {
                'pos': pos,
                'lex_units': {}
            })

if __name__ == '__main__':
    wn = Ukb.load('wordnets/ukb/dicts/wn30.txt', 'wordnets/ukb/rels/wnet30_and_g_rels.txt')
#    loader = Wn30Loader(Wn30(), 'wordnets/wn30_food')
#    wn = loader.load()