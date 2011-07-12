#!/usr/bin/env python
from json import JSONDecoder, dumps
import argparse
import re
import operator


parser = argparse.ArgumentParser(description='convert a stream of JSON objects to a list')
parser.add_argument('files', nargs='+', type=argparse.FileType('r'))
args = parser.parse_args()

decoder = JSONDecoder()
obj_lists = [decoder.decode(file.read()) for file in args.files]
new_list = reduce(operator.add, obj_lists, [])
print dumps(new_list)
