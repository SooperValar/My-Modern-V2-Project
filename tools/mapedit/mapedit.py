#!/usr/bin/env python3
"""MyV2 Editor - the Mercenaries of Astonia v2 map editor, in the browser.

Run it in the server's folder (where .dat/ and ./server are), then open
http://localhost:8080 in your browser:

    python3 mapedit.py
    python3 mapedit.py --client /mnt/c/Users/Cody/Desktop/MyV2/Client --port 8080

Editing works only while the game server is stopped; while it runs the map
can be looked at but not changed. Changes are kept in memory until Save, which
first copies map.dat and item.dat into .dat/mapedit-backups/<date-time>/.
Only the Python standard library is needed.

Files read: .dat/map.dat, item.dat, titem.dat, char.dat (written: map.dat,
item.dat), area.c (zone names), the client's GFX/, pnglib.dat/.idx and
gx00.dat/.idx (sprites), and optionally a minimap picture (world_minimap.png).
"""
import argparse, glob, io, json, mmap, os, re, shutil, struct, subprocess, sys, threading, time, zlib, random
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------- data layout
# (offsets from the server's data.h; checked against the file sizes at start)
MAPX = MAPY = 1024
MAXITEM, MAXCHARS, MAXTITEM = 98304, 8192, 4548
MAP_SIZE, ITEM_SIZE, CHAR_SIZE = 28, 634, 3605
USE_EMPTY, USE_ACTIVE = 0, 1
# map: sprite H, fsprite H, ch I, to_ch I, it I, dlight H, light h, flags Q
MAP_FMT = '<HHIIIHhQ'
# item
I_USED, I_NAME, I_DESC, I_FLAGS, I_TEMP, I_SPRITE, I_X, I_Y, I_CARRIED, I_DRIVER, I_DATA, I_ACTIVE, I_LIGHT = \
    0, 1, 81, 281, 295, 537, 529, 531, 533, 593, 594, 525, 509
I_PLACEMENT = 293
# character
C_USED, C_NAME, C_FLAGS, C_SPRITE, C_TEMP, C_X, C_Y, C_DIR = 0, 1, 301, 297, 319, 717, 719, 733

MF = ['move block', 'sight block', 'indoors', 'under water', 'no lag', 'no monsters', 'bank', 'tavern',
      'no magic', 'death trap', 'no light', 'arena', 'lit', 'no expire', 'no fight']
MF_MOVEBLOCK, MF_SIGHTBLOCK = 1, 2
CF_PLAYER, CF_BODY = 1 << 5, 1 << 17
IF_MOVEBLOCK, IF_SIGHTBLOCK, IF_TAKE, IF_LOOK, IF_LOOKSPECIAL, IF_USE, IF_USESPECIAL = 1, 2, 4, 16, 32, 512, 1024

# build mode's random floors: picking one of these paints a random one of its set (same as the game)
FLOOR_SETS = {1003: [1003, 1005, 1006, 1007], 542: list(range(542, 551)), 551: list(range(551, 555)),
              133: list(range(133, 142)), 142: [142, 143, 144, 145], 170: list(range(170, 176)),
              704: [704, 659, 660, 688], 950: list(range(950, 959)), 16670: list(range(16670, 16674)),
              16933: [16933, 16957, 16958, 16959]}


def cstr(b):
    return b.split(b'\0', 1)[0].decode('latin-1')


# ---------------------------------------------------------------- world
class World:
    def __init__(self, dat, server_dir, area_file):
        self.dat, self.server_dir, self.area_file = dat, server_dir, area_file
        self.lock = threading.RLock()
        self.load()

    def load(self):
        with self.lock:
            p = lambda n: os.path.join(self.dat, n)
            self.map = bytearray(open(p('map.dat'), 'rb').read())
            self.item = bytearray(open(p('item.dat'), 'rb').read())
            self.titem = open(p('titem.dat'), 'rb').read()
            self.char = open(p('char.dat'), 'rb').read()
            if len(self.map) < MAPX * MAPY * MAP_SIZE or len(self.item) < MAXITEM * ITEM_SIZE \
                    or len(self.titem) < MAXTITEM * ITEM_SIZE:
                sys.exit('The .dat files are smaller than this editor expects - wrong folder or another server version.')
            self.mtimes = {n: os.path.getmtime(p(n)) for n in ('map.dat', 'item.dat')}
            self.undo, self.redo, self.dirty = [], [], 0
            self.free_hint = 1
            self.areas = self.read_areas()
            self.gen = getattr(self, 'gen', 0) + 1      # the browser fetches everything again when this changes
            self.loaded = time.time()
            if not hasattr(self, 'history'):
                self.history = []

    def refresh_live(self):
        """while the game runs (view only), read its files again now and then so NPCs and changes show"""
        with self.lock:
            if self.dirty or time.time() - self.loaded < 8:
                return
            p = lambda n: os.path.join(self.dat, n)
            try:
                self.map = bytearray(open(p('map.dat'), 'rb').read())
                self.item = bytearray(open(p('item.dat'), 'rb').read())
                self.char = open(p('char.dat'), 'rb').read()
            except OSError:
                return
            self.mtimes = {n: os.path.getmtime(p(n)) for n in ('map.dat', 'item.dat')}
            self.undo, self.redo = [], []
            self.gen += 1
            self.loaded = time.time()

    def online(self):
        n = 0
        for c in range(1, MAXCHARS):
            o = c * CHAR_SIZE
            if self.char[o + C_USED] == USE_ACTIVE and struct.unpack_from('<Q', self.char, o + C_FLAGS)[0] & CF_PLAYER:
                n += 1
        return n

    def chars(self):
        """every NPC and player standing somewhere in the world"""
        out = []
        for c in range(1, MAXCHARS):
            o = c * CHAR_SIZE
            if not self.char[o + C_USED]:
                continue
            fl = struct.unpack_from('<Q', self.char, o + C_FLAGS)[0]
            if fl & CF_BODY:
                continue
            x, y = struct.unpack_from('<HH', self.char, o + C_X)
            if not x and not y:
                continue
            out.append([c, cstr(self.char[o + C_NAME:o + C_NAME + 40]), x, y,
                        struct.unpack_from('<H', self.char, o + C_TEMP)[0], 1 if fl & CF_PLAYER else 0,
                        self.char_sprite(c), 1 if self.char[o + C_USED] == USE_ACTIVE else 0])
        return out

    def search(self, q):
        q = q.strip().lower()
        out = []
        if not q:
            return out
        m = re.match(r'^(\d+)[ ,]+(\d+)$', q)
        if m:
            out.append({'type': 'place', 'name': 'Position %s, %s' % m.groups(), 'x': int(m.group(1)), 'y': int(m.group(2))})
        seen = set()
        for a, b, c, d, n in self.areas:
            if q in n.lower() and n not in seen:
                seen.add(n)
                out.append({'type': 'place', 'name': n, 'x': (a + c) // 2, 'y': (b + d) // 2})
        for c in self.chars():
            if q in c[1].lower():
                out.append({'type': 'player' if c[5] else 'npc', 'name': c[1], 'x': c[2], 'y': c[3], 'temp': c[4],
                            'sprite': c[6], 'online': c[7]})
                if len(out) > 60:
                    break
        for t in range(1, MAXTITEM):
            o = t * ITEM_SIZE
            if not self.titem[o + I_USED]:
                continue
            name = cstr(self.titem[o + I_NAME:o + I_NAME + 40])
            if q in name.lower() or q == str(t):
                out.append({'type': 'item', 'name': name, 't': t, 'sprite': self.ti_u16(t, I_SPRITE)})
                if len(out) > 100:
                    break
        return out[:100]

    def read_areas(self):
        try:
            src = open(self.area_file, encoding='latin-1').read()
        except OSError:
            return []
        out = []
        for a, b, c, d, n in re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*"([^"]+)"', src):
            out.append((int(a), int(b), int(c), int(d), n))
        return out

    def zone(self, x, y):
        return ', '.join(n for a, b, c, d, n in self.areas if a <= x <= c and b <= y <= d)

    # --- raw access
    def tile(self, x, y):
        return list(struct.unpack_from(MAP_FMT, self.map, (x + y * MAPX) * MAP_SIZE))

    def set_tile(self, x, y, t):
        struct.pack_into(MAP_FMT, self.map, (x + y * MAPX) * MAP_SIZE, *t)

    def it_u8(self, i, off): return self.item[i * ITEM_SIZE + off]
    def it_u16(self, i, off): return struct.unpack_from('<H', self.item, i * ITEM_SIZE + off)[0]
    def it_u64(self, i, off): return struct.unpack_from('<Q', self.item, i * ITEM_SIZE + off)[0]
    def ti_u16(self, t, off): return struct.unpack_from('<H', self.titem, t * ITEM_SIZE + off)[0]
    def ti_u64(self, t, off): return struct.unpack_from('<Q', self.titem, t * ITEM_SIZE + off)[0]

    def item_sprite(self, i):
        o = i * ITEM_SIZE
        s0, s1 = struct.unpack_from('<hh', self.item, o + I_SPRITE)
        active = struct.unpack_from('<i', self.item, o + I_ACTIVE)[0]
        return (s1 if active and s1 else s0) & 0xffff

    def char_sprite(self, c):
        o = c * CHAR_SIZE
        spr = struct.unpack_from('<H', self.char, o + C_SPRITE)[0]
        d = self.char[o + C_DIR]
        return spr + {3: 0, 4: 8, 2: 16, 1: 24, 5: 32, 6: 40, 7: 48, 8: 56}.get(d, 0) if spr else 0

    # --- reading for the browser
    def region(self, x0, y0, x1, y1):
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(MAPX - 1, x1), min(MAPY - 1, y1)
        g, f, fl, it, ch, li = [], [], [], [], [], []
        with self.lock:
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    s, fs, c, _, i, dl, lt, flags = struct.unpack_from(MAP_FMT, self.map, (x + y * MAPX) * MAP_SIZE)
                    g.append(s); f.append(fs); fl.append(flags & 0xffffffff); li.append(max(0, lt))
                    it.append(self.item_sprite(i) if 0 < i < MAXITEM and self.it_u8(i, I_USED) else 0)
                    ch.append(self.char_sprite(c) if 0 < c < MAXCHARS and self.char[c * CHAR_SIZE + C_USED] else 0)
        return {'x0': x0, 'y0': y0, 'w': x1 - x0 + 1, 'h': y1 - y0 + 1, 'g': g, 'f': f, 'fl': fl, 'it': it, 'ch': ch, 'li': li}

    def tile_info(self, x, y):
        with self.lock:
            s, fs, c, _, i, dl, li, flags = self.tile(x, y)
            r = {'x': x, 'y': y, 'zone': self.zone(x, y), 'floor': s, 'object': fs, 'light': li, 'dlight': dl,
                 'flags': [MF[b] for b in range(len(MF)) if flags >> b & 1]}
            if 0 < i < MAXITEM and self.it_u8(i, I_USED):
                o = i * ITEM_SIZE
                r['item'] = {'index': i, 'name': cstr(self.item[o + I_NAME:o + I_NAME + 40]), 'temp': self.it_u16(i, I_TEMP),
                             'sprite': self.item_sprite(i), 'driver': self.item[o + I_DRIVER],
                             'data': list(struct.unpack_from('<10i', self.item, o + I_DATA)),
                             'desc': cstr(self.item[o + I_DESC:o + I_DESC + 200])}
            if 0 < c < MAXCHARS and self.char[c * CHAR_SIZE + C_USED]:
                o = c * CHAR_SIZE
                r['char'] = {'index': c, 'name': cstr(self.char[o + C_NAME:o + C_NAME + 40]),
                             'temp': struct.unpack_from('<H', self.char, o + C_TEMP)[0]}
            return r

    def palette(self):
        with self.lock:
            floors, objs = {}, {}
            mv = memoryview(self.map)
            for k in range(MAPX * MAPY):
                s, fs = struct.unpack_from('<HH', mv, k * MAP_SIZE)
                floors[s] = floors.get(s, 0) + 1
                if fs:
                    objs[fs] = objs.get(fs, 0) + 1
            temps = []
            for t in range(1, MAXTITEM):
                o = t * ITEM_SIZE
                if not self.titem[o + I_USED]:
                    continue
                fl = self.ti_u64(t, I_FLAGS)
                # [number, name, sprite, can be picked up, driver, blocks (1 walking, 2 sight), becomes an item (else drawn into the tile)]
                temps.append([t, cstr(self.titem[o + I_NAME:o + I_NAME + 40]), self.ti_u16(t, I_SPRITE),
                              1 if fl & IF_TAKE else 0, self.titem[o + I_DRIVER],
                              (1 if fl & IF_MOVEBLOCK else 0) | (2 if fl & IF_SIGHTBLOCK else 0),
                              1 if fl & (IF_TAKE | IF_LOOK | IF_LOOKSPECIAL | IF_USE | IF_USESPECIAL) else 0])
        fl_sorted = sorted(floors.items(), key=lambda a: -a[1])
        ob_sorted = sorted(objs.items(), key=lambda a: -a[1])
        return {'floors': fl_sorted, 'objects': ob_sorted, 'templates': temps, 'flags': MF, 'sets': FLOOR_SETS}

    # --- editing: every change remembers the old bytes so a batch can be undone
    def _save_map(self, rec, x, y):
        k = ('m', x, y)
        if k not in rec:
            o = (x + y * MAPX) * MAP_SIZE
            rec[k] = bytes(self.map[o:o + MAP_SIZE])

    def _save_item(self, rec, i):
        k = ('i', i)
        if k not in rec:
            rec[k] = bytes(self.item[i * ITEM_SIZE:(i + 1) * ITEM_SIZE])

    def _free_item(self):
        for i in list(range(self.free_hint, MAXITEM)) + list(range(1, self.free_hint)):
            if not self.item[i * ITEM_SIZE + I_USED]:
                self.free_hint = i + 1
                return i
        return 0

    def _remove_item(self, rec, x, y):
        t = self.tile(x, y)
        i = t[4]
        if 0 < i < MAXITEM:
            self._save_item(rec, i)
            self.item[i * ITEM_SIZE + I_USED] = USE_EMPTY
        t[4] = 0
        self.set_tile(x, y, t)

    def apply(self, ops, label=''):
        """ops: list of dicts; returns (tiles changed, messages)"""
        rec, msgs, n = {}, [], 0
        with self.lock:
            for op in ops:
                x, y = int(op['x']), int(op['y'])
                if not (0 <= x < MAPX and 0 <= y < MAPY):
                    continue
                self._save_map(rec, x, y)
                t = self.tile(x, y)
                k = op['op']
                if k == 'floor':
                    s = int(op['s'])
                    t[0] = random.choice(FLOOR_SETS[s]) if s in FLOOR_SETS and op.get('set', True) else s
                    self.set_tile(x, y, t)
                elif k == 'object':           # a raw object sprite (eyedropper), with its blocking
                    t[1] = int(op['s'])
                    blk = int(op.get('block', 3))
                    t[7] = (t[7] & ~3) | (MF_MOVEBLOCK if blk & 1 else 0) | (MF_SIGHTBLOCK if blk & 2 else 0)
                    if not t[1]:
                        t[7] &= ~3
                    self.set_tile(x, y, t)
                elif k == 'place':            # a template, like build mode
                    tp = int(op['t'])
                    if not (0 < tp < MAXTITEM) or not self.titem[tp * ITEM_SIZE + I_USED]:
                        msgs.append('template %d does not exist' % tp); continue
                    fl = self.ti_u64(tp, I_FLAGS)
                    if fl & (IF_TAKE | IF_LOOK | IF_LOOKSPECIAL | IF_USE | IF_USESPECIAL):
                        if t[4] and 0 < t[4] < MAXITEM and self.it_u8(t[4], I_USED):
                            if not op.get('replace'):
                                msgs.append('%d,%d already has an item' % (x, y)); continue
                            self._remove_item(rec, x, y); t = self.tile(x, y)
                        if self.titem[tp * ITEM_SIZE + I_DRIVER] == 33:
                            msgs.append('pentagrams need build mode in game (they get numbered there)'); continue
                        i = self._free_item()
                        if not i:
                            msgs.append('no free item slot'); continue
                        self._save_item(rec, i)
                        o = i * ITEM_SIZE
                        self.item[o:o + ITEM_SIZE] = self.titem[tp * ITEM_SIZE:(tp + 1) * ITEM_SIZE]
                        self.item[o + I_USED] = USE_ACTIVE
                        struct.pack_into('<H', self.item, o + I_TEMP, tp)
                        struct.pack_into('<hhH', self.item, o + I_X, x, y, 0)
                        struct.pack_into('<i', self.item, o + I_ACTIVE, 0)
                        t[1] = 0          # an item replaces an object sprite (as in the game)
                        t[4] = i
                    else:                             # a plain piece: drawn into the tile
                        t[1] = self.ti_u16(tp, I_SPRITE)
                        t[7] = (t[7] & ~3) | (MF_MOVEBLOCK if fl & IF_MOVEBLOCK else 0) | (MF_SIGHTBLOCK if fl & IF_SIGHTBLOCK else 0)
                    self.set_tile(x, y, t)
                elif k == 'erase':            # like left-click in build mode: object and item go, floor stays
                    self._remove_item(rec, x, y)
                    t = self.tile(x, y)
                    t[1] = 0
                    t[7] &= ~3
                    self.set_tile(x, y, t)
                elif k == 'flag':
                    b = 1 << int(op['bit'])
                    m = int(op.get('mode', 2))
                    t[7] = (t[7] | b) if m == 1 else (t[7] & ~b) if m == 0 else (t[7] ^ b)
                    self.set_tile(x, y, t)
                n += 1
            # keep only real changes
            real = {}
            for key, old in rec.items():
                cur = bytes(self.map[(key[1] + key[2] * MAPX) * MAP_SIZE:(key[1] + key[2] * MAPX + 1) * MAP_SIZE]) if key[0] == 'm' \
                    else bytes(self.item[key[1] * ITEM_SIZE:(key[1] + 1) * ITEM_SIZE])
                if cur != old:
                    real[key] = old
            if real:
                self.undo.append(real)
                self.redo.clear()
                self.dirty += 1
                tiles = [k for k in real if k[0] == 'm']
                self.history.append({'t': time.strftime('%H:%M:%S'), 'what': label or 'edit', 'tiles': len(tiles),
                                     'x': tiles[0][1], 'y': tiles[0][2]})
            return len([k for k in real if k[0] == 'm']), msgs

    def _swap(self, rec):
        back = {}
        for key, old in rec.items():
            if key[0] == 'm':
                o = (key[1] + key[2] * MAPX) * MAP_SIZE
                back[key] = bytes(self.map[o:o + MAP_SIZE]); self.map[o:o + MAP_SIZE] = old
            else:
                o = key[1] * ITEM_SIZE
                back[key] = bytes(self.item[o:o + ITEM_SIZE]); self.item[o:o + ITEM_SIZE] = old
        return back

    def undo_redo(self, which):
        with self.lock:
            src, dst = (self.undo, self.redo) if which == 'undo' else (self.redo, self.undo)
            if not src:
                return []
            rec = src.pop()
            dst.append(self._swap(rec))
            self.dirty += 1
            tiles = [k for k in rec if k[0] == 'm']
            if tiles:
                self.history.append({'t': time.strftime('%H:%M:%S'), 'what': which, 'tiles': len(tiles), 'x': tiles[0][1], 'y': tiles[0][2]})
            return [[k[1], k[2]] for k in rec if k[0] == 'm']

    def save(self):
        with self.lock:
            p = lambda n: os.path.join(self.dat, n)
            for n in ('map.dat', 'item.dat'):
                if abs(os.path.getmtime(p(n)) - self.mtimes[n]) > 1:
                    return 'The world files changed on disk since they were loaded (the server ran?). Reload first - your unsaved changes would overwrite them.'
            bk = os.path.join(self.dat, 'mapedit-backups', time.strftime('%Y%m%d-%H%M%S'))
            os.makedirs(bk, exist_ok=True)
            for n in ('map.dat', 'item.dat'):
                shutil.copy2(p(n), os.path.join(bk, n))
            for n, data in (('map.dat', self.map), ('item.dat', self.item)):
                with open(p(n) + '.tmp', 'wb') as f:
                    f.write(data)
                os.replace(p(n) + '.tmp', p(n))
                self.mtimes[n] = os.path.getmtime(p(n))
            self.dirty = 0
            self.history.append({'t': time.strftime('%H:%M:%S'), 'what': 'saved to the game', 'tiles': 0})
            return 'Saved. Backup of the old files: ' + bk

    def backups(self):
        d = os.path.join(self.dat, 'mapedit-backups')
        if not os.path.isdir(d):
            return []
        return sorted(n for n in os.listdir(d) if re.match(r'^\d{8}-\d{6}$', n))

    def restore_last(self):
        """put the files from before the last save back (that backup is then marked used)"""
        with self.lock:
            b = self.backups()
            if not b:
                return 'There is no saved backup to go back to.'
            src = os.path.join(self.dat, 'mapedit-backups', b[-1])
            for n in ('map.dat', 'item.dat'):
                shutil.copy2(os.path.join(src, n), os.path.join(self.dat, n))
            os.rename(src, src + '-restored')
            self.load()
            self.history.append({'t': time.strftime('%H:%M:%S'), 'what': 'undid the save of ' + b[-1], 'tiles': 0})
            return 'Went back to the world as it was before the save of %s.' % b[-1]


