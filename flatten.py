#!/usr/bin/env python3
import collections
import datetime
import subprocess

import dateutil.parser
import os
from typing import Dict, Iterator, List, TypeVar, Tuple, Optional

T = TypeVar('T')

RawLog = collections.namedtuple('RawLog', ['commit', 'tree', 'date'])
TreeInfo = collections.namedtuple('TreeInfo', ['mode', 'object_type', 'sha'])


def commits(path: str) -> Iterator[RawLog]:
    git_dir = path + '/.git'
    if os.path.isdir(git_dir) and not os.listdir(git_dir + '/refs/heads'):
        return

    for log_line in subprocess.check_output(
            ['/usr/bin/git', '--git-dir=' + git_dir, 'log', '--first-parent', '--format=%H %T %cd', '--date=iso']
    ).split(b'\n'):
        if not log_line:
            break
        parts = log_line.decode('utf-8').split(' ', 2)
        when = dateutil.parser.parse(parts[2])  # type: datetime.datetime
        yield RawLog(parts[0], parts[1], when)


def last(of: List[T]) -> T:
    return of[len(of) - 1]


class Repo:
    def __init__(self, path: str):
        self.path = path
        self.commits = list(commits(path))
        self.sub = {}  # type: Dict[str, Repo]
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

    def earliest_commit(self) -> Tuple[Optional[str], Optional[RawLog]]:
        commit = None
        if self.commits:
            commit = last(self.commits)
        src = None
        for name, repo in sorted(self.sub.items()):
            if not repo.commits:
                continue

            candidate = last(repo.commits)
            if not commit or candidate.date < commit.date:
                commit = candidate
                src = name

        if not commit:
            return None, None

        if src:
            self.sub[src].commits.pop()
        else:
            self.commits.pop()

        return src, commit

    def write_tree(self, tree: Dict[str, TreeInfo]) -> str:
        ret = ''
        for name, info in tree.items():
            ret += '{} {} {}\t{}\0'.format(info.mode, info.object_type, info.sha, name)

        return subprocess.check_output(
            ['git', '--git-dir=' + self.path + '/.git', 'mktree', '-z'],
            input=ret.encode('utf-8')).decode('utf-8').strip()

    def load_commit(self, sha: str) -> List[str]:
        return subprocess.check_output(
            ['git', '--git-dir=' + self.path + '/.git', 'cat-file', 'commit', sha]
        ).decode('utf-8').split('\n')

    def commit_tree(self, tree: str, ref: str, parents: Iterator[str]) -> str:
        new_lines = ['tree ' + tree]
        for parent in parents:
            new_lines.append('parent ' + parent)

        original_lines = self.load_commit(ref)
        original_lines.pop(0)  # tree
        if original_lines[0].startswith('parent '):
            original_lines.pop(0)

        new_lines.extend(original_lines)

        return subprocess.check_output(
            ['git', '--git-dir=' + self.path + '/.git', 'hash-object', '-w', '--stdin', '-t', 'commit'],
            input='\n'.join(new_lines).encode('utf-8')
        ).decode('utf-8').strip()

    def update_ref(self, ref: str, to: str):
        subprocess.check_call(
            ['git', '--git-dir=' + self.path + '/.git', 'update-ref', ref, to]
        )


def main():
    new = Repo('flattened')
    orig = Repo('jdk9')

    new.set_alternates(orig)
    overlay = {}  # type: Dict[str, TreeInfo]
    tree = {}
    head = None
    while True:
        src, found_commit = orig.earliest_commit()
        if not found_commit:
            break

        if src:
            # update to a child repo
            overlay[src] = TreeInfo('040000', 'tree', found_commit.tree)
        else:
            # update to the root
            tree = orig.read_tree(found_commit.tree)

        tree.update(overlay)

        head = new.commit_tree(new.write_tree(tree), found_commit.commit, [head] if head else [])

    new.update_ref('refs/heads/master', head)


if '__main__' == __name__:
    main()
