import argparse
import itertools
import json
import logging
import sys

import dulwich.repo
import git


def build_relatives(repo_path=None):
    if repo_path is None:
        repo_path = '.'

    repo = dulwich.repo.Repo(repo_path)

    children = {}
    parents = {}

    heads = {n: s for n, s in repo.get_refs().items() if n.startswith(b'refs/heads/')}

    for entry in repo.get_walker(include=list(heads.values())):
        for p in entry.commit.parents:
            parents.setdefault(entry.commit.id.decode(), set()).add(p.decode())
            children.setdefault(p.decode(), set()).add(entry.commit.id.decode())

    return children, parents


# def traverse(self, call_this, payload=None):
#     child = None
#     for child in self.children:
#         child.traverse(call_this, payload)
#
#     if child is None:
#         call_this(self, payload)


def interface_rev(commit):
    a = commit.tree['interface/swRevs.h']

    for line in a.data_stream.read().decode().splitlines():
        if line.startswith('#define INTERFACE_SW_REV '):
            return int(line.split('#define INTERFACE_SW_REV ')[1])

    return None


def matches_rev(target_rev, commit):
    return target_rev == interface_rev(commit)


def history(repo, base_commit, mappings, test, visited=None):
    if visited is None:
        visited = set()

    revisions = {base_commit}

    relatives = (mapping[base_commit.hexsha] for mapping in mappings)
    relatives = itertools.chain(*relatives)

    for commit in relatives:
        if commit in visited:
            continue
        visited.add(commit)

        commit = repo.commit(commit)
        if test(commit):
            revisions |= history(
                repo=repo,
                base_commit=commit,
                mappings=mappings,
                test=test,
                visited=visited
            )

    return revisions


def contiguous_commits(repo, base_commit, test, repo_path='.'):
    children, parents = build_relatives(repo_path=repo_path)

    return history(
        repo=repo,
        base_commit=base_commit,
        mappings=(parents, children),
        test=test
    )


def parse_args(args):
    parser = argparse.ArgumentParser()
    # parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--sha', '-s', required=True)
    parser.add_argument('--repository', '--repo', '-r', default='.')
    parser.add_argument('--json', '-j', action='store_true')

    return parser.parse_args(args)


def main(*args, logger):
    args = parse_args(args=args)

    repo = git.Repo(args.repository)

    base_commit = repo.commit(args.sha)
    target_rev = interface_rev(base_commit)
    cc = contiguous_commits(
        repo=repo,
        base_commit=base_commit,
        test=lambda commit: matches_rev(target_rev=target_rev, commit=commit),
        repo_path=args.repository
    )

    h = sorted(cc, key=lambda c: c.committed_date, reverse=True)
    h = (c.hexsha for c in h)

    if args.json:
        print(json.dumps(list(h), indent=4))
    else:
        print('\n'.join(h))


def _entry_point():
    import traceback

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('contiguouscommits.log')

    for handler in (stream_handler, file_handler):
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

    return main(*sys.argv[1:], logger=logger)