def server_running():
    try:
        out = subprocess.run(['pgrep', '-x', 'server'], capture_output=True, text=True).stdout.split()
        return any(int(p) != os.getpid() for p in out)
    except Exception:
        return False


# ---------------------------------------------------------------- sprites
class Sprites:
    def __init__(self, client):
        self.client = client
        self.gfx = {}
        for d in ('GFX', 'gfx'):
            for f in glob.glob(os.path.join(client, d, '*')):
                n, e = os.path.splitext(os.path.basename(f))
                if n.isdigit():
                    self.gfx.setdefault(int(n), {})[e.lower()] = f
        try:
            pi = open(os.path.join(client, 'pnglib.idx'), 'rb').read()
            self.pidx = struct.unpack('<%di' % (len(pi) // 4), pi)
            self.pdat = open(os.path.join(client, 'pnglib.dat'), 'rb').read()
        except OSError:
            self.pidx, self.pdat = (), b''
        try:
            self.gidx = open(os.path.join(client, 'gx00.idx'), 'rb').read()
            f = open(os.path.join(client, 'gx00.dat'), 'rb')
            self.gdat = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        except (OSError, ValueError):
            self.gidx, self.gdat = b'', None
        self.cache = {}
        self.lock = threading.Lock()

    @staticmethod
    def png(w, h, rgba):
        raw = b''.join(b'\0' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
        def chunk(t, d):
            c = t + d
            return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + \
            chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')

    def get(self, nr):
        """(content type, bytes) or None; the client looks in the same order"""
        with self.lock:
            if nr in self.cache:
                return self.cache[nr]
        r = None
        d = self.gfx.get(nr, {})
        if '.png' in d:
            r = ('image/png', open(d['.png'], 'rb').read())
        elif nr < len(self.pidx) and self.pidx[nr]:
            st = self.pidx[nr]
            end = min([v for v in self.pidx if v > st] or [len(self.pdat)])
            r = ('image/png', self.pdat[st:end])
        elif '.bmp' in d:
            r = ('image/bmp', open(d['.bmp'], 'rb').read())
        elif self.gdat is not None and nr * 12 + 12 <= len(self.gidx):
            xs, ys, off = struct.unpack_from('<3i', self.gidx, nr * 12)
            if 0 < xs <= 2048 and 0 < ys <= 2048:
                px = struct.unpack_from('<%dH' % (xs * ys), self.gdat, off)
                out = bytearray(xs * ys * 4)
                for k, v in enumerate(px):
                    if v != 0xF81F:
                        out[k * 4] = ((v >> 11) & 31) * 255 // 31
                        out[k * 4 + 1] = ((v >> 5) & 63) * 255 // 63
                        out[k * 4 + 2] = (v & 31) * 255 // 31
                        out[k * 4 + 3] = 255
                r = ('image/png', self.png(xs, ys, bytes(out)))
        with self.lock:
            self.cache[nr] = r
        return r


# ---------------------------------------------------------------- web server
def make_handler(world, sprites, page, minimap):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, ctype, body, cache=False):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'max-age=86400' if cache else 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def js(self, obj):
            self.send(200, 'application/json', json.dumps(obj).encode())

        def do_GET(self):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path == '/':
                return self.send(200, 'text/html; charset=utf-8', page)
            if u.path.startswith('/sprite/'):
                try:
                    r = sprites.get(int(u.path[8:]))
                except ValueError:
                    r = None
                return self.send(200, r[0], r[1], True) if r else self.send(404, 'text/plain', b'no sprite')
            if u.path in ('/icon.ico', '/favicon.ico'):   # the game's own icon, from the client folder
                for n in ('res_icon_1.ico', 'TLB.ICO', 'tlb.ico'):
                    f = os.path.join(sprites.client, n)
                    if os.path.exists(f):
                        return self.send(200, 'image/x-icon', open(f, 'rb').read(), True)
                return self.send(404, 'text/plain', b'none')
            if u.path == '/minimap.png':
                if minimap and os.path.exists(minimap):
                    return self.send(200, 'image/png', open(minimap, 'rb').read(), True)
                return self.send(404, 'text/plain', b'none')
            if u.path == '/api/info':
                running = server_running()
                if running:
                    world.refresh_live()
                return self.js({'running': running, 'online': world.online(), 'gen': world.gen, 'dirty': world.dirty,
                                'undo': len(world.undo), 'redo': len(world.redo), 'areas': world.areas,
                                'minimap': bool(minimap and os.path.exists(minimap)), 'dat': os.path.abspath(world.dat),
                                'backups': len(world.backups())})
            if u.path == '/api/search':
                return self.js(world.search(q.get('q', '')))
            if u.path == '/api/chars':
                return self.js(world.chars())
            if u.path == '/api/history':
                return self.js({'history': world.history[-300:], 'backups': world.backups()})
            if u.path == '/api/region':
                return self.js(world.region(int(q['x0']), int(q['y0']), int(q['x1']), int(q['y1'])))
            if u.path == '/api/tile':
                return self.js(world.tile_info(int(q['x']), int(q['y'])))
            if u.path == '/api/palette':
                return self.js(world.palette())
            self.send(404, 'text/plain', b'not found')

        def do_POST(self):
            u = urlparse(self.path)
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n) or b'{}')
            if u.path in ('/api/edit', '/api/undo', '/api/redo', '/api/save', '/api/relight', '/api/restore') and server_running():
                return self.js({'error': 'The game server is running: the map is view-only. Stop the server to edit.'})
            if u.path == '/api/edit':
                changed, msgs = world.apply(body.get('ops', []), body.get('label', ''))
                return self.js({'changed': changed, 'msgs': msgs, 'dirty': world.dirty, 'undo': len(world.undo), 'redo': len(world.redo)})
            if u.path in ('/api/undo', '/api/redo'):
                tiles = world.undo_redo(u.path[5:])
                return self.js({'tiles': tiles, 'dirty': world.dirty, 'undo': len(world.undo), 'redo': len(world.redo)})
            if u.path == '/api/save':
                return self.js({'msg': world.save(), 'dirty': world.dirty})
            if u.path == '/api/restore':
                if world.dirty:
                    return self.js({'error': 'There are unsaved changes: save or discard them first.'})
                return self.js({'msg': world.restore_last()})
            if u.path == '/api/reload':
                world.load()
                return self.js({'msg': 'Reloaded from disk.'})
            if u.path == '/api/relight':
                if world.dirty:
                    return self.js({'error': 'Save first.'})
                exe = os.path.join(world.server_dir, 'server')
                if not os.path.exists(exe):
                    return self.js({'error': 'No ./server here to recompute the lights.'})
                try:
                    subprocess.run([exe, 'light'], cwd=world.server_dir, capture_output=True, timeout=600)
                except subprocess.TimeoutExpired:
                    return self.js({'error': 'Relight took too long.'})
                world.load()
                return self.js({'msg': 'Lights recomputed (./server light) and the map reloaded.'})
            self.send(404, 'text/plain', b'not found')
    return H


