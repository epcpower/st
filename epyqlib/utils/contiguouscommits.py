import argparse
import itertools
import json
import logging
import sys

import dulwich.repo


def build_relatives(repo):
    children = {}
    parents = {}

    heads = {n: s for n, s in repo.get_refs().items()
             if n.startswith(b'refs/heads/')}

    for entry in repo.get_walker(include=list(heads.values())):
        for p in entry.commit.parents:
            parents.setdefault(entry.commit.id, set()).add(p)
            children.setdefault(p, set()).add(entry.commit.id)

    return children, parents


# def traverse(self, call_this, payload=None):
#     child = None
#     for child in self.children:
#         child.traverse(call_this, payload)
#
#     if child is None:
#         call_this(self, payload)


def interface_rev(repo, commit):
    tree = repo[commit.tree]
    _, swrevs_sha = tree.lookup_path(
        lambda sha: repo[sha], b'interface/swRevs.h')
    swrevs = repo[swrevs_sha]

    for line in swrevs.data.decode().splitlines():
        if line.startswith('#define INTERFACE_SW_REV '):
            return int(line.split('#define INTERFACE_SW_REV ')[1])

    return None


def matches_rev(target_rev, repo, commit):
    return target_rev == interface_rev(repo, commit)


def history(repo, base_commit, mappings, test, visited=None):
    if visited is None:
        visited = set()

    revisions = {base_commit}

    relatives = (mapping[base_commit.id] for mapping in mappings)
    relatives = itertools.chain(*relatives)

    for commit in relatives:
        if commit in visited:
            continue
        visited.add(commit)

        commit = repo[commit]
        if test(commit):
            revisions |= history(
                repo=repo,
                base_commit=commit,
                mappings=mappings,
                test=test,
                visited=visited
            )

    return revisions


def contiguous_commits(repo, base_commit, test):
    children, parents = build_relatives(repo=repo)

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

    encoded_sha = args.sha.encode()

    repo = dulwich.repo.Repo(args.repository)

    relatives = itertools.chain(*build_relatives(repo=repo))
    found = {relative for relative in relatives
             if relative.startswith(encoded_sha)}

    if len(found) == 0:
        raise Exception('No matches found for sha {}'.format(args.sha))
    elif len(found) > 1:
        raise Exception('Multiple matches found for sha {}:\n\n{}'.format(args.sha, ''.join('\n\t'+s for s in (sha.decode() for sha in sorted(found)))))

    [sha] = found

    base_commit = repo[sha]
    target_rev = interface_rev(repo, base_commit)
    cc = contiguous_commits(
        repo=repo,
        base_commit=base_commit,
        test=lambda commit: matches_rev(target_rev=target_rev, repo=repo, commit=commit)
    )

    h = sorted(cc, key=lambda c: c.commit_time, reverse=True)
    h = (c.id.decode() for c in h)

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
