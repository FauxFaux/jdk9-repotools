#!/usr/bin/env python3
import collections
import datetime
import subprocess

import dateutil.parser
import os
from typing import Dict, Iterator, List

RawLog = collections.namedtuple('RawLog', ['commit', 'tree', 'date'])
TreeInfo = collections.namedtuple('TreeInfo', ['mode', 'object_type', 'sha'])


def commits(path: str) -> Iterator[RawLog]:
    git_dir = path + '/.git'
    if not os.path.isdir(git_dir) or not os.listdir(git_dir + '/refs/heads'):
        return

    for log_line in subprocess.check_output(
            ['/usr/bin/git', '--git-dir=' + git_dir, 'log', '--first-parent', '--format=%H %T %cd', '--date=iso']
    ).split(b'\n'):
        if not log_line:
            break
        parts = log_line.decode('utf-8').split(' ', 2)
        when = dateutil.parser.parse(parts[2])  # type: datetime.datetime
        yield RawLog(parts[0], parts[1], when)


class Repo:
    def __init__(self, path: str):
        self.path = path
        self.commits = list(commits(path))
        self.sub = {}  # type: Dict[str, List[RawLog]]
        try:
            submodules = set(os.listdir(path + '/.git/modules'))
        except IOError:
            return
        for mod in submodules:
            self.sub[mod] = Repo('{}/{}'.format(path, mod))

    def read_tree(self, tree: str) -> Dict[str, TreeInfo]:
        the_tree = {}  # type: Dict[str, TreeInfo]
        for tree_line in subprocess.check_output(
                ['git', '--git-dir={}/.git'.format(self.path), 'ls-tree', '-z', tree]
        ).split(b'\0'):
            if not tree_line:
                break

            (mode, object_type, sha_name) = tree_line.decode('utf-8').split(' ', 2)
            (sha, name) = sha_name.split('\t', 1)
            the_tree[name] = TreeInfo(mode, object_type, sha)

        return the_tree

    def set_alternates(self, src: 'Repo') -> None:
        with open(self.path + '/.git/objects/info/alternates', 'w') as f:
            f.write('../../../{}/.git/objects\n'.format(src.path))
            for sub in src.sub.keys():
                f.write('../../../{}/.git/modules/{}/objects\n'.format(src.path, sub))


def write_tree(tree: Dict[str, TreeInfo]) -> str:
    ret = ''
    for name, info in tree.items():
        ret += '{} {} {}\t{}\0'.format(info.mode, info.object_type, info.sha, name)

    return subprocess.check_output(['git', 'mktree', '-z'], stdin=ret).decode('utf-8').strip()


def main():
    new = Repo('flattened')
    orig = Repo('jdk9')

    new.set_alternates(orig)
    initial = orig.commits.pop()
    print(orig.read_tree(initial.tree))


if '__main__' == __name__:
    main()