def main():
    ap = argparse.ArgumentParser(description='MyV2 Editor: the Astonia v2 map editor (browser)')
    ap.add_argument('--dat', default='.dat', help='folder with map.dat etc. (default .dat)')
    ap.add_argument('--client', default='/mnt/c/Users/Cody/Desktop/MyV2/Client', help='the game client folder (sprites)')
    ap.add_argument('--area', default='area.c', help="the server's area.c (zone names)")
    ap.add_argument('--minimap', default=None, help='world minimap picture (default: the project docs one)')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--host', default='127.0.0.1')
    a = ap.parse_args()
    if a.minimap is None:
        a.minimap = os.path.join(a.client, 'Claude outputs', 'My-Modern-V2-Project', 'docs', 'world_minimap.png')
    if not os.path.exists(os.path.join(a.dat, 'map.dat')):
        sys.exit('No %s/map.dat - run this in the server folder, or give --dat.' % a.dat)
    print('Loading the world from %s ...' % os.path.abspath(a.dat))
    world = World(a.dat, os.path.dirname(os.path.abspath(a.dat)), a.area)
    sprites = Sprites(a.client)
    if not sprites.gfx and not sprites.pidx and sprites.gdat is None:
        print('Warning: no sprites found in %s (give --client)' % a.client)
    page = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mapedit.html'), 'rb').read() \
        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mapedit.html')) else PAGE.encode()
    httpd = ThreadingHTTPServer((a.host, a.port), make_handler(world, sprites, page, a.minimap))
    print('MyV2 Editor: open http://localhost:%d in your browser.%s Ctrl+C to quit.' %
          (a.port, ' (The game server is running: view only.)' if server_running() else ''))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        if world.dirty:
            print('\nQuit with unsaved changes - they were not written.')
        print('Bye.')


PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MyV2 Editor</title>
<link rel="icon" href="/icon.ico">
<style>
:root {
  --bg: #121316; --rail: #17181c; --panel: #1b1c20; --panel2: #232429; --panel3: #2b2d33; --line: #2f3137; --text: #e7e4dc;
  --dim: #8f8c84; --dim2: #6c6a64; --gold: #d6a443; --gold2: #f0c463; --goldbg: #3a2f17; --ok: #6cc070; --okbg: #1d2e1f; --bad: #e0675a; --badbg: #3a1f1c;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); font: 13px/1.4 system-ui, "Segoe UI", sans-serif; overflow: hidden; }
button, input, select { font: inherit; color: var(--text); }
button { cursor: pointer; background: none; border: 0; }
input[type=text], input[type=number], select { background: var(--panel2); border: 1px solid var(--line); border-radius: 6px; padding: 5px 9px; outline: none; }
input[type=text]:focus, input[type=number]:focus { border-color: var(--gold); }
input[type=checkbox] { accent-color: var(--gold); width: 15px; height: 15px; margin: 0; }
kbd { background: var(--panel3); border: 1px solid var(--line); border-radius: 3px; padding: 0 4px; font: 11px ui-monospace, Consolas, monospace; color: var(--text); }
.mono { font-family: ui-monospace, Consolas, monospace; }
svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; display: block; }

