#!/usr/bin/env python3
"""Wall decorations for the other wall (Nov 16, Cody: "sprites that are only south facing should also have a west facing").
The game's wall pictures, mirrors, bookshelves and chained skeletons hang only on walls running along x (the wall to the
south of the item's tile, the face seen down-left). Mirrored left-right, the same picture hangs on walls running along y
(the wall to the west of the tile, the face seen down-right): sorted and drawn like the game does (render check:
Client\\Claude outputs\\decor\\). The other two sides (walls to the north / east) face away from the camera and are hidden
behind the wall itself, so they need no pictures. The shields already come in both (746/747, 748/749).
New numbers from 48000 (this range is kept for Claude's sprite work while other sessions build the world).
    mirror_decor.py <client folder>      -> <client>/GFX/48000.png ... and mirror_decor.json (new sprite -> game sprite)"""
import json, os, sys
from PIL import Image, ImageOps
HERE = os.path.dirname(os.path.abspath(__file__))
DECOR = [(572, 'Picture of Misty Plains'), (580, 'Picture of Sunset'), (1246, 'Mirror (framed)'),
         (16552, 'Mirror (round)'), (16553, 'Mirror (round) II'),
         (16897, 'Bookshelf 1'), (16898, 'Bookshelf 2'), (16908, 'Bookshelf 3'), (16909, 'Bookshelf 4'), (16910, 'Bookshelf 5 (book of wisdom)'),
         (16911, 'Bookshelf 5, the book taken'),
         (620, 'Skeleton in Chains'), (622, 'Skeleton in Chains II'), (624, 'Skeleton in Chains III'), (626, 'Skeleton in Chains IV')]
FIRST = 48000


def main():
    client = sys.argv[1]
    sys.argv = [sys.argv[0], client, '/tmp']
    exec(open(os.path.join(HERE, '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
    out = {}
    for i, (s, name) in enumerate(DECOR):
        im = load(s).convert('RGBA')
        ImageOps.mirror(im).save(os.path.join(client, 'GFX', '%05d.png' % (FIRST + i)))
        out[FIRST + i] = {'from': s, 'name': name + ' (west wall)'}
    json.dump(out, open(os.path.join(HERE, 'mirror_decor.json'), 'w'), indent=1)
    print(len(out), 'sprites', FIRST, '-', FIRST + len(out) - 1)


if __name__ == '__main__':
    main()
