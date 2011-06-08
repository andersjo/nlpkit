# coding: utf-8
import universal
import re
from nlpkit.paths import data_path
from itertools import izip_longest
import os.path
from glob import glob

class Wn30Synset(universal.Synset):
    def hypernyms(self):
        return self.related('@') + self.related('@i')

    def label(self):
        first_lemma = '' if not self.lemmas() else self.lemmas()[0]
        return '{} {} {}'.format(self.id, self['gloss'], first_lemma)

class Wn30(universal.Wordnet):
    Synset = Wn30Synset
    _hyponym_name = '~'

    @classmethod
    def load(cls, path):
        return Wn30Loader(Wn30(), path).load()


class Wn30Loader(object):
    def __init__(self, wordnet, path):
        self._wordnet = wordnet
        self._G = wordnet.G
        self._path = data_path(path)

    def load(self):
        for filename in glob(os.path.join(self._path, "data*")):
            with open(filename) as file:
                for line in file:
                    if line.startswith("  "):
                        continue
                    try:
                        fields = self._parse_line(line.strip())
                        self._handle_fields(fields)
                    except StandardError as e:
                        print "Error while parsing {}: {}".format(filename, line)
                        print e.message
                        raise e
        return self._wordnet

    def format_synset_id(self, offset, pos):
        return "{}-{}".format(offset, pos)

    # http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
    def _grouper(self, iterable, n, fillvalue=None):
        args = [iter(iterable)] * n
        return izip_longest(*args, fillvalue=fillvalue)

    def _handle_fields(self, fields):
        synset_id = self.format_synset_id(fields['synset_offset'][0], fields['ss_type'][0])
        synset_data = {
            'pos': fields['ss_type'][0],
            'gloss': fields['gloss'],
            'semantic_file': fields['lex_filenum'][0],
            'lex_units': {}
        }
        self._G.add_node(synset_id, synset_data)

        self._handle_words(synset_id, fields.get('words', []))
        self._handle_pointers(synset_id, fields.get('pointers', []))

    def _handle_words(self, synset_id, words):
        # word
        # ASCII form of a word as entered in the synset by the lexicographer, with spaces replaced by underscore characters (_ ).
        # The text of the word is case sensitive, in contrast to its form in the corresponding index. pos file, that contains only lower-case forms.
        # In data.adj , a word is followed by a syntactic marker if one was specified in the lexicographer file.
        # A syntactic marker is appended, in parentheses, onto word without any intervening spaces.
        # See wninput(5WN) for a list of the syntactic markers for adjectives.
        #
        # lex_id    ! Note that lex_id means something different in nlpkit
        # One digit hexadecimal integer that, when appended onto lemma , uniquely identifies a sense within a lexicographer file.
        # lex_id numbers usually start with 0 , and are incremented as additional senses of the word are added to the same file,
        # although there is no requirement that the numbers be consecutive or begin with 0 .
        # Note that a value of 0 is the default, and therefore is not present in lexicographer files.
        for i, word in enumerate(words[::2]):
            self._G.node[synset_id]['lex_units'][i+1] = {'lemma': word.lower()}
            # FIXME strip out parenthesis
            self._wordnet.add_synset_lookup(word.lower(), synset_id)

    def _handle_pointers(self, synset_id, pointers):
        # ptr is of the form
        #   pointer_symbol  synset_offset  pos  source/target
        # The source/target field distinguishes lexical and semantic pointers.
        # It is a four byte field, containing two two-digit hexadecimal integers.
        # The first two digits indicates the word number in the current (source) synset,
        # the last two digits indicate the word number in the target synset.
        # A value of 0000 means that pointer_symbol represents a semantic relation between the current (source) synset
        # and the target synset indicated by synset_offset .
        # A lexical relation between two words in different synsets is represented by non-zero values in the source and target word numbers.
        # The first and last two bytes of this field indicate the word numbers in the source and target synsets,
        # respectively, between which the relation holds. Word numbers are assigned to the word fields in a synset,
        # from left to right, beginning with 1 .
        for ptr_sym, offset, pos, src_target in self._grouper(pointers, 4):
            target_synset_id = self.format_synset_id(offset, pos)
            if src_target == '0000':
                self._G.add_edge(synset_id, target_synset_id, type=ptr_sym)
            elif len(src_target) == 4:
                self._G.add_edge(synset_id, target_synset_id,
                                 type=ptr_sym,
                                 lex_src=int(src_target[0:2], 16),
                                 lex_target=int(src_target[2:4], 16))
            else:
                raise StandardError("An error")

    def _parse_line(self, line):
        """Parse the fields of a single line and return the result as dict of token lists."""
        d = dict()

        def unpack(tail, names, count=1):
            if len(tail) == 0:
                return
            name = names[0]
            rest = tail[count:]
            if name == 'w_cnt':
                unpack(rest, names[1:], int(tail[0], 16) * 2)
            elif name == 'p_cnt':
                unpack(rest, names[1:], int(tail[0]) * 4)
            elif name == 'f_cnt':
                unpack(rest, names[1:], int(tail[0]) * 3)
            else:
                d[name] = tail[0:count]
                unpack(rest, names[1:])

        # Format of line according to http://wordnet.princeton.edu/wordnet/man/wndb.5WN.html
        #     synset_offset  lex_filenum  ss_type  w_cnt  word  lex_id  [word  lex_id...]  p_cnt  [ptr...]  [frames...]  |   gloss
        data, gloss = line.split("|")
        d['gloss'] = gloss
        line_spec = 'synset_offset lex_filenum ss_type w_cnt words p_cnt pointers f_cnt frames'.split()
        unpack(data.split(), line_spec)
        return d

# FIXME fold this into the universal.framework
class WN30Matcher(object):
    def __init__(self):
        from nltk.corpus import wordnet as wn
        from nlpkit.wordnet.wn30 import fix_pos, format_synset_id

        self.wn = wn
        self.fix_pos = fix_pos
        self.format_synset_id = format_synset_id

    def select(self, what, synset_id):
        meth = getattr(self, what.replace('-', '_'))
        return meth(synset_id)

    def synset(self, synset_id):
        return set([synset_id])

    def grand_parent(self, synset_id):
        return set(gp_id for parent_id in self.parent(synset_id) for gp_id in self.parent(parent_id))

    def _synset(self, synset_id):
        synset_id_m = re.match("^(\d+)-(\w)$", synset_id)
        return self.wn._synset_from_pos_and_offset(synset_id_m.group(2), int(synset_id_m.group(1)))

    def parent(self, synset_id):
        hypernyms = self._synset(synset_id).hypernyms()
        if hypernyms:
            return set(self.format_synset_id(hypernym) for hypernym in hypernyms)
        else:
            return set([synset_id])

    def semantic_file(self, synset_id):
        return set([self._synset(synset_id).lexname])

def fix_pos(pos):
    return pos.replace('s', 'a')


def format_synset_id(synset):
    return "%08i-%s" % (synset.offset, fix_pos(synset.pos))


if __name__ == '__main__':
    loader = Wn30Loader(Wn30(), 'wordnets/wn30_food')
    wn = loader.load()