/* layout */
#app { display: grid; grid-template-columns: 64px 280px 1fr 280px; grid-template-rows: 52px 1fr; height: 100%; }
#app.noright { grid-template-columns: 64px 280px 1fr 0; }
header { grid-column: 1 / -1; display: flex; align-items: center; gap: 14px; padding: 0 14px; border-bottom: 1px solid var(--line); background: var(--rail); }
.logo { display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 15px; min-width: 316px; }
.logo img { width: 32px; height: 32px; border-radius: 6px; image-rendering: pixelated; box-shadow: 0 0 0 1px #3b3d44; }
.logo .ed { color: var(--gold); }
#search { position: relative; flex: 1; max-width: 560px; margin: 0 auto; }
#search input { width: 100%; padding: 8px 12px 8px 34px; border-radius: 8px; background: var(--panel); }
#search > svg { position: absolute; left: 11px; top: 9px; width: 16px; height: 16px; color: var(--dim); }
#search .hint { position: absolute; right: 9px; top: 7px; }
#results { position: absolute; left: 0; right: 0; top: 40px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; max-height: 420px; overflow-y: auto; display: none; z-index: 20; box-shadow: 0 12px 30px rgba(0,0,0,.5); }
#results .r { display: flex; gap: 10px; align-items: center; padding: 6px 10px; cursor: pointer; }
#results .r:hover, #results .r.act { background: var(--panel3); }
#results .r canvas { width: 30px; height: 30px; flex: none; }
#results .ty { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: var(--dim2); width: 46px; flex: none; }
#results .sub { color: var(--dim); font-size: 11px; margin-left: auto; }
#pill { margin-left: auto; padding: 4px 12px; border-radius: 99px; font-size: 12px; white-space: nowrap; }
#pill.up { background: var(--okbg); color: var(--ok); border: 1px solid #2c4a2f; }
#pill.down { background: var(--goldbg); color: var(--gold2); border: 1px solid #574420; }

nav { background: var(--rail); border-right: 1px solid var(--line); display: flex; flex-direction: column; align-items: center; padding: 8px 0; gap: 4px; }
nav button { width: 52px; padding: 7px 0 6px; border-radius: 8px; color: var(--dim); display: flex; flex-direction: column; align-items: center; gap: 3px; font-size: 11px; }
nav button svg { width: 20px; height: 20px; }
nav button:hover { color: var(--text); background: var(--panel); }
nav button.on { color: var(--gold2); background: var(--goldbg); }
nav .grow { flex: 1; }

#left { background: var(--panel); border-right: 1px solid var(--line); display: flex; flex-direction: column; min-height: 0; }
.tabs { display: flex; flex-wrap: wrap; gap: 2px 4px; padding: 10px 10px 0; border-bottom: 1px solid var(--line); }
.tabs button { padding: 6px 8px 8px; color: var(--dim); border-bottom: 2px solid transparent; }
.tabs button:hover { color: var(--text); }
.tabs button.on { color: var(--gold2); border-bottom-color: var(--gold); }
#lsearch { margin: 10px; }
.sect { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--dim2); padding: 6px 12px 6px; }
#palwrap { flex: 1; overflow-y: auto; padding: 0 8px 10px 10px; min-height: 0; }
.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.cell { aspect-ratio: 1 / 1.08; background: var(--panel2); border: 1px solid var(--line); border-radius: 7px; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; padding: 2px 2px 3px; font: 10px ui-monospace, Consolas, monospace; color: var(--dim); overflow: hidden; text-align: center; line-height: 1.1; }
.cell:hover { border-color: #4a4c53; }
.cell.sel { border-color: var(--gold); background: var(--goldbg); color: var(--gold2); box-shadow: 0 0 0 1px var(--gold) inset; }
.cell canvas { width: 100%; flex: 1; min-height: 0; object-fit: contain; }
.cell .sw { width: 20px; height: 20px; border-radius: 5px; margin: auto 0 6px; }
.cell .lab { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.list .row { display: flex; gap: 10px; align-items: center; padding: 5px 6px; border-radius: 6px; cursor: pointer; border: 1px solid transparent; }
.list .row:hover { background: var(--panel2); }
.list .row.sel { border-color: var(--gold); background: var(--goldbg); }
.list .row canvas { width: 34px; height: 34px; flex: none; }
.list .row .n { color: var(--dim); font-size: 11px; }
.empty { color: var(--dim); padding: 10px 4px; }
#card { border-top: 1px solid var(--line); padding: 10px 12px; display: flex; gap: 12px; align-items: center; min-height: 62px; }
#card canvas { width: 40px; height: 40px; flex: none; background: var(--panel2); border-radius: 6px; }
#card .t { font-weight: 600; }
#card .s { color: var(--dim); font-size: 12px; }

#view { position: relative; min-width: 0; min-height: 0; overflow: hidden; background: #050506; }
#cv { width: 100%; height: 100%; display: block; }
#bar { position: absolute; left: 10px; right: 10px; top: 10px; display: flex; gap: 8px; flex-wrap: wrap; pointer-events: none; z-index: 3; }
.grp { display: flex; align-items: center; gap: 2px; background: rgba(27,28,32,.94); border: 1px solid var(--line); border-radius: 9px; padding: 3px; pointer-events: auto; box-shadow: 0 4px 14px rgba(0,0,0,.4); }
.grp button { width: 32px; height: 30px; border-radius: 6px; color: #c9c6be; display: grid; place-items: center; }
.grp button:hover:not(:disabled) { background: var(--panel3); color: #fff; }
.grp button.on { background: var(--goldbg); color: var(--gold2); box-shadow: 0 0 0 1px #6b5323 inset; }
.grp button:disabled { opacity: .35; cursor: default; }
.grp .lbl { color: var(--dim2); font-size: 11px; padding: 0 4px 0 8px; }
.grp select { background: transparent; border: 0; padding: 3px 4px; }
.grp select option { background: var(--panel); }
.grp .zv { width: 48px; text-align: center; color: var(--dim); font-size: 12px; }
#bar .rgt { margin-left: auto; }
#coords { position: absolute; left: 10px; bottom: 10px; background: rgba(23,24,28,.92); border: 1px solid var(--line); border-radius: 7px; padding: 4px 10px; color: var(--dim); font: 12px ui-monospace, Consolas, monospace; pointer-events: none; z-index: 3; }
#mini { position: absolute; right: 10px; bottom: 10px; width: 220px; height: 220px; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: #000; z-index: 3; box-shadow: 0 6px 20px rgba(0,0,0,.5); display: none; }
#mini .t { position: absolute; left: 8px; top: 5px; font-size: 10px; letter-spacing: .08em; color: rgba(255,255,255,.65); text-shadow: 0 1px 2px #000; pointer-events: none; }
#mini canvas { width: 100%; height: 100%; cursor: crosshair; image-rendering: pixelated; }
#world { position: absolute; inset: 0; background: rgba(5,5,6,.82); z-index: 10; display: none; place-items: center; }
#world canvas { width: min(92%, 88vh); aspect-ratio: 1; image-rendering: pixelated; border: 1px solid var(--line); border-radius: 8px; cursor: crosshair; }
#world .t { position: absolute; top: 14px; color: var(--dim); }
#banner { position: absolute; left: 50%; transform: translateX(-50%); top: 56px; background: var(--badbg); color: #ffd6cf; border: 1px solid #5a2c26; padding: 6px 14px; border-radius: 8px; z-index: 4; display: none; font-size: 12px; }
#toast { position: absolute; left: 50%; transform: translateX(-50%); bottom: 16px; max-width: 70%; background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--gold); padding: 8px 14px; border-radius: 7px; display: none; z-index: 12; white-space: pre-line; }

#right { background: var(--panel); border-left: 1px solid var(--line); display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
#rscroll { flex: 1; overflow-y: auto; padding: 4px 14px 10px; min-height: 0; }
#right .sect { padding: 14px 0 8px; }
#tile { color: var(--dim); }
#tile .hd { color: var(--text); font-weight: 600; }
#tile .kv { display: grid; grid-template-columns: 62px 1fr; gap: 6px 8px; align-items: center; margin-top: 8px; }
#tile .kv .k { color: var(--dim2); font-size: 12px; }
#tile .kv .v { display: flex; gap: 6px; align-items: center; min-width: 0; }
#tile .kv canvas { width: 28px; height: 28px; flex: none; background: var(--panel2); border-radius: 4px; }
#tile .kv input[type=number] { width: 72px; padding: 3px 6px; }
#tile .x { color: var(--dim); padding: 1px 6px; border: 1px solid var(--line); border-radius: 5px; font-size: 11px; }
#tile .x:hover { color: var(--bad); border-color: var(--bad); }
#tile .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); }
#tile .flg { display: grid; grid-template-columns: 1fr 1fr; gap: 3px 8px; margin-top: 8px; }
.chk { display: flex; align-items: center; gap: 8px; padding: 3px 0; cursor: pointer; user-select: none; }
.chk .dot { width: 9px; height: 9px; border-radius: 3px; flex: none; }
.chk span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.flags2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 10px; }
.keys { color: var(--dim); font-size: 12px; line-height: 1.75; }
#foot { border-top: 1px solid var(--line); padding: 12px 14px; }
#dirty { color: var(--dim); margin-bottom: 8px; }
#dirty.on { color: var(--gold2); }
.btns { display: flex; gap: 8px; align-items: center; }
.btn { padding: 7px 14px; border-radius: 7px; }
.btn.pri { background: #9a7428; color: #fff7e6; font-weight: 600; }
.btn.pri:hover:not(:disabled) { background: #b38630; }
.btn.ghost { color: var(--dim); }
.btn.ghost:hover:not(:disabled) { color: var(--text); }
.btn:disabled { opacity: .4; cursor: default; }
#undosave { margin-top: 8px; color: var(--dim2); font-size: 12px; padding: 0; }
#undosave:hover:not(:disabled) { color: var(--text); }
#undosave:disabled { opacity: .5; cursor: default; }
</style>
</head>
<body>
<div id="app">
<header>
  <div class="logo"><img src="/icon.ico" alt=""><div>MyV2 <span class="ed">Editor</span></div></div>
  <div id="search">
    <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input id="q" type="text" placeholder="Search items, NPCs, players, places… or type x y" autocomplete="off">
    <span class="hint"><kbd>Ctrl K</kbd></span>
    <div id="results"></div>
  </div>
  <div id="pill" class="down">…</div>
</header>

<nav>
  <button data-m="map" class="on" title="Build the map"><svg viewBox="0 0 24 24"><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/></svg>Map</button>
  <button data-m="npcs" title="Every NPC and player in the world"><svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/></svg>NPCs</button>
  <button data-m="history" title="What you changed, and the saves"><svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></svg>History</button>
  <div class="grow"></div>
  <button data-m="help" title="How it works"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17h.01"/></svg>Help</button>
</nav>

<aside id="left">
  <div class="tabs" id="tabs"></div>
  <input id="lsearch" type="text" placeholder="Search name or number" autocomplete="off">
  <div id="palwrap"></div>
  <div id="card"></div>
</aside>

<main id="view">
  <canvas id="cv"></canvas>
  <div id="bar">
    <div class="grp" id="toolgrp"></div>
    <div class="grp"><span class="lbl">Size</span>
      <select id="size" title="Brush size: [ and ]"><option value="1">1×1</option><option value="2">2×2</option><option value="3">3×3</option><option value="5">5×5</option><option value="7">7×7</option><option value="9">9×9</option></select>
    </div>
    <div class="grp">
      <button id="undo" title="Undo (Ctrl+Z)"><svg viewBox="0 0 24 24"><path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/></svg></button>
      <button id="redo" title="Redo (Ctrl+Y)"><svg viewBox="0 0 24 24"><path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/></svg></button>
    </div>
    <div class="grp">
      <button id="zout" title="Zoom out (wheel)"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6"/></svg></button>
      <span class="zv" id="zv">100%</span>
      <button id="zin" title="Zoom in (wheel)"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6M11 8v6"/></svg></button>
    </div>
    <div class="grp">
      <button id="tgrid" title="Grid (G)"><svg viewBox="0 0 24 24"><path d="M12 3 21 12 12 21 3 12z"/><path d="M7.5 7.5 16.5 16.5M16.5 7.5 7.5 16.5"/></svg></button>
      <button id="twalls" title="See through walls (W)"><svg viewBox="0 0 24 24"><path d="M4 20V8l8-4 8 4v12"/><path d="M9 20v-6h6v6" stroke-dasharray="2 2"/></svg></button>
      <button id="tlight" title="Light from lamps, as at night (L)"><svg viewBox="0 0 24 24"><path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/></svg></button>
      <button id="tref" title="Load the world again from disk"><svg viewBox="0 0 24 24"><path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/></svg></button>
    </div>
    <div class="grp rgt">
      <button id="tright" title="Show / hide the right panel"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></svg></button>
    </div>
  </div>
  <div id="banner">The game server is running: you can look around, but editing is off. Stop the server to edit.</div>
  <div id="coords">–</div>
  <div id="mini"><span class="t">MAP</span><canvas id="mcv" width="1024" height="1024" title="Click to go there · M for the big map"></canvas></div>
  <div id="world"><span class="t">World map — click to go there · M or Esc to close</span><canvas id="wcv" width="1024" height="1024"></canvas></div>
  <div id="toast"></div>
</main>

<aside id="right">
  <div id="rscroll">
    <div class="sect">Tile</div>
    <div id="tile">Pick the select tool (<kbd>V</kbd>) and click a tile to see and change what is on it.</div>
    <div class="sect">Show</div>
    <div id="layers"></div>
    <div class="sect">Show flags</div>
    <div id="flagshow" class="flags2"></div>
    <div class="sect">Keys</div>
    <div class="keys">
      <kbd>V</kbd> select · <kbd>B</kbd> brush · <kbd>U</kbd> rectangle · <kbd>F</kbd> fill · <kbd>E</kbd> erase · <kbd>I</kbd> pick · <kbd>H</kbd> or <kbd>Space</kbd> move<br>
      Right-drag moves · wheel zooms · <kbd>[</kbd> <kbd>]</kbd> brush size<br>
      <kbd>Alt</kbd> paints the opposite (clears a flag, erases)<br>
      <kbd>Ctrl Z</kbd> / <kbd>Ctrl Y</kbd> undo / redo · <kbd>Ctrl S</kbd> save<br>
      <kbd>M</kbd> world map · <kbd>Ctrl K</kbd> search · <kbd>G</kbd> <kbd>W</kbd> <kbd>L</kbd> grid, walls, light
    </div>
  </div>
  <div id="foot">
    <div id="dirty">No unsaved changes</div>
    <div class="btns">
      <button class="btn pri" id="save">Save to the game</button>
      <button class="btn ghost" id="discard">Discard</button>
    </div>
    <button id="undosave" title="Put the world back as it was before the last save (from its backup)">Undo last save</button>
  </div>
</aside>
</div>

<script>
'use strict';
const MAPX = 1024, CH = 32;
const $ = s => document.querySelector(s);
const cv = $('#cv'), ctx = cv.getContext('2d');
const base = document.createElement('canvas'), bctx = base.getContext('2d');
let W = 0, H = 0, cam = { x: 0, y: 0 }, zoom = 1;
let info = { running: false, online: 0, dirty: 0, undo: 0, redo: 0, areas: [], gen: 0, backups: 0 };
let pal = null, mode = 'map', tab = 'builder', tool = 'brush';
let brush = { kind: 'floor', s: 142, set: true };
let recent = [];
let size = 1;
const show = { floors: true, walls: true, items: true, chars: true, see: false, light: false, grid: false, names: true };
const flagOn = new Set();
let selTile = null;
const chunks = new Map(), sprites = new Map();
let hover = null, stroke = null, rect = null, panning = null, spaceDown = false, needDraw = true, baseDirty = true;

const FLAGS = ['blocks walking', 'blocks sight', 'indoors', 'under water', 'no lag', 'no monsters', 'bank', 'tavern',
  'no magic', 'death trap', 'no light', 'arena', 'lit', 'no expire', 'no fighting'];
const FCOL = ['#ef5a50', '#b48cff', '#5b8ff5', '#3cc9d8', '#8c96a8', '#47c98a', '#e8b44a', '#f08a3c', '#d468e8', '#ff5a3c', '#5d6470', '#f06ea6', '#ffe9a8', '#a6d65c', '#2fbfa0'];
const TOOLS = [
  ['select', 'V', 'Select: look at a tile and change it', '<path d="M5 3l14 8-6 2-3 6z"/>'],
  ['brush', 'B', 'Brush: paint the chosen piece', '<path d="M18 3l3 3-9 9-4 1 1-4z"/><path d="M8 16c-2 0-4 2-4 5 3 0 5-2 5-4"/>'],
  ['rect', 'U', 'Rectangle: drag an area', '<rect x="4" y="5" width="16" height="14" rx="1"/>'],
  ['fill', 'F', 'Fill: a room (up to its walls, indoors or outdoors like the tile you click) or, with a floor, a patch of the same floor', '<path d="M5 12 12 5l7 7-7 7z"/><path d="M19 15c1 2 2 3 2 4a2 2 0 0 1-4 0c0-1 1-2 2-4z"/>'],
  ['erase', 'E', 'Erase: remove walls, objects and items (floor stays)', '<path d="m3 17 9-9 7 7-5 5H7z"/><path d="M14 20h7"/>'],
  ['pick', 'I', 'Pick: take what is on a tile as the brush', '<path d="M20 4a2.8 2.8 0 0 0-4 0l-3 3 4 4 3-3a2.8 2.8 0 0 0 0-4z"/><path d="m13 7-9 9v4h4l9-9"/>'],
  ['pan', 'H', 'Move the view', '<path d="M8 13V6a1.5 1.5 0 0 1 3 0v6M11 11V4a1.5 1.5 0 0 1 3 0v7M14 11V5.5a1.5 1.5 0 0 1 3 0V13M17 9.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-1a7 7 0 0 1-5.5-2.7L4.3 14a1.6 1.6 0 0 1 2.4-2l1.3 1.3"/>'],
];

// ---------------------------------------------------------------- helpers
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  return r.json();
}
let toastT = 0;
function toast(msg, bad) {
  const t = $('#toast'); t.textContent = msg; t.style.display = 'block';
  t.style.borderLeftColor = bad ? 'var(--bad)' : 'var(--gold)';
  clearTimeout(toastT); toastT = setTimeout(() => t.style.display = 'none', bad ? 6000 : 3500);
}
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const wx = (x, y) => 16 * (x + y), wy = (x, y) => 8 * (x - y);
function screenToTile(sx, sy) {
  const px = (sx - W / 2) / zoom + cam.x, py = (sy - H / 2) / zoom + cam.y;
  const u = (px - 32) / 16, v = (py - 56) / 8;
  return { x: Math.round((u + v) / 2), y: Math.round((u - v) / 2) };
}
function tileToScreen(x, y) { return { sx: (wx(x, y) + 32 - cam.x) * zoom + W / 2, sy: (wy(x, y) + 56 - cam.y) * zoom + H / 2 }; }
function centerOn(x, y) { cam.x = wx(x, y) + 32; cam.y = wy(x, y) + 56; redraw(); }
function redraw() { needDraw = true; baseDirty = true; }
function redrawTop() { needDraw = true; }

// ---------------------------------------------------------------- sprites
const waiting = new Map();
function sprite(n) {
  if (!n) return null;
  let s = sprites.get(n);
  if (s) return s.img;
  s = { img: null }; sprites.set(n, s);
  const im = new Image();
  im.onload = () => {
    const c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
    const g = c.getContext('2d'); g.drawImage(im, 0, 0);
    try {
      const d = g.getImageData(0, 0, c.width, c.height), a = d.data;
      for (let i = 0; i < a.length; i += 4) if (a[i] > 240 && a[i + 1] < 16 && a[i + 2] > 240) a[i + 3] = 0;
      g.putImageData(d, 0, 0);
    } catch (e) {}
    s.img = c; redraw();
    const l = waiting.get(n); if (l) { waiting.delete(n); l.forEach(paintThumb); }
  };
  im.src = '/sprite/' + n;
  return null;
}
function thumb(n, w, h) {
  const c = document.createElement('canvas'); c.width = w; c.height = h || w; c.dataset.spr = n;
  paintThumb(c); return c;
}
function paintThumb(c) {
  const n = +c.dataset.spr, im = sprite(n), g = c.getContext('2d');
  g.clearRect(0, 0, c.width, c.height);
  if (!n) return;
  if (!im) { if (!waiting.has(n)) waiting.set(n, []); waiting.get(n).push(c); return; }
  const s = Math.min(c.width / im.width, c.height / im.height, 2);
  g.imageSmoothingEnabled = s < 1;
  g.drawImage(im, (c.width - im.width * s) / 2, (c.height - im.height * s) / 2 + (im.height > im.width ? 0 : c.height * .08), im.width * s, im.height * s);
}

// ---------------------------------------------------------------- map data
function chunk(cx, cy) {
  const k = cx + ',' + cy;
  let c = chunks.get(k);
  if (c) return c.data;
  c = { data: null }; chunks.set(k, c);
  api(`/api/region?x0=${cx * CH}&y0=${cy * CH}&x1=${cx * CH + CH - 1}&y1=${cy * CH + CH - 1}`).then(d => { c.data = d; redraw(); });
  return null;
}
function refetch(tiles) {
  const seen = new Set();
  for (const [x, y] of tiles) {
    const cx = Math.floor(x / CH), cy = Math.floor(y / CH), k = cx + ',' + cy;
    if (seen.has(k)) continue; seen.add(k);
    const old = chunks.get(k), c = { data: old ? old.data : null }; chunks.set(k, c);
    api(`/api/region?x0=${cx * CH}&y0=${cy * CH}&x1=${cx * CH + CH - 1}&y1=${cy * CH + CH - 1}`).then(d => { c.data = d; redraw(); });
  }
}
function T(x, y) {
  if (x < 0 || y < 0 || x >= MAPX || y >= MAPX) return null;
  const d = chunk(Math.floor(x / CH), Math.floor(y / CH));
  return d ? { d, i: (y - d.y0) * d.w + (x - d.x0) } : null;
}

// ---------------------------------------------------------------- drawing
function visible() {
  const pts = [[0, 0], [W, 0], [0, H], [W, H]].map(([sx, sy]) => {
    const px = (sx - W / 2) / zoom + cam.x, py = (sy - H / 2) / zoom + cam.y;
    const u = (px - 32) / 16, v = (py - 56) / 8;
    return [(u + v) / 2, (u - v) / 2];
  });
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  return { x0: Math.max(0, Math.floor(Math.min(...xs)) - 2), x1: Math.min(MAPX - 1, Math.ceil(Math.max(...xs)) + 8),
           y0: Math.max(0, Math.floor(Math.min(...ys)) - 8), y1: Math.min(MAPX - 1, Math.ceil(Math.max(...ys)) + 2) };
}
let g2 = bctx;
function put(n, x, y, a) {
  const im = sprite(n);
  if (!im) return;
  if (a !== undefined) g2.globalAlpha = a;
  g2.drawImage(im, wx(x, y) - im.width / 2 + 32, wy(x, y) - im.height + 64);
  if (a !== undefined) g2.globalAlpha = 1;
}
function diamond(x, y, c) {
  c = c || g2;
  const cx = wx(x, y) + 32, cy = wy(x, y) + 56;
  c.beginPath(); c.moveTo(cx - 16, cy); c.lineTo(cx, cy - 8); c.lineTo(cx + 16, cy); c.lineTo(cx, cy + 8); c.closePath();
}
function draw() {
  needDraw = false;
  const v = visible();
  if (baseDirty) {
    baseDirty = false;
    if (base.width !== W || base.height !== H) { base.width = W; base.height = H; }
    g2 = bctx;
    g2.setTransform(1, 0, 0, 1, 0, 0);
    g2.fillStyle = '#050506'; g2.fillRect(0, 0, W, H);
    g2.setTransform(zoom, 0, 0, zoom, W / 2 - cam.x * zoom, H / 2 - cam.y * zoom);
    g2.imageSmoothingEnabled = zoom < 1;
    if (show.floors) for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
      const t = T(x, y);
      if (!t) continue;
      const g = t.d.g[t.i];
      if (g && g !== 1008) put(g, x, y);
    }
    const fl = [...flagOn];
    if (fl.length || show.grid || show.light) {
      g2.lineWidth = 1 / zoom;
      for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
        const t = T(x, y);
        if (!t) continue;
        const f = t.d.fl[t.i];
        if (show.light && t.d.g[t.i] !== 1008) {
          const lit = (f >>> 12) & 1, l = lit ? 64 : t.d.li[t.i];
          const a = Math.max(0, Math.min(.86, 1 - l / 48));
          if (a > .02) { diamond(x, y); g2.fillStyle = `rgba(0,0,8,${a})`; g2.fill(); }
        }
        for (const b of fl) if ((f >>> b) & 1) { diamond(x, y); g2.fillStyle = FCOL[b] + '70'; g2.fill(); }
        if (show.grid && zoom >= .45) { diamond(x, y); g2.strokeStyle = 'rgba(255,255,255,.13)'; g2.stroke(); }
      }
    }
    const chars = show.chars && zoom >= .3;
    for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
      const t = T(x, y);
      if (!t) continue;
      const d = t.d, i = t.i;
      if (show.walls && d.f[i]) put(d.f[i], x, y, show.see ? .28 : undefined);
      if (show.items && d.it[i]) put(d.it[i], x, y);
      if (chars && d.ch[i]) put(d.ch[i], x, y);
    }
    drawMini(v);
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.drawImage(base, 0, 0);
  ctx.setTransform(zoom, 0, 0, zoom, W / 2 - cam.x * zoom, H / 2 - cam.y * zoom);
  if (rect) {
    ctx.fillStyle = 'rgba(214,164,67,.33)';
    for (let y = Math.min(rect.a.y, rect.b.y); y <= Math.max(rect.a.y, rect.b.y); y++)
      for (let x = Math.min(rect.a.x, rect.b.x); x <= Math.max(rect.a.x, rect.b.x); x++) { diamond(x, y, ctx); ctx.fill(); }
  }
  if (hover && tool !== 'pan') {
    ctx.lineWidth = 1.6 / zoom; ctx.strokeStyle = '#ffd36a';
    for (const [x, y] of footprint(hover.x, hover.y)) { diamond(x, y, ctx); ctx.stroke(); }
  }
  if (selTile) { diamond(selTile.x, selTile.y, ctx); ctx.lineWidth = 2.2 / zoom; ctx.strokeStyle = '#6fb0ff'; ctx.stroke(); }
  // area names, in screen space
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (show.names && zoom >= .35) {
    ctx.font = '600 12px system-ui, Segoe UI, sans-serif'; ctx.textBaseline = 'middle';
    const used = [];
    for (const a of info.areas) {
      if (a[2] < v.x0 || a[0] > v.x1 || a[3] < v.y0 || a[1] > v.y1) continue;
      if ((a[2] - a[0]) * (a[3] - a[1]) < 12) continue;
      const p = tileToScreen((a[0] + a[2]) / 2, (a[1] + a[3]) / 2);
      if (p.sx < 0 || p.sy < 0 || p.sx > W || p.sy > H) continue;
      if (used.some(u => Math.abs(u[0] - p.sx) < 110 && Math.abs(u[1] - p.sy) < 22)) continue;
      used.push([p.sx, p.sy]);
      const w = ctx.measureText(a[4]).width + 14;
      ctx.fillStyle = 'rgba(20,18,12,.78)'; ctx.strokeStyle = 'rgba(214,164,67,.5)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.roundRect(p.sx - w / 2, p.sy - 10, w, 20, 4); ctx.fill(); ctx.stroke();
      ctx.fillStyle = '#f3d79b'; ctx.textAlign = 'center'; ctx.fillText(a[4], p.sx, p.sy + 1);
    }
  }
}
function loop() { if (needDraw) draw(); requestAnimationFrame(loop); }

// ---------------------------------------------------------------- minimap and world map
const mini = new Image(); let miniOk = false;
function drawMap(c, v) {
  const g = c.getContext('2d');
  g.drawImage(mini, 0, 0, 1024, 1024);
  if (!v) return;
  g.strokeStyle = '#ffd36a'; g.lineWidth = c === $('#mcv') ? 10 : 4;
  g.strokeRect(v.y0, v.x0, Math.max(10, v.y1 - v.y0), Math.max(10, v.x1 - v.x0));   // minimap: column = map y, row = map x
}
function drawMini(v) { if (miniOk) drawMap($('#mcv'), v); }
function mapClick(e) {
  const r = e.target.getBoundingClientRect();
  centerOn(Math.floor((e.clientY - r.top) / r.height * 1024), Math.floor((e.clientX - r.left) / r.width * 1024));
}
$('#mcv').onclick = mapClick;
$('#wcv').onclick = e => { mapClick(e); toggleWorld(false); };
function toggleWorld(on) {
  if (!miniOk) return toast('No world map picture found (docs/world_minimap.png).', true);
  const w = $('#world'); on = on === undefined ? w.style.display !== 'grid' : on;
  w.style.display = on ? 'grid' : 'none';
  if (on) drawMap($('#wcv'), visible());
}

// ---------------------------------------------------------------- left panel
const TABS = { builder: 'Builder', floors: 'Floors', walls: 'Walls', objects: 'Objects', items: 'Items', flags: 'Flags' };
function cats() {
  // [number, name, sprite, take, driver, blocks, item]
  const t = pal.templates;
  return {
    walls: t.filter(x => !x[3] && !x[6] && (x[5] & 2)),          // drawn into the tile and block sight: walls, trees, pillars
    objects: t.filter(x => !x[3] && !(!x[6] && (x[5] & 2))),
    items: t.filter(x => x[3]),
  };
}
function brushKey(b) { return b.kind + ':' + (b.kind === 'place' ? b.t[0] : b.kind === 'flag' ? b.bit : b.s); }
function setBrush(b, keepTool) {
  brush = b;
  const k = brushKey(b);
  recent = [b, ...recent.filter(r => brushKey(r) !== k)].slice(0, 24);
  if (!keepTool && (tool === 'select' || tool === 'pick' || tool === 'pan' || tool === 'erase')) setTool('brush');
  card(); document.querySelectorAll('#palwrap [data-k]').forEach(el => el.classList.toggle('sel', el.dataset.k === k));
}
function card() {
  const c = $('#card'); c.innerHTML = '';
  let spr = 0, t = '', s = '';
  if (brush.kind === 'floor') { spr = brush.s; t = 'Floor ' + brush.s; s = brush.set && pal && pal.sets[brush.s] ? 'Floor sprite ' + brush.s + ' (random variants ' + pal.sets[brush.s].join(', ') + ')' : 'Floor sprite ' + brush.s; }
  else if (brush.kind === 'place') { spr = brush.t[2]; t = brush.t[1]; s = `Template ${brush.t[0]} · ${brush.t[6] ? 'item' : 'drawn into the tile'}${brush.t[5] & 1 ? ' · blocks walking' : ''}`; }
  else if (brush.kind === 'object') { spr = brush.s; t = 'Object ' + brush.s; s = 'Picked from the map' + (brush.block & 1 ? ' · blocks walking' : '') + (brush.block & 2 ? ' · blocks sight' : ''); }
  else if (brush.kind === 'flag') { t = 'Flag: ' + FLAGS[brush.bit]; s = 'Paint sets it · Alt+paint clears it'; }
  if (brush.kind === 'flag') { const d = document.createElement('div'); d.style.cssText = `width:40px;height:40px;border-radius:8px;background:${FCOL[brush.bit]};flex:none`; c.appendChild(d); }
  else c.appendChild(thumb(spr, 40));
  const d = document.createElement('div'); d.innerHTML = `<div class="t"></div><div class="s"></div>`;
  d.firstChild.textContent = t; d.lastChild.textContent = s; c.appendChild(d);
}
function lazy(container, items, make) {
  container.innerHTML = '';
  let shown = 0;
  const more = () => {
    const end = Math.min(items.length, shown + 96);
    for (; shown < end; shown++) container.appendChild(make(items[shown]));
    if (shown < items.length) {
      const s = document.createElement('div'); s.style.cssText = 'height:10px;grid-column:1/-1'; container.appendChild(s);
      const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { io.disconnect(); s.remove(); more(); } }, { root: $('#palwrap') });
      io.observe(s);
    }
  };
  more();
  if (!items.length) container.innerHTML = '<div class="empty" style="grid-column:1/-1">Nothing matches.</div>';
}
function cellFloor(s, n) {
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = 'floor:' + s;
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = `Floor ${s}` + (n ? ` · on ${n} tiles` : '') + (pal.sets[s] ? ' · paints random variants' : '');
  c.appendChild(thumb(s, 64, 48)); const l = document.createElement('div'); l.className = 'lab'; l.textContent = s; c.appendChild(l);
  c.onclick = () => setBrush({ kind: 'floor', s, set: true });
  return c;
}
function cellFlag(b) {
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = 'flag:' + b;
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = 'Paint the ' + FLAGS[b] + ' flag (Alt+paint clears it)';
  c.innerHTML = `<div class="sw" style="background:${FCOL[b]}"></div><div class="lab"></div>`;
  c.lastChild.textContent = FLAGS[b];
  c.onclick = () => { setBrush({ kind: 'flag', bit: b }); if (!flagOn.has(b)) { flagOn.add(b); layersUI(); redraw(); } };
  return c;
}
function cellTemp(t) {
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = 'place:' + t[0];
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = `${t[1]} · template ${t[0]} · ${t[6] ? 'item' : 'drawn into the tile'}${t[5] & 1 ? ' · blocks walking' : ''}${t[5] & 2 ? ' · blocks sight' : ''}`;
  c.appendChild(thumb(t[2], 64, 64)); const l = document.createElement('div'); l.className = 'lab'; l.textContent = t[1]; c.appendChild(l);
  c.onclick = () => setBrush({ kind: 'place', t });
  return c;
}
function cellRecent(b) {
  if (b.kind === 'floor') return cellFloor(b.s, 0);
  if (b.kind === 'flag') return cellFlag(b.bit);
  if (b.kind === 'place') return cellTemp(b.t);
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = brushKey(b);
  c.appendChild(thumb(b.s, 64, 64)); const l = document.createElement('div'); l.className = 'lab'; l.textContent = 'obj ' + b.s; c.appendChild(l);
  c.onclick = () => setBrush(b); return c;
}
function leftUI() {
  const tabs = $('#tabs'), w = $('#palwrap'), q = $('#lsearch').value.trim().toLowerCase();
  if (mode === 'map') {
    tabs.innerHTML = Object.entries(TABS).map(([k, v]) => `<button data-tab="${k}" class="${k === tab ? 'on' : ''}">${v}</button>`).join('');
    tabs.querySelectorAll('button').forEach(b => b.onclick = () => { tab = b.dataset.tab; $('#lsearch').value = ''; leftUI(); });
    $('#lsearch').style.display = ''; $('#card').style.display = '';
    $('#lsearch').placeholder = 'Search name or number';
  } else {
    tabs.innerHTML = `<button class="on">${{ npcs: 'NPCs and players', history: 'History', help: 'Help' }[mode]}</button>`;
    $('#lsearch').style.display = mode === 'npcs' ? '' : 'none'; $('#card').style.display = 'none';
    $('#lsearch').placeholder = 'Search a name';
  }
  w.innerHTML = '';
  if (!pal && mode === 'map') { w.innerHTML = '<div class="empty">Loading…</div>'; return; }
  const sect = t => { const s = document.createElement('div'); s.className = 'sect'; s.style.padding = '8px 2px 8px'; s.textContent = t; w.appendChild(s); };
  const grid = () => { const g = document.createElement('div'); g.className = 'grid'; w.appendChild(g); return g; };
  const match = (name, num) => !q || name.toLowerCase().includes(q) || String(num) === q || String(num).startsWith(q);
  if (mode === 'map') {
    const C = cats();
    if (tab === 'builder') {
      if (recent.length) { sect('Recently used'); lazy(grid(), recent.filter(b => match(b.kind === 'place' ? b.t[1] : b.kind === 'flag' ? FLAGS[b.bit] : '', b.kind === 'place' ? b.t[0] : b.s ?? '')), cellRecent); }
      sect('Floors and flags');
      const g = grid();
      const fl = FLAGS.map((f, i) => i).filter(i => match(FLAGS[i], ''));
      const fs = pal.floors.filter(([s]) => match('', s)).slice(0, 60);
      lazy(g, [...fl.map(b => ['f', b]), ...fs.map(f => ['g', f])], ([k, v]) => k === 'f' ? cellFlag(v) : cellFloor(v[0], v[1]));
      sect('Walls'); lazy(grid(), C.walls.filter(t => match(t[1], t[0])).slice(0, 24), cellTemp);
      sect('Objects'); lazy(grid(), C.objects.filter(t => match(t[1], t[0])).slice(0, 24), cellTemp);
    } else if (tab === 'floors') {
      const list = pal.floors.filter(([s]) => match('', s));
      if (/^\d+$/.test(q) && !list.some(([s]) => String(s) === q)) list.unshift([+q, 0]);
      sect('Floors · by how often they are used'); lazy(grid(), list, f => cellFloor(f[0], f[1]));
    } else if (tab === 'flags') {
      sect('Paint a flag on tiles'); lazy(grid(), FLAGS.map((f, i) => i).filter(i => match(FLAGS[i], '')), cellFlag);
    } else {
      const list = C[tab].filter(t => match(t[1], t[0]));
      sect({ walls: 'Walls · drawn into the tile, they block', objects: 'Objects · furniture, decoration, doors, chests…', items: 'Items · things players can pick up' }[tab]);
      lazy(grid(), list, cellTemp);
    }
  } else if (mode === 'npcs') {
    w.innerHTML = '<div class="empty">Loading…</div>';
    api('/api/chars').then(list => {
      if (mode !== 'npcs') return;
      list = list.filter(c => !q || c[1].toLowerCase().includes(q) || String(c[4]) === q);
      list.sort((a, b) => b[5] - a[5] || a[1].localeCompare(b[1]));
      const box = document.createElement('div'); box.className = 'list'; w.innerHTML = ''; w.appendChild(box);
      const s = document.createElement('div'); s.className = 'sect'; s.style.padding = '2px 2px 8px'; s.textContent = `${list.length} in the world · click to go there`; box.appendChild(s);
      lazy(box, list, c => {
        const r = document.createElement('div'); r.className = 'row';
        r.appendChild(thumb(c[6], 34));
        const d = document.createElement('div'); d.innerHTML = '<div></div><div class="n"></div>';
        d.firstChild.textContent = c[1]; d.lastChild.textContent = `${c[5] ? (c[7] ? 'player · online' : 'player · offline') : 'template ' + c[4]} · ${c[2]}, ${c[3]}`;
        r.appendChild(d); r.onclick = () => { centerOn(c[2], c[3]); selectTile(c[2], c[3]); };
        return r;
      });
    });
  } else if (mode === 'history') {
    w.innerHTML = '<div class="empty">Loading…</div>';
    api('/api/history').then(h => {
      if (mode !== 'history') return;
      const box = document.createElement('div'); box.className = 'list'; w.innerHTML = ''; w.appendChild(box);
      const s = document.createElement('div'); s.className = 'sect'; s.style.padding = '2px 2px 8px'; s.textContent = 'This session, newest first'; box.appendChild(s);
      const items = h.history.slice().reverse();
      if (!items.length) box.insertAdjacentHTML('beforeend', '<div class="empty">Nothing changed yet.</div>');
      for (const e of items) {
        const r = document.createElement('div'); r.className = 'row';
        r.innerHTML = `<div><div></div><div class="n"></div></div>`;
        r.firstChild.firstChild.textContent = e.what;
        r.querySelector('.n').textContent = e.t + (e.tiles ? ` · ${e.tiles} tile${e.tiles === 1 ? '' : 's'} · ${e.x}, ${e.y}` : '');
        if (e.tiles) r.onclick = () => centerOn(e.x, e.y);
        box.appendChild(r);
      }
      const s2 = document.createElement('div'); s2.className = 'sect'; s2.style.padding = '14px 2px 8px'; s2.textContent = 'Backups from saves'; box.appendChild(s2);
      if (!h.backups.length) box.insertAdjacentHTML('beforeend', '<div class="empty">None yet: every save keeps a copy of the files from before it.</div>');
      h.backups.slice().reverse().forEach((b, i) => {
        const r = document.createElement('div'); r.className = 'row';
        r.innerHTML = `<div><div class="mono"></div><div class="n"></div></div>`;
        r.querySelector('.mono').textContent = b.replace(/^(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d)(\d\d)$/, '$1-$2-$3 $4:$5:$6');
        r.querySelector('.n').textContent = i === 0 ? 'the world before the last save · "Undo last save" goes back to it' : 'the world before an earlier save';
        box.appendChild(r);
      });
    });
  } else if (mode === 'help') {
    w.innerHTML = `<div class="keys" style="padding:4px 2px">
      <p><b style="color:var(--gold2)">Editing</b> works while the game server is stopped. While it runs you can look around: NPCs and players are shown live.</p>
      <p><b style="color:var(--gold2)">Pick something</b> on the left (a floor, a flag, a wall, an object or an item), then paint it with the
      <b>brush</b>, a <b>rectangle</b> or <b>fill</b>. Fill covers the room you click into (up to its walls), or with a floor, the patch of the same floor.</p>
      <p><b style="color:var(--gold2)">Alt</b> paints the opposite: with a flag it clears it, with a wall/object/item it erases.</p>
      <p><b style="color:var(--gold2)">Select</b> (V) a tile to see everything on it in the right panel and change it there: floor, object, item, flags.</p>
      <p><b style="color:var(--gold2)">Save to the game</b> writes the map; the files from before are kept as a backup, and <b>Undo last save</b> puts them back. Afterwards the lighting can be recomputed with <span class="mono">./server light</span> (button in the right panel after a save).</p>
      <p><b style="color:var(--gold2)">Pentagrams</b> still need build mode in the game (they are numbered there).</p></div>`;
  }
}
$('#lsearch').oninput = () => leftUI();
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  mode = b.dataset.m; document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b)); $('#lsearch').value = ''; leftUI();
});

