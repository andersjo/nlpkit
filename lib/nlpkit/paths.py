# coding: utf-8
from os.path import expanduser, exists, abspath
import os.path
import os
from os import environ, access

def data_path(relative_path):
    """
    Return an absolute path of the file or directory given by the relative path.

    Relative paths are checked against the list of data path roots given by data_dir().
    The first path that exists and can be read is returned. If no such path exists,
    the return value is None.
    """
    for dir in data_dirs():
        path = os.path.join(dir, relative_path)
        if exists(path) and access(path, os.R_OK):
            return abspath(path)
    raise IOError()

def save_data_path(relative_path, create_dir=False):
    data_dir = data_dirs[0]
    path = data_dir + '/' + relative_path

    return path

def data_dirs():
    """
    Return a list of absolute path names used as the data file search path.

    By convention, a path is considered a data path if it exists, is readable, and one or more
    of the conditions below apply:
        1) the path is listed in the colon separated environment variable NLPKIT_DATA
           (same format as PATH)
        2) the path's final component is a directory named 'data' and located somewhere along the path from the
           current working directory to the filesystem root.
           If the working directory is '/opt/local/myscript.py', the paths '/opt/local/data', '/opt/data', and '/data'
            will be considered.
        3) the path is called 'data' and located in the current user's home directory.
    """
    candidates = []
    if 'NLPKIT_DATA' in environ:
        for path in environ['NLPKIT_DATA'].split(":"):
            candidates.append(path)

    def add_below(cur_path):
        head, tail = os.path.split(cur_path)
        candidates.append(os.path.join(head, 'data'))
        if len(head) > 1:
            add_below(head)
    add_below(os.getcwd())

    absolute_paths = (abspath(expanduser(cand)) for cand in candidates)
    return filter(lambda f: exists(f) and access(f, os.R_OK), absolute_paths)

