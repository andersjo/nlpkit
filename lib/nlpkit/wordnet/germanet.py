__author__="anders"
__date__ ="$01-04-2011 10:46:42$"

import xml.dom.minidom
from glob import glob
from itertools import chain
from collections import defaultdict
import networkx as nx
from os.path import basename

class GermanetV53(object):
    def __init__(self, data_dir):
        self._data_dir = data_dir
        self._lemma_synset_map = defaultdict(lambda: set())
        self.G = nx.DiGraph()
        self._read()

    def _read(self):
        self._read_object_files()
        self._read_relations()

    def _read_object_files(self):
        files = [   glob(self._data_dir + "/" + prefix + "*xml")
                    for prefix in ['adj', 'nomen', 'verben'] ]
        for file in chain.from_iterable(files):
            filename = basename(file)
            dom = xml.dom.minidom.parse(file)
            dom.normalize()
            for synset in dom.getElementsByTagName('synset'):
                node_id = synset.getAttribute('id')
                self.G.add_node(node_id)
                lemmas = set([lemma_node.firstChild.data for lemma_node in synset.getElementsByTagName('orthForm')])
                self.G.node[node_id]['lemmas'] = lemmas
                self.G.node[node_id]['pos'] = self._map_category_to_pos(synset.getAttribute('category'))
                self.G.node[node_id]['filename'] = filename
                for lemma in lemmas:
                    self._lemma_synset_map[lemma.lower()].add(node_id)

    def _read_relations(self):
        dom = xml.dom.minidom.parse(self._data_dir + "/gn_relations.xml")
        for rel_node in dom.getElementsByTagName('con_rel'):
            attr_nodes = [rel_node.attributes.item(i) for i in range(0, rel_node.attributes.length)]
            a = dict([(n.name, n.value) for n in attr_nodes])
            self.G.add_edge(a['from'], a['to'], type=a['name'])
            if a['dir'] == 'both':
                self.G.add_edge(a['to'], a['from'], type=a['name'])
            elif a['dir'] == 'revert':
                self.G.add_edge(a['to'], a['from'], type=a['inv'])

    def _map_category_to_pos(self, category):
        return {'nomen': 'n', 'adj': 'a', 'verben': 'v'}[category]

    def synsets(self, lemma_str, pos='n'):
        synsets = [Synset(node_id, self) for node_id in self._lemma_synset_map[lemma_str]]
        if pos != None:
            return filter(lambda s: s['pos'] == pos, synsets)
        else:
            return synsets

Germanet = GermanetV53

class Synset(object):
    def __init__(self, id, net):
        self._id = id
        self._net = net
        self.G = net.G

    def rels(self, type):
        return [Synset(target, self._net)
                for target, attr in self.G[self._id].items()
                if attr['type'] == type ]

    def hyponyms(self):
        return self.rels('hyponymy')

    def __getitem__(self, key):
        return self.G.node[self._id].get(key)

if __name__ == "__main__":
    for tagged_word in [('kommen', 'v'), ('zeit', 'n')]:
        print tagged_word
        print alt_words_de(tagged_word, '')
#    gn = Germanet('../data/GN_V53')


