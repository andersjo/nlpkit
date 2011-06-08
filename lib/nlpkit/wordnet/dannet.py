# coding: utf-8
from itertools import count
import codecs
from nlpkit.wordnet import generic
from nlpkit.paths import data_path

class DannetSynset(generic.Synset):
    def label(self):
        return self['label']

class DannetLex(generic.LexUnit):
    def label(self):
        return self['word']

    def lemma(self):
        return self['word']

class Dannet(generic.Wordnet):
    Synset = DannetSynset
    LexUnit = DannetLex

    @classmethod
    def load(cls, path):
        return DannetLoader(path).load()

class DannetLoader(object):
    REVERSE_RELATIONS = {
       u'has_holonym': u'has_meronym',
       u'has_holo_location': u'has_mero_location',
       u'has_holo_madeof': u'has_mero_madeof',
       u'has_holo_member': u'has_mero_member',
       u'has_holo_part': u'has_mero_part',
       u'has_hyperonym': u'has_hyponym',
       u'has_hyponym': u'has_hyperonym',
       u'has_meronym': u'has_holonym',
       u'has_mero_location': u'has_holo_location',
       u'has_mero_madeof': u'has_holo_madeof',
       u'has_mero_member': u'has_holo_member',
       u'has_mero_part': u'has_holo_part'}

    POS_MAP = {'Noun': 'n', 'Adjective': 'a', 'Verb': 'v'}
#    REVERSE_RELATIONS.update(dict((r2, r1) for r1, r2 in REVERSE_RELATIONS.items()))

    def __init__(self, dannet_path):
        self.dannet_path = data_path(dannet_path)
        self.dannet = Dannet()
        self._words = {}
        self._wordsense_ids = count()

    def load(self):
        self._load_synsets()
        self._load_synset_attributes()
        self._load_words()
        self._load_wordsenses()
        self._load_relations()
        return self.dannet

    def _load_rows(self, filename, header_line, callback):
        header = header_line.split()
        path = '{}/{}'.format(self.dannet_path, filename)
        with codecs.open(path,encoding="iso8859-1") as f:
            for line in f:
                parts = line.strip().split("@")
                callback(dict(zip(header, parts)))

    def _load_synsets(self):
        #  id:    Id of synset. This id will remain constant in future versions
        #         of DanNet.
        #  label: Name of synset based on the word forms linked to this synset.
        #         It is only intended as a convenience for the user. For
        #         information about the lexical forms, please refer to words.csv.
        #  gloss: Gloss of the synsets. Consists of a small part of the definition
        #         from the Danish Dictionary plus hand-selected examples from the
        #         corpus.
        #  ontological_type: Ontological type of the synset, e.g. 'Comestible'
        #         or 'Vehicle+Object+Artifact'.
        def _load_synset(row):
            self.dannet.S.add_node(row['id'], row)
        self._load_rows("synsets.csv", "id label gloss ontological_type", _load_synset)

    def _load_synset_attributes(self):
        # synset_id:    Id of synset
        # name:         Name of attribute. Currently one of 'domain' and 'connotation'
        # value:        Attribute value
        def _load_synset_attribute(row):
            self.dannet.S.node[row['synset_id']][row['name']] = row['value']
        self._load_rows("synset_attributes.csv", "synset_id name value", _load_synset_attribute)

    def _load_words(self):
        #  id:    Id for the lexical entry. This will be stable through future
        #         versions of DanNet. However, for some id's a number has been
        #         appended to the core id with a hyphen (e.g. '...-1'. This part
        #         of the id might unfortunately in rare cases change in future
        #         releases, while the core part will be stable.
        #  form:  The lexical form of the entry
        #  pos:   The part of speech of the entry
        def _load_word(row):
            self._words[row['id']] = row
        self._load_rows("words.csv", "id form pos", _load_word)

    def _load_wordsenses(self):
        #  ddo_id: Id of the wordsense in the DDO dictionary
        #  wordsense_id:   Id of the word sense
        #  synset_id: Id of the synset (in the synsets.csv file)
        #  register:  Some word senses may be marked as non-standard, e.g.
        #             'sj.' for seldomly used, 'gl.' for old-fashionable,
        #             or 'slang'.
        #             In general, if a value is present for a word sense in
        #             this column, it may be regarded as non-standard use.
        def _load_wordsenses(row):
            wordsense_id = self._wordsense_ids.next()
            word = self._words[row['word_id']]['form']
            pos = self._words[row['word_id']]['pos']

            lex_unit_data = {'word': word,
                             'pos': self.POS_MAP.get(pos) }
            lex_unit_data.update(row)
            self.dannet.L.add_node(wordsense_id, lex_unit_data)
            self.dannet.add_synset_lookup(word, row['synset_id'])
            self.dannet.L.add_edge(row['synset_id'], wordsense_id, type='synset')
        self._load_rows("wordsenses.csv", "ddo_id word_id synset_id register", _load_wordsenses)

    def _load_relations(self):
        #  synset_id: Id of the synset is described by the relation.
        #  name:      The name of the relation (in wordnet/owl terminology)
        #  name2:     the name of the relation (i EuroWordNet terminology)
        #  value:     The target of the relation. The Value is always an id
        #             of a synset (in the synsets.csv file), a dummy (in
        #             the dummies.csv file), or a Princeton Wordnet synset.
        #  taxonomic: Possible values: 'taxonomic' or 'nontaxonomic'
        #             Distinguishes between taxonomic and nontaxonomic
        #             hyponymy, cf. the specifications for DanNet
        #             (http://wordnet.dk/download_html). Available only in
        #             Danish. Only relevant for the hyponymOf relation.
        #  inheritance_comment: A synset inherits relations from hypernyms
        #             If a relation is inherited rather than supplied for the
        #             particular synset, a text comment will state from which
        #             synset the relation stems.
        def _load_relation(row):
            # Link to Princeton Wordnet. Could possibly be imported as an empty node
            if row['value'].startswith("ENG"):
                return
            edge_attr = dict((k,v) for k,v in row.items() if k in ['inheritance_comment', 'taxonomic'])
            edge_attr['type'] = row['name2']
            self._add_edge_unless_dup(row['synset_id'], row['value'], edge_attr)
            if row['name2'] in self.REVERSE_RELATIONS:
                reverse_edge_attr = dict(edge_attr)
                reverse_edge_attr['type'] = self.REVERSE_RELATIONS[row['name2']]
                self._add_edge_unless_dup(row['value'], row['synset_id'], reverse_edge_attr)
        self._load_rows("relations.csv", "synset_id name name2 value taxonomic inheritance_comment", _load_relation)

    def _add_edge_unless_dup(self, src_n, target_n, edge_attr):
        # Avoid the duplicate edges that are seemingly present in the input data
        if src_n in self.dannet.S.edge and target_n in self.dannet.S.edge[src_n]:
            if any(e['type'] == edge_attr['type'] for e in self.dannet.S.edge[src_n][target_n].values()):
                return
        self.dannet.S.add_edge(src_n, target_n, attr_dict=edge_attr)

if __name__ == '__main__':
    path = data_path('wordnets/dannet/1.4')
    loader = DannetLoader(path)
    loader.load()
    d = loader.dannet