// ---------------------------------------------------------------- right panel
function layersUI() {
  const L = [['floors', 'Floors'], ['walls', 'Walls and objects'], ['items', 'Items'], ['chars', 'Characters'], ['see', 'See through walls (W)'], ['light', 'Light from lamps (L)'], ['grid', 'Grid (G)'], ['names', 'Area names']];
  $('#layers').innerHTML = L.map(([k, v]) => `<label class="chk"><input type="checkbox" data-l="${k}" ${show[k] ? 'checked' : ''}><span>${v}</span></label>`).join('');
  $('#layers').querySelectorAll('input').forEach(i => i.onchange = () => { show[i.dataset.l] = i.checked; toggles(); redraw(); });
  $('#flagshow').innerHTML = FLAGS.map((f, i) => `<label class="chk"><input type="checkbox" data-f="${i}" ${flagOn.has(i) ? 'checked' : ''}><span class="dot" style="background:${FCOL[i]}"></span><span>${f}</span></label>`).join('');
  $('#flagshow').querySelectorAll('input').forEach(i => i.onchange = () => { const b = +i.dataset.f; i.checked ? flagOn.add(b) : flagOn.delete(b); redraw(); });
  toggles();
}
function toggles() {
  $('#tgrid').classList.toggle('on', show.grid); $('#twalls').classList.toggle('on', show.see); $('#tlight').classList.toggle('on', show.light);
}
function flipShow(k) { show[k] = !show[k]; layersUI(); redraw(); }
$('#tgrid').onclick = () => flipShow('grid'); $('#twalls').onclick = () => flipShow('see'); $('#tlight').onclick = () => flipShow('light');
$('#tright').onclick = () => { $('#app').classList.toggle('noright'); setTimeout(resize, 0); };

