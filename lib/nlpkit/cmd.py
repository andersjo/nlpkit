import argparse
import atexit
import json
import os
import sys
import pymongo
from nlpkit import new_id

class CmdRun(object):
    def __init__(self, args):
        self.id = new_id()
        self.args = args
        atexit.register(self.save_stats)

    def save_stats(self):
        conn = pymongo.Connection()
        db = conn.nlpkit
        db.cmd_runs.insert(self.stringify(self.stats()))

    def stats(self):
        times = os.times()
        return {
            '_id': pymongo.objectid.ObjectId(self.id),
            'utime': times[0],
            'stime': times[1],
            'cutime': times[2],
            'cstime': times[3],
            'elapsed_time': times[4],
            'args': vars(self.args),
            'env': dict(os.environ),
            'pid': os.getpid(),
            'argv': " ".join(sys.argv)
        }

    def stringify(self, obj):
        if isinstance(obj, dict):
            return dict((k, self.stringify(v)) for k,v in obj.items())
        elif isinstance(obj, list):
            return [self.stringify(v) for v in obj]
        elif isinstance(obj, (float, int, pymongo.objectid.ObjectId)):
            return obj
        else:
            return str(obj)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='the punch utility')
    parser.add_argument('where', choices=('face', 'stomach'))
    parser.add_argument('--insult', action='store_true', help='add insult to injury')
    args = parser.parse_args(args=['--insult', 'face'])
    CmdRun(args)
    sys.exit(3)

