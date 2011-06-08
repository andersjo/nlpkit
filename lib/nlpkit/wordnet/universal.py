from UserDict import IterableUserDict

__author__="anders"
__date__ ="$01-04-2011 10:46:42$"

from itertools import chain, ifilter, groupby
from collections import defaultdict
import networkx as nx

class Wordnet(object):
    """A wordnet graph structure that allows lookup of synsets by lemma and synset id

    The graph is directly accessible as an attribute and need not be manipulated through this class
    as long it adheres to the structure and naming convention described below.

    Lexical units (words associated with synsets) are a part of the
    synset data structure. Links between lexical nodes are also links between synsets. They can be filtered
     on retrieval and even left out of the graph completely.

    Example node data structure

    {
        'pos': 'n',                     # can be an empty string
        'lex_units': {                  # can be a dict with no items
            '1': {'word': 'mouton'}     # lexical unit data keyed by the id of the lexical unit in the synset
            '2': {'word': 'mutton'}     # 'word' is a required attribute
        }
    }

    Example edge data structure

    {
        'type': 'hyperonym',            # required
    }
    """
    def __init__(self):
        self.G = nx.MultiDiGraph()
        self._synset_map = defaultdict(lambda: set())

    def add_synset_lookup(self, word_form, synset_id):
        self._synset_map[word_form].add(synset_id)

    def synsets(self, lemma, pos=None):
        if lemma not in self._synset_map:
            return None
        synsets = [self.Synset(node_id, self) for node_id in self._synset_map[lemma]]
        if pos != None:
            return filter(lambda s: s['pos'] == pos, synsets)
        else:
            return synsets

    def all_synsets(self):
        for n in self.G.nodes_iter():
            yield self.Synset(n, self)

    def relation_counts(self):
        edges = chain.from_iterable(self.G[src_n][target_n].values() for src_n, target_n in nx.edges_iter(self.G))
        types = [e['type'] for e in edges]
        grouped = groupby(sorted(types))
        return dict((name, len(list(vals))) for name, vals in grouped)

    def top_synsets(self):
        return list(path for s in self.all_synsets() for path in s.hypernym_paths())

    def __getitem__(self, key):
        if key in self.G.node:
            return self.Synset(key, self)

class LexUnit(IterableUserDict):
    def __init__(self, id, synset):
        self.id = id
        self._synset = synset
        self.data = self._synset['lex_units'][self.id]

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.label())

    def label(self):
        return '{}:{}:{}'.format(self._synset.id, self.id, self.lemma())

    def lemma(self):
        return self['lemma']

class Relation(IterableUserDict):
    def __init__(self, idx, src_synset, target_synset_id):
        self._idx = idx
        self._src_synset = src_synset
        self._target_synset_id = target_synset_id
        self._wordnet = self._src_synset._wordnet
        self.data = self._wordnet.G[self._src_synset.id][self._target_synset_id][self._idx]

    def is_lexical(self):
        return all(k in self for k in ['lex_src', 'lex_target'])

    def src_synset(self):
        return self._src_synset

    def target_synset(self):
        return self._wordnet.Synset(self._target_synset_id, self._wordnet)

    def src_lex_unit(self):
        return self._wordnet.LexUnit(self['lex_src'], self.src_synset())

    def target_lex_unit(self):
        return self._wordnet.LexUnit(self['lex_target'], self.src_synset())


class Synset(IterableUserDict):
    def __init__(self, id, wordnet):
        self.id = id
        self._wordnet = wordnet
        self.data = self._wordnet.G.node[self.id]

    def related(self, type=None, lex_rel=True):
        return [r.target_synset() for r in self.relations(type, lex_rel)]

    def relations(self, type=None, lex_rel=True):
        return [r for r in self._unfiltered_relations()
                if type is None or type == r['type']
                if lex_rel or not r.is_lexical()]

    def _unfiltered_relations(self):
        return [Relation(idx, self, target_synset_id)
                for target_synset_id, edges in self._wordnet.G[self.id].items()
                for idx in edges.keys()]

    def lex_units(self):
        return [self._wordnet.LexUnit(lex_id, self) for lex_id in self['lex_units'].keys()]

    def lemmas(self):
        return [lu.lemma() for lu in self.lex_units()]

    def hypernyms(self):
        return self.related(self._wordnet._hypernym_name)

    def hyponyms(self):
        return self.related(self._wordnet._hyponym_name)

    def hypernym_paths(self):
        return [[self] + path
                for h in self.hypernyms()
                for path in h.hypernym_paths()] \
        or [[self]]

#    def __getitem__(self, key):
#        return self._wordnet.G.node[self.id].get(key)

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.label())

#    def __hash__(self):
#        return self.id.__hash__()
#
#    def __eq__(self, other):
#        return self.id == other.id

    def label(self):
        return self.id



Wordnet.LexUnit = LexUnit
Wordnet.Synset = Synset