async function selectTile(x, y) {
  selTile = { x, y }; redrawTop();
  const r = await api(`/api/tile?x=${x}&y=${y}`);
  if (!selTile || selTile.x !== x || selTile.y !== y) return;
  const ro = info.running;
  const el = $('#tile');
  el.innerHTML = `<div class="hd mono">${x}, ${y}</div><div>${esc(r.zone || 'no zone')}</div>
    <div class="kv">
      <span class="k">Floor</span><span class="v" id="tf"></span>
      <span class="k">Object</span><span class="v" id="to"></span>
      <span class="k">Item</span><span class="v" id="ti"></span>
      ${r.char ? '<span class="k">NPC</span><span class="v" id="tc"></span>' : ''}
      <span class="k">Light</span><span class="v">${r.light}</span>
    </div>
    <div class="flg" id="tfl"></div>`;
  const tf = $('#tf'); tf.appendChild(thumb(r.floor, 28));
  const fin = document.createElement('input'); fin.type = 'number'; fin.value = r.floor; fin.disabled = ro; fin.title = 'Type a floor sprite number';
  fin.onchange = () => edit([{ op: 'floor', x, y, s: +fin.value, set: false }], 'floor ' + fin.value, true);
  tf.appendChild(fin);
  const to = $('#to');
  if (r.object) {
    to.appendChild(thumb(r.object, 28)); to.insertAdjacentHTML('beforeend', `<span class="nm mono">${r.object}${r.flags.includes('move block') ? ' · blocks' : ''}</span>`);
    if (!ro) { const b = document.createElement('button'); b.className = 'x'; b.textContent = 'remove'; b.onclick = () => edit([{ op: 'erase', x, y }], 'erase', true); to.appendChild(b); }
  } else to.textContent = '–';
  const ti = $('#ti');
  if (r.item) {
    ti.appendChild(thumb(r.item.sprite, 28));
    const n = document.createElement('span'); n.className = 'nm'; n.textContent = r.item.name; n.title = `template ${r.item.temp} · driver ${r.item.driver}${r.item.desc ? '\n' + r.item.desc : ''}`; ti.appendChild(n);
    if (!ro) { const b = document.createElement('button'); b.className = 'x'; b.textContent = 'remove'; b.onclick = () => edit([{ op: 'erase', x, y }], 'erase', true); ti.appendChild(b); }
  } else ti.textContent = '–';
  if (r.char) { const n = document.createElement('span'); n.className = 'nm'; n.textContent = `${r.char.name} (template ${r.char.temp})`; $('#tc').appendChild(n); }
  const fl = $('#tfl');
  FLAGS.forEach((f, i) => {
    const on = r.flags.includes({ 'blocks walking': 'move block', 'blocks sight': 'sight block', 'no fighting': 'no fight' }[f] || f);
    const l = document.createElement('label'); l.className = 'chk';
    l.innerHTML = `<input type="checkbox" ${on ? 'checked' : ''} ${ro ? 'disabled' : ''}><span class="dot" style="background:${FCOL[i]}"></span><span></span>`;
    l.lastChild.textContent = f;
    l.firstChild.onchange = e => edit([{ op: 'flag', x, y, bit: i, mode: e.target.checked ? 1 : 0 }], (e.target.checked ? 'set ' : 'cleared ') + f, true);
    fl.appendChild(l);
  });
}

