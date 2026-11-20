"""Incremental client-dist publish: the last client-dist tree + the client files that are new or changed in size since
(new sprites), with manifest.txt updated the same way publish_client.py writes it, and the player zip updated the same way."""
import os, sys, subprocess, hashlib, tempfile, shutil
client, repo, version = sys.argv[1], sys.argv[2], sys.argv[3]
def git(*a, env=None, inp=None):
    return subprocess.run(['git', '-C', repo] + list(a), check=True, capture_output=True, text=True, env=env, input=inp).stdout.strip()
man = git('show', 'client-dist:manifest.txt').split('\n')
old = {}
for l in man:
    if l.startswith('file '):
        _, h, sz, rel = l.split(' ', 3); old[rel] = (h, int(sz))
NEVER = {'merc.dat', 'merc2.dat', 'client.ini', 'client.log', 'launcher.log'}
changed = []
for top in ['merc.exe', 'Launcher.exe', 'pnglib.dat', 'pnglib.idx']:
    p = os.path.join(client, top)
    if top not in old or os.path.getsize(p) != old[top][1]: changed.append((top, p))
for d in ('GFX', 'sfx'):
    for root, _, names in os.walk(os.path.join(client, d)):
        for n in names:
            if n in NEVER or n.lower().endswith(('.moa', '.part', '.tmp')): continue
            p = os.path.join(root, n); rel = os.path.relpath(p, client).replace(os.sep, '/')
            if rel not in old or os.path.getsize(p) != old[rel][1]: changed.append((rel, p))
print('new or changed:', len(changed))
idx = tempfile.mktemp(prefix='cd-index-'); env = dict(os.environ, GIT_INDEX_FILE=idx)
git('read-tree', 'client-dist', env=env)
info = []
for rel, p in changed:                                    # sha256 for the manifest
    data = open(p, 'rb').read(); old[rel] = (hashlib.sha256(data).hexdigest(), len(data))
# all the files stored in ONE git call (one call per file ran past the device shell's 3 minutes, Nov 19)
blobs = subprocess.run(['git', '-C', repo, 'hash-object', '-w', '--stdin-paths'], input='\n'.join(os.path.abspath(p) for _, p in changed) + '\n',
                       capture_output=True, check=True, text=True).stdout.split()
assert len(blobs) == len(changed)
for (rel, _), blob in zip(changed, blobs): info.append('100644 %s\t%s' % (blob, rel))
lines = [l for l in man if l and not l.startswith(('file ', 'base ', 'version '))]
lines.append('version ' + version)
for rel in sorted(old, key=lambda r: r.lower()): lines.append('file %s %d %s' % (old[rel][0], old[rel][1], rel))
lines += [l for l in man if l.startswith('base ')]
mblob = git('hash-object', '-w', '--stdin', inp='\n'.join(lines) + '\n')
info.append('100644 %s\tmanifest.txt' % mblob)
git('update-index', '--add', '--index-info', env=env, inp='\n'.join(info) + '\n')
tree = git('write-tree', env=env); parent = git('rev-parse', 'refs/heads/client-dist')
commit = git('commit-tree', tree, '-p', parent, '-m', 'Client files ' + version)
git('update-ref', 'refs/heads/client-dist', commit, parent)
os.remove(idx)
print('client-dist is now %s (+%d files), version %s' % (commit[:7], len(changed), version))

# the player download too (Nov 19, Cody: "why can you not update the zip?"): the zip in <Client>/For Players is the one
# made for the publish before this one, so it is copied here, every file this publish changed goes in (the rest is kept
# as it is), and the new zip replaces the old in one step. Its files are checked against this publish's manifest.
import zipfile, tempfile as _tf
ZIP = os.path.join(client, 'For Players', 'Mercenaries-of-Asgard-v2.zip'); G = 'Mercenaries of Asgard v2/'
if os.path.exists(ZIP):
    tmp = _tf.mkdtemp(prefix='zip-'); oldz = os.path.join(tmp, 'old.zip'); newz = os.path.join(tmp, 'new.zip')
    shutil.copyfile(ZIP, oldz); todo = set(G + r for r, _ in changed)
    with zipfile.ZipFile(oldz) as o, zipfile.ZipFile(newz, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for i in o.infolist():
            if i.filename in todo: continue
            z.writestr(i, b'' if i.is_dir() else o.read(i.filename), compress_type=i.compress_type)
        for rel, p in changed: z.write(p, G + rel)
    with zipfile.ZipFile(newz) as z:
        names = set(z.namelist()); miss = [r for r in old if G + r not in names]
    assert not miss and zipfile.ZipFile(newz).testzip() is None, ('zip check failed', miss[:5])
    shutil.copyfile(newz, ZIP + '.part'); os.replace(ZIP + '.part', ZIP); shutil.rmtree(tmp, ignore_errors=True)
    print('Player download updated: %s (%.1f MB)' % (ZIP, os.path.getsize(ZIP) / 1e6))
