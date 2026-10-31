#!/usr/bin/env python3
"""Publish the player client: puts the current client files on the project's `client-dist` branch,
with manifest.txt, so players' Launcher.exe downloads what changed.

    publish_client.py <client folder> <project repo> [version text]

- Files kept up to date: merc.exe, Launcher.exe, pnglib.dat/.idx, README.txt, GFX/*, sfx/*.
- gx00.dat/.idx (96 MB, the original graphics; they never change) are listed as "base": the launcher
  only checks they exist; players get them once from the zip.
- Never published: merc.dat (your character logins), client.ini, client.log, *.moa, backups.
- The branch is written with git plumbing from a temporary folder, so your working copy and the
  branch you're on are not touched. Afterwards: `git push origin client-dist`.
"""
import hashlib, os, shutil, subprocess, sys, tempfile, time

KEEP_TOP = ['merc.exe', 'Launcher.exe', 'pnglib.dat', 'pnglib.idx']
KEEP_DIRS = ['GFX', 'sfx']
BASE = ['gx00.dat', 'gx00.idx']
NEVER = {'merc.dat', 'merc2.dat', 'client.ini', 'client.log', 'launcher.log'}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def git(repo, *a, env=None, inp=None):
    return subprocess.run(['git', '-C', repo] + list(a), check=True, capture_output=True, text=True,
                          env=env, input=inp).stdout.strip()


def main():
    client, repo = sys.argv[1], sys.argv[2]
    version = sys.argv[3] if len(sys.argv) > 3 else time.strftime('%Y-%m-%d %H:%M')
    readme = os.path.join(repo, 'client', 'package', 'README.txt')
    stage = tempfile.mkdtemp(prefix='client-dist-')
    files = []
    for n in KEEP_TOP:
        p = os.path.join(client, n)
        if not os.path.isfile(p):
            sys.exit('missing in the client folder: ' + n)
        files.append((n, p))
    if os.path.isfile(readme):
        files.append(('README.txt', readme))
    for d in KEEP_DIRS:
        for root, _, names in os.walk(os.path.join(client, d)):
            for n in sorted(names):
                p = os.path.join(root, n)
                rel = os.path.relpath(p, client).replace(os.sep, '/')
                if n in NEVER or n.lower().endswith(('.moa', '.part', '.tmp')):
                    continue
                files.append((rel, p))
    lines = ['# MyV2 Astonia client files, made by tools/release/publish_client.py', 'version ' + version]
    for rel, p in sorted(files, key=lambda x: x[0].lower()):
        dst = os.path.join(stage, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(p, dst)
        lines.append('file %s %d %s' % (sha(dst), os.path.getsize(dst), rel))
    for n in BASE:
        p = os.path.join(client, n)
        if os.path.isfile(p):
            lines.append('base %d %s' % (os.path.getsize(p), n))
    open(os.path.join(stage, 'manifest.txt'), 'w', newline='\n').write('\n'.join(lines) + '\n')

    idx = tempfile.mktemp(prefix='client-dist-index-')
    env = dict(os.environ, GIT_INDEX_FILE=idx)
    git(repo, '--work-tree=' + stage, 'add', '-A', '.', env=env)
    tree = git(repo, 'write-tree', env=env)
    try:
        parent = git(repo, 'rev-parse', '-q', '--verify', 'refs/heads/client-dist')
    except subprocess.CalledProcessError:
        parent = ''
    if parent and git(repo, 'rev-parse', parent + '^{tree}') == tree:
        print('Nothing changed since the last publish (%s).' % parent[:7])
    else:
        args = ['commit-tree', tree, '-m', 'Client files ' + version] + (['-p', parent] if parent else [])
        commit = git(repo, *args)
        git(repo, 'update-ref', 'refs/heads/client-dist', commit)
        print('client-dist is now %s: %d files, version %s' % (commit[:7], len(files), version))
        print('Next: git push origin client-dist')
    shutil.rmtree(stage, ignore_errors=True)
    try:
        os.remove(idx)
    except OSError:
        pass


if __name__ == '__main__':
    main()