// ---------------------------------------------------------------- editing
function footprint(x, y) {
  const out = [], o = Math.floor((size - 1) / 2);
  for (let dy = 0; dy < size; dy++) for (let dx = 0; dx < size; dx++) out.push([x - o + dx, y - o + dy]);
  return out;
}
function opFor(x, y, alt) {
  const b = brush;
  if (tool === 'erase' || (alt && (b.kind === 'place' || b.kind === 'object'))) return { op: 'erase', x, y };
  if (b.kind === 'flag') return { op: 'flag', x, y, bit: b.bit, mode: alt ? 0 : 1 };
  if (alt) return null;
  if (b.kind === 'floor') return { op: 'floor', x, y, s: b.s, set: b.set };
  if (b.kind === 'object') return { op: 'object', x, y, s: b.s, block: b.block };
  if (b.kind === 'place') return { op: 'place', x, y, t: b.t[0] };
  return null;
}
function label(alt) {
  if (tool === 'erase') return 'erase';
  const b = brush;
  if (b.kind === 'flag') return (alt ? 'cleared ' : 'set ') + FLAGS[b.bit];
  if (alt) return 'erase';
  return b.kind === 'floor' ? 'floor ' + b.s : b.kind === 'place' ? b.t[1] : 'object ' + b.s;
}
function preview(op) {
  const t = T(op.x, op.y);
  if (!t) return;
  const d = t.d, i = t.i;
  if (op.op === 'floor') d.g[i] = op.s;
  else if (op.op === 'object') d.f[i] = op.s;
  else if (op.op === 'place') { if (brush.t && brush.t[6]) { if (!d.it[i]) { d.it[i] = brush.t[2]; d.f[i] = 0; } } else if (brush.t) d.f[i] = brush.t[2]; }
  else if (op.op === 'erase') { d.f[i] = 0; d.it[i] = 0; }
  else if (op.op === 'flag') { const b = 1 << op.bit; d.fl[i] = op.mode === 1 ? (d.fl[i] | b) : (d.fl[i] & ~b); }
  redraw();
}
async function edit(ops, lbl, reselect) {
  if (!ops.length) return;
  if (info.running) { toast('The game server is running: editing is off.', true); refetch(ops.map(o => [o.x, o.y])); return; }
  const r = await api('/api/edit', { ops, label: lbl });
  if (r.error) toast(r.error, true);
  else if (r.msgs && r.msgs.length) toast([...new Set(r.msgs)].slice(0, 3).join('\n'), true);
  Object.assign(info, { dirty: r.dirty ?? info.dirty, undo: r.undo ?? info.undo, redo: r.redo ?? info.redo }); status();
  refetch(ops.map(o => [o.x, o.y]));
  if (selTile && (reselect || ops.some(o => o.x === selTile.x && o.y === selTile.y))) selectTile(selTile.x, selTile.y);
  if (mode === 'history') leftUI();
}
async function undoRedo(w) {
  if (info.running) return;
  const r = await api('/api/' + w, {});
  if (r.error) return toast(r.error, true);
  Object.assign(info, { dirty: r.dirty, undo: r.undo, redo: r.redo }); status();
  if (r.tiles && r.tiles.length) { refetch(r.tiles); toast((w === 'undo' ? 'Undone: ' : 'Redone: ') + r.tiles.length + ' tile(s)'); if (selTile) selectTile(selTile.x, selTile.y); }
  if (mode === 'history') leftUI();
}
function fill(x, y, alt) {
  const s = T(x, y);
  if (!s) return;
  const byFloor = brush.kind === 'floor' && tool !== 'erase' && !alt;
  const g0 = s.d.g[s.i];
  const ok = (t) => {
    if (!t) return false;
    const g = t.d.g[t.i];
    if (byFloor) return g === g0;
    // a room: up to its walls and the edge of the void, and only indoors (or only outdoors) like where you clicked
    return g !== 1008 && !(t.d.fl[t.i] & 1) && ((t.d.fl[t.i] >>> 2) & 1) === in0;
  };
  const in0 = (s.d.fl[s.i] >>> 2) & 1;
  if (!ok(s)) return toast(byFloor ? 'Nothing to fill there.' : 'That tile is a wall: click inside a room.', true);
  const seen = new Set([x + ',' + y]), q = [[x, y]], ops = [];
  while (q.length) {
    const [cx, cy] = q.pop();
    const op = opFor(cx, cy, alt); if (op) ops.push(op);
    if (ops.length > 20000) return toast('That area is too big to fill (over 20000 tiles).', true);
    const here = T(cx, cy);
    if (!byFloor && here && here.d.it[here.i] && (cx !== x || cy !== y)) continue;   // a door or other item: filled, but the fill doesn't go past it
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = cx + dx, ny = cy + dy, k = nx + ',' + ny;
      if (seen.has(k)) continue; seen.add(k);
      const t = T(nx, ny);
      if (!t) { if (nx >= 0 && ny >= 0 && nx < MAPX && ny < MAPX) return toast('Part of that area is not loaded yet: zoom out a little and try again.', true); continue; }
      if (ok(t) || (!byFloor && t.d.it[t.i] && t.d.g[t.i] !== 1008)) q.push([nx, ny]);
    }
  }
  ops.forEach(preview);
  edit(ops, label(alt) + ' (fill)');
}
async function pick(x, y) {
  const r = await api(`/api/tile?x=${x}&y=${y}`);
  if (r.item) {
    const t = pal.templates.find(t => t[0] === r.item.temp);
    if (t) { setBrush({ kind: 'place', t }); toast('Picked ' + t[1]); return; }
  }
  if (r.object) { setBrush({ kind: 'object', s: r.object, block: (r.flags.includes('move block') ? 1 : 0) | (r.flags.includes('sight block') ? 2 : 0) }); toast('Picked object ' + r.object); return; }
  setBrush({ kind: 'floor', s: r.floor, set: false }); toast('Picked floor ' + r.floor);
}

