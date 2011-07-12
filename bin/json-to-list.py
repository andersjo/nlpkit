#!/usr/bin/env python
from json import JSONDecoder
import argparse
import re


parser = argparse.ArgumentParser(description='convert a stream of JSON objects to a list')
parser.add_argument('file', type=argparse.FileType('r'))
args = parser.parse_args()

def json_objects(input):
    decoder = JSONDecoder()
    next_obj_pat = re.compile("\S")

    idx = 0
    while True:
        obj, stop = decoder.raw_decode(contents[idx:])
        yield (obj, idx, idx+stop)
        m = next_obj_pat.search(contents, idx + stop)
        if m:
            idx = m.start()
        else:
            break



contents = args.file.read()
chunks = [contents[start:stop]
          for obj, start, stop in json_objects(contents)]
print "[{}]".format(",\n".join(chunks))