// ---------------------------------------------------------------- tools
function setTool(t) {
  tool = t;
  document.querySelectorAll('#toolgrp button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
  cv.style.cursor = t === 'pan' ? 'grab' : t === 'select' ? 'default' : 'crosshair';
  redrawTop();
}
$('#toolgrp').innerHTML = TOOLS.map(([t, k, tip, path]) => `<button data-t="${t}" title="${tip} (${k})"><svg viewBox="0 0 24 24">${path}</svg></button>`).join('');
document.querySelectorAll('#toolgrp button').forEach(b => b.onclick = () => setTool(b.dataset.t));
$('#size').onchange = e => { size = +e.target.value; redrawTop(); };
function stepSize(d) {
  const o = [...$('#size').options].map(o => +o.value), i = Math.max(0, Math.min(o.length - 1, o.indexOf(size) + d));
  size = o[i]; $('#size').value = size; redrawTop();
}

// ---------------------------------------------------------------- input
function resize() {
  const r = $('#view').getBoundingClientRect();
  W = cv.width = Math.floor(r.width); H = cv.height = Math.floor(r.height); redraw();
}
window.addEventListener('resize', resize);
cv.addEventListener('contextmenu', e => e.preventDefault());
function zoomAt(f, sx, sy) {
  if (sx === undefined) { sx = W / 2; sy = H / 2; }
  const px = (sx - W / 2) / zoom + cam.x, py = (sy - H / 2) / zoom + cam.y;
  zoom = Math.min(3, Math.max(.15, zoom * f));
  cam.x = px - (sx - W / 2) / zoom; cam.y = py - (sy - H / 2) / zoom;
  $('#zv').textContent = Math.round(zoom * 100) + '%';
  redraw();
}
$('#zin').onclick = () => zoomAt(1.25); $('#zout').onclick = () => zoomAt(1 / 1.25);
cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX - r.left, e.clientY - r.top);
}, { passive: false });
cv.addEventListener('mousedown', e => {
  $('#results').style.display = 'none';
  const r = cv.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top, t = screenToTile(sx, sy);
  if (e.button === 1 || e.button === 2 || (e.button === 0 && (spaceDown || tool === 'pan'))) { panning = { sx, sy, cx: cam.x, cy: cam.y }; cv.style.cursor = 'grabbing'; e.preventDefault(); return; }
  if (e.button !== 0) return;
  if (tool === 'select') { selectTile(t.x, t.y); return; }
  if (tool === 'pick') { pick(t.x, t.y); return; }
  if (info.running) { toast('The game server is running: editing is off.', true); return; }
  if (tool === 'fill') { fill(t.x, t.y, e.altKey); return; }
  if (tool === 'rect' || e.shiftKey) { rect = { a: t, b: t, alt: e.altKey }; redrawTop(); return; }
  stroke = { ops: [], seen: new Set(), alt: e.altKey };
  paintAt(t);
});
function paintAt(t) {
  for (const [x, y] of footprint(t.x, t.y)) {
    const k = x + ',' + y;
    if (stroke.seen.has(k)) continue;
    stroke.seen.add(k);
    const op = opFor(x, y, stroke.alt);
    if (op) { stroke.ops.push(op); preview(op); }
  }
  if (!stroke.ops.length && brush.kind !== 'flag' && stroke.alt) toast('Alt with a floor does nothing: use the eraser for objects.', true);
}
window.addEventListener('mousemove', e => {
  const r = cv.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
  if (panning) { cam.x = panning.cx - (sx - panning.sx) / zoom; cam.y = panning.cy - (sy - panning.sy) / zoom; redraw(); return; }
  if (e.target !== cv && !stroke && !rect) { if (hover) { hover = null; redrawTop(); } return; }
  const t = screenToTile(sx, sy);
  if (!hover || hover.x !== t.x || hover.y !== t.y) {
    hover = t; redrawTop();
    const d = T(t.x, t.y);
    let s = `${t.x}, ${t.y}`;
    const z = info.areas.filter(a => a[0] <= t.x && t.x <= a[2] && a[1] <= t.y && t.y <= a[3]).map(a => a[4]);
    if (z.length) s += ' · ' + z[z.length - 1];
    if (d) { s += ` · floor ${d.d.g[d.i]}`; if (d.d.f[d.i]) s += ` · wall ${d.d.f[d.i]}`; if (d.d.it[d.i]) s += ' · item'; if (d.d.ch[d.i]) s += ' · NPC'; }
    $('#coords').textContent = s;
  }
  if (rect) { rect.b = t; redrawTop(); return; }
  if (stroke) paintAt(t);
});
window.addEventListener('mouseup', () => {
  if (panning) { panning = null; setTool(tool); return; }
  if (rect) {
    const x0 = Math.min(rect.a.x, rect.b.x), x1 = Math.max(rect.a.x, rect.b.x), y0 = Math.min(rect.a.y, rect.b.y), y1 = Math.max(rect.a.y, rect.b.y), alt = rect.alt;
    rect = null;
    if ((x1 - x0 + 1) * (y1 - y0 + 1) > 40000) { toast('That area is too big (at most 200×200 at once).', true); redrawTop(); return; }
    const ops = [];
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const op = opFor(x, y, alt); if (op) { ops.push(op); preview(op); } }
    edit(ops, label(alt) + ` (${x1 - x0 + 1}×${y1 - y0 + 1})`); return;
  }
  if (stroke) { const s = stroke; stroke = null; edit(s.ops, label(s.alt)); }
});
window.addEventListener('keydown', e => {
  const k = e.key.toLowerCase();
  if ((e.ctrlKey || e.metaKey) && k === 'k') { e.preventDefault(); $('#q').focus(); $('#q').select(); return; }
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
    if (k === 'escape') e.target.blur();
    return;
  }
  if (e.ctrlKey || e.metaKey) {
    if (k === 'z' && !e.shiftKey) { e.preventDefault(); undoRedo('undo'); }
    else if (k === 'y' || (k === 'z' && e.shiftKey)) { e.preventDefault(); undoRedo('redo'); }
    else if (k === 's') { e.preventDefault(); save(); }
    return;
  }
  if (k === ' ') { spaceDown = true; cv.style.cursor = 'grab'; e.preventDefault(); return; }
  if (k === 'escape') { toggleWorld(false); rect = null; selTile = null; redrawTop(); return; }
  const map = { v: 'select', b: 'brush', u: 'rect', f: 'fill', e: 'erase', i: 'pick', h: 'pan' };
  if (map[k]) return setTool(map[k]);
  if (k === '[') return stepSize(-1);
  if (k === ']') return stepSize(1);
  if (k === 'g') return flipShow('grid');
  if (k === 'w') return flipShow('see');
  if (k === 'l') return flipShow('light');
  if (k === 'm') return toggleWorld();
  const step = 160 / zoom;
  if (k === 'arrowleft') { cam.x -= step; redraw(); } else if (k === 'arrowright') { cam.x += step; redraw(); }
  else if (k === 'arrowup') { cam.y -= step; redraw(); } else if (k === 'arrowdown') { cam.y += step; redraw(); }
});
window.addEventListener('keyup', e => { if (e.key === ' ') { spaceDown = false; setTool(tool); } });
window.addEventListener('blur', () => { spaceDown = false; });

// ---------------------------------------------------------------- search
let sq = 0, sres = [], sact = 0;
$('#q').addEventListener('input', async () => {
  const q = $('#q').value, id = ++sq;
  if (!q.trim()) { $('#results').style.display = 'none'; return; }
  const r = await api('/api/search?q=' + encodeURIComponent(q));
  if (id !== sq) return;
  sres = r; sact = 0; results();
});
$('#q').addEventListener('keydown', e => {
  if (e.key === 'ArrowDown') { sact = Math.min(sres.length - 1, sact + 1); results(); e.preventDefault(); }
  else if (e.key === 'ArrowUp') { sact = Math.max(0, sact - 1); results(); e.preventDefault(); }
  else if (e.key === 'Enter' && sres[sact]) { choose(sres[sact]); }
  else if (e.key === 'Escape') { $('#results').style.display = 'none'; $('#q').blur(); }
});
$('#q').addEventListener('focus', () => { if (sres.length && $('#q').value.trim()) $('#results').style.display = 'block'; });
function results() {
  const box = $('#results'); box.innerHTML = '';
  if (!sres.length) { box.innerHTML = '<div class="r" style="cursor:default;color:var(--dim)">Nothing found.</div>'; box.style.display = 'block'; return; }
  sres.forEach((r, i) => {
    const el = document.createElement('div'); el.className = 'r' + (i === sact ? ' act' : '');
    el.innerHTML = `<span class="ty">${{ place: 'place', npc: 'NPC', player: 'player', item: 'item' }[r.type]}</span>`;
    if (r.sprite) el.appendChild(thumb(r.sprite, 30)); else { const s = document.createElement('span'); s.style.width = '30px'; el.appendChild(s); }
    const n = document.createElement('span'); n.textContent = r.name; el.appendChild(n);
    const sub = document.createElement('span'); sub.className = 'sub mono';
    sub.textContent = r.type === 'item' ? 'template ' + r.t + ' · use as brush' : `${r.x}, ${r.y}` + (r.type === 'player' ? (r.online ? ' · online' : ' · offline') : '');
    el.appendChild(sub);
    el.onmousedown = e => { e.preventDefault(); choose(r); };
    box.appendChild(el);
  });
  box.style.display = 'block';
  const a = box.querySelector('.act'); if (a) a.scrollIntoView({ block: 'nearest' });
}
function choose(r) {
  $('#results').style.display = 'none'; $('#q').blur();
  if (r.type === 'item') {
    const t = pal && pal.templates.find(t => t[0] === r.t);
    if (t) { setBrush({ kind: 'place', t }); mode = 'map'; tab = t[3] ? 'items' : cats().walls.includes(t) ? 'walls' : 'objects'; document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x.dataset.m === 'map')); $('#lsearch').value = String(t[0]); leftUI(); toast('Brush: ' + t[1]); }
    return;
  }
  centerOn(r.x, r.y); selectTile(r.x, r.y);
}
document.addEventListener('mousedown', e => { if (!$('#search').contains(e.target)) $('#results').style.display = 'none'; });

// ---------------------------------------------------------------- saving and status
async function save() {
  if (info.running) return toast('Stop the game server first.', true);
  if (!info.dirty) return toast('Nothing to save.');
  const r = await api('/api/save', {});
  if (r.error) return toast(r.error, true);
  info.dirty = r.dirty; await refreshInfo(); toast(r.msg + (r.dirty === 0 ? '\nTip: ./server light recomputes the lighting (the Relight button below).' : ''), r.dirty !== 0);
  relightBtn(r.dirty === 0);
  if (mode === 'history') leftUI();
}
$('#save').onclick = save;
$('#discard').onclick = async () => {
  if (!info.dirty) return toast('Nothing to discard.');
  if (!confirm('Throw away all unsaved changes?')) return;
  const r = await api('/api/reload', {});
  chunks.clear(); redraw(); relightBtn(false); toast('Changes discarded.'); await refreshInfo(); if (selTile) selectTile(selTile.x, selTile.y);
};
$('#undosave').onclick = async () => {
  if (info.running) return toast('Stop the game server first.', true);
  if (info.dirty) return toast('Save or discard the current changes first.', true);
  if (!confirm('Put the world back as it was before the last save? (The newer files are replaced by that backup.)')) return;
  const r = await api('/api/restore', {});
  if (r.error) return toast(r.error, true);
  chunks.clear(); redraw(); toast(r.msg); relightBtn(false); await refreshInfo();
  if (mode === 'history') leftUI();
};
$('#tref').onclick = async () => {
  if (info.dirty && !confirm('Throw away the unsaved changes and load the world from disk again?')) return;
  const r = await api('/api/reload', {}); chunks.clear(); redraw(); toast(r.msg); refreshInfo();
};
function relightBtn(on) {
  let b = $('#relight');
  if (!on) { if (b) b.remove(); return; }
  if (b) return;
  b = document.createElement('button'); b.id = 'relight'; b.className = 'btn ghost'; b.style.cssText = 'padding:0;margin:8px 0 0 14px;font-size:12px'; b.textContent = 'Relight the world'; b.title = 'Recompute the lighting of the whole world (./server light)';
  b.onclick = async () => {
    if (!confirm('Recompute the lighting of the whole world? It takes a minute or two.')) return;
    toast('Relighting… a minute or two.');
    const r = await api('/api/relight', {});
    if (r.error) return toast(r.error, true);
    chunks.clear(); redraw(); toast(r.msg); b.remove(); refreshInfo();
  };
  $('#undosave').insertAdjacentElement('afterend', b);
}
function status() {
  const p = $('#pill');
  p.className = info.running ? 'up' : 'down';
  p.textContent = info.running ? `Server up · ${info.online} online` : 'Server stopped · editing on';
  $('#banner').style.display = info.running ? 'block' : 'none';
  const d = $('#dirty');
  d.textContent = info.running ? 'View only while the server runs' : info.dirty ? `${info.dirty} unsaved change${info.dirty === 1 ? '' : 's'}` : 'No unsaved changes';
  d.classList.toggle('on', !!info.dirty);
  $('#save').disabled = info.running || !info.dirty;
  $('#discard').disabled = !info.dirty;
  $('#undo').disabled = info.running || !info.undo;
  $('#redo').disabled = info.running || !info.redo;
  $('#undosave').disabled = info.running || !!info.dirty || !info.backups;
}
async function refreshInfo() {
  const r = await api('/api/info');
  const first = !info.areas.length, gen = info.gen;
  Object.assign(info, r); status();
  if (gen && r.gen !== gen) { chunks.clear(); redraw(); if (selTile) selectTile(selTile.x, selTile.y); }
  if (r.minimap && !miniOk && !mini.src) { mini.onload = () => { miniOk = true; $('#mini').style.display = 'block'; redraw(); }; mini.src = '/minimap.png'; }
  if (first) redraw();
}

// ---------------------------------------------------------------- start
(async function start() {
  resize();
  layersUI(); setTool('brush'); leftUI();
  await refreshInfo();
  pal = await api('/api/palette');
  card(); leftUI();
  const m = location.hash.match(/(\d+),(\d+)/);
  if (m) centerOn(+m[1], +m[2]); else centerOn(512, 512);
  setInterval(refreshInfo, 4000);
  setInterval(() => { const c = screenToTile(W / 2, H / 2); history.replaceState(null, '', '#' + c.x + ',' + c.y); }, 1000);
  loop();
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main()
