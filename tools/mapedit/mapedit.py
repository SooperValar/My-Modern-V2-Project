#!/usr/bin/env python3
"""Mercenaries of Astonia v2 - map editor in the browser.

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
        g, f, fl, it, ch = [], [], [], [], []
        with self.lock:
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    s, fs, c, _, i, _, _, flags = struct.unpack_from(MAP_FMT, self.map, (x + y * MAPX) * MAP_SIZE)
                    g.append(s); f.append(fs); fl.append(flags & 0xffffffff)
                    it.append(self.item_sprite(i) if 0 < i < MAXITEM and self.it_u8(i, I_USED) else 0)
                    ch.append(self.char_sprite(c) if 0 < c < MAXCHARS and self.char[c * CHAR_SIZE + C_USED] else 0)
        return {'x0': x0, 'y0': y0, 'w': x1 - x0 + 1, 'h': y1 - y0 + 1, 'g': g, 'f': f, 'fl': fl, 'it': it, 'ch': ch}

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

    def apply(self, ops):
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
            return 'Saved. Backup of the old files: ' + bk


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
            if u.path == '/minimap.png':
                if minimap and os.path.exists(minimap):
                    return self.send(200, 'image/png', open(minimap, 'rb').read(), True)
                return self.send(404, 'text/plain', b'none')
            if u.path == '/api/info':
                return self.js({'running': server_running(), 'dirty': world.dirty, 'undo': len(world.undo),
                                'redo': len(world.redo), 'areas': world.areas, 'minimap': bool(minimap and os.path.exists(minimap)),
                                'dat': os.path.abspath(world.dat)})
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
            if u.path in ('/api/edit', '/api/undo', '/api/redo', '/api/save', '/api/relight') and server_running():
                return self.js({'error': 'The game server is running: the map is view-only. Stop the server to edit.'})
            if u.path == '/api/edit':
                changed, msgs = world.apply(body.get('ops', []))
                return self.js({'changed': changed, 'msgs': msgs, 'dirty': world.dirty, 'undo': len(world.undo), 'redo': len(world.redo)})
            if u.path in ('/api/undo', '/api/redo'):
                tiles = world.undo_redo(u.path[5:])
                return self.js({'tiles': tiles, 'dirty': world.dirty, 'undo': len(world.undo), 'redo': len(world.redo)})
            if u.path == '/api/save':
                return self.js({'msg': world.save(), 'dirty': world.dirty})
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
    ap = argparse.ArgumentParser(description='Astonia v2 map editor (browser)')
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
    print('Map editor: open http://localhost:%d in your browser.%s Ctrl+C to quit.' %
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
<title>Astonia Map Editor</title>
<style>
:root {
  --bg: #16171a; --panel: #1f2024; --panel2: #26282d; --line: #34363c; --text: #e4e2dc; --dim: #9a978f;
  --accent: #d9a441; --accent2: #6aa7e8; --bad: #e0675a; --good: #6cc070;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); font: 13px/1.4 system-ui, Segoe UI, sans-serif; overflow: hidden; }
button, input, select { font: inherit; color: var(--text); background: var(--panel2); border: 1px solid var(--line); border-radius: 4px; padding: 3px 8px; }
button { cursor: pointer; }
button:hover:not(:disabled) { border-color: var(--accent); }
button:disabled { opacity: .4; cursor: default; }
button.on { background: #3a3220; border-color: var(--accent); color: #fff; }
input[type=checkbox] { padding: 0; }
#top { position: absolute; left: 0; right: 0; top: 0; height: 40px; display: flex; gap: 6px; align-items: center; padding: 0 10px; background: var(--panel); border-bottom: 1px solid var(--line); white-space: nowrap; overflow-x: auto; }
#top .title { font-weight: 600; color: var(--accent); margin-right: 6px; }
#top .sep { width: 1px; height: 22px; background: var(--line); margin: 0 4px; }
#status { margin-left: auto; color: var(--dim); }
#banner { position: absolute; left: 300px; right: 0; top: 40px; padding: 6px 12px; background: #4a2723; color: #ffd9d3; display: none; z-index: 2; }
#side { position: absolute; left: 0; top: 40px; bottom: 0; width: 300px; background: var(--panel); border-right: 1px solid var(--line); display: flex; flex-direction: column; }
#tools { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; padding: 8px; border-bottom: 1px solid var(--line); }
#tools button { padding: 5px 2px; font-size: 12px; }
#opts { padding: 8px; border-bottom: 1px solid var(--line); display: flex; flex-direction: column; gap: 6px; }
#opts label { display: flex; gap: 6px; align-items: center; color: var(--dim); }
#pal { flex: 1; overflow-y: auto; padding: 6px 8px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, 52px); gap: 4px; }
.cell { width: 52px; height: 60px; background: var(--panel2); border: 1px solid var(--line); border-radius: 4px; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; font-size: 10px; color: var(--dim); overflow: hidden; }
.cell.sel { border-color: var(--accent); background: #3a3220; color: #fff; }
.cell canvas { width: 44px; height: 44px; }
.row { display: flex; gap: 8px; align-items: center; padding: 3px 4px; border-radius: 4px; cursor: pointer; border: 1px solid transparent; }
.row:hover { background: var(--panel2); }
.row.sel { border-color: var(--accent); background: #3a3220; }
.row canvas { width: 36px; height: 36px; flex: none; }
.row .n { color: var(--dim); font-size: 11px; }
#info { border-top: 1px solid var(--line); padding: 8px; font-size: 12px; max-height: 32%; overflow-y: auto; }
#info b { color: var(--accent); font-weight: 600; }
#info .k { color: var(--dim); }
#mini { border-top: 1px solid var(--line); padding: 8px; display: none; }
#mini canvas { width: 284px; height: 284px; image-rendering: pixelated; cursor: crosshair; border: 1px solid var(--line); }
#view { position: absolute; left: 300px; right: 0; top: 40px; bottom: 0; }
#cv { width: 100%; height: 100%; display: block; background: #050506; }
#hover { position: absolute; left: 310px; bottom: 8px; background: rgba(20,20,24,.85); padding: 4px 8px; border-radius: 4px; color: var(--dim); pointer-events: none; }
#toast { position: absolute; right: 12px; bottom: 12px; max-width: 460px; background: var(--panel2); border: 1px solid var(--line); border-left: 3px solid var(--accent); padding: 8px 12px; border-radius: 4px; display: none; z-index: 5; }
.help { color: var(--dim); font-size: 11px; line-height: 1.5; }
kbd { background: var(--panel2); border: 1px solid var(--line); border-radius: 3px; padding: 0 4px; font-size: 11px; }
</style>
</head>
<body>
<div id="top">
  <span class="title">Astonia Map Editor</span>
  <input id="goto" size="9" placeholder="x y" title="Go to a map position (x y)">
  <button id="gobtn">Go</button>
  <select id="zones" title="Go to a zone"><option value="">Zones…</option></select>
  <span class="sep"></span>
  <label title="Tile outlines"><input type="checkbox" id="grid"> Grid</label>
  <select id="ovl" title="Show a tile flag"><option value="-1">Show flag…</option></select>
  <label title="Draw NPCs and players"><input type="checkbox" id="shownpc" checked> NPCs</label>
  <span class="sep"></span>
  <button id="undo" title="Ctrl+Z">Undo</button>
  <button id="redo" title="Ctrl+Y">Redo</button>
  <button id="save" title="Ctrl+S: write map.dat and item.dat (a backup is made first)">Save</button>
  <button id="relight" title="After saving: recompute the lighting (./server light)">Relight</button>
  <button id="reload" title="Load the world again from disk (unsaved changes are lost)">Reload</button>
  <span id="status"></span>
</div>
<div id="banner">The game server is running: the map is view-only. Stop the server to edit.</div>
<div id="side">
  <div id="tools">
    <button data-t="inspect" title="1: look at a tile">Look</button>
    <button data-t="floor" title="2: paint floor">Floor</button>
    <button data-t="place" title="3: place walls, objects, items">Place</button>
    <button data-t="erase" title="4: remove objects and items (floor stays)">Erase</button>
    <button data-t="flag" title="5: tile flags">Flags</button>
  </div>
  <div id="opts"></div>
  <div id="pal"></div>
  <div id="info"><div class="help">
    <b>Mouse</b>: left = use the tool (drag to paint, <kbd>Shift</kbd>+drag for a rectangle), right-click = pick up what's on a tile,
    wheel = zoom, middle-drag or <kbd>Space</kbd>+drag = move. <kbd>Arrows</kbd>/<kbd>WASD</kbd> move too.<br>
    <b>Keys</b>: <kbd>1</kbd>-<kbd>5</kbd> tools, <kbd>Ctrl+Z</kbd>/<kbd>Ctrl+Y</kbd> undo/redo, <kbd>Ctrl+S</kbd> save, <kbd>G</kbd> grid.
  </div></div>
  <div id="mini"><canvas id="mcv" width="1024" height="1024" title="Click to go there"></canvas></div>
</div>
<div id="view"><canvas id="cv"></canvas></div>
<div id="hover"></div>
<div id="toast"></div>

<script>
'use strict';
const MAPX = 1024, CH = 32;
const $ = s => document.querySelector(s);
const cv = $('#cv'), ctx = cv.getContext('2d');
let W = 0, H = 0;
let cam = { x: 0, y: 0 }, zoom = 1;
let tool = 'inspect';
let info = { running: false, dirty: 0, undo: 0, redo: 0, areas: [] };
let pal = null;
const brush = { floors: [142], floorSet: true, place: null, replace: false, raw: null, rawBlock: 3, flag: 2, flagMode: 1 };
const chunks = new Map();
const sprites = new Map();
let hover = null, stroke = null, rect = null, panning = null, spaceDown = false, needDraw = true, baseDirty = true;
const base = document.createElement('canvas'), bctx = base.getContext('2d');   // the map; hover and selection go on top

// ---------------------------------------------------------------- helpers
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  return r.json();
}
let toastT = 0;
function toast(msg, bad) {
  const t = $('#toast'); t.textContent = msg; t.style.display = 'block';
  t.style.borderLeftColor = bad ? 'var(--bad)' : 'var(--accent)';
  clearTimeout(toastT); toastT = setTimeout(() => t.style.display = 'none', bad ? 7000 : 4000);
}
const wx = (x, y) => 16 * (x + y), wy = (x, y) => 8 * (x - y);
function screenToTile(sx, sy) {
  const px = (sx - W / 2) / zoom + cam.x, py = (sy - H / 2) / zoom + cam.y;
  const u = (px - 32) / 16, v = (py - 56) / 8;
  return { x: Math.round((u + v) / 2), y: Math.round((u - v) / 2) };
}
function centerOn(x, y) { cam.x = wx(x, y) + 32; cam.y = wy(x, y) + 56; redraw(); }
function redraw() { needDraw = true; baseDirty = true; }
function redrawTop() { needDraw = true; }

// ---------------------------------------------------------------- sprites
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
      for (let i = 0; i < a.length; i += 4) if (a[i] > 240 && a[i + 1] < 16 && a[i + 2] > 240) a[i + 3] = 0;   // the game's magenta = see-through
      g.putImageData(d, 0, 0);
    } catch (e) {}
    s.img = c; redraw(); thumbsDirty(n);
  };
  im.src = '/sprite/' + n;
  return null;
}

// ---------------------------------------------------------------- map data (32x32 chunks)
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
    const k = Math.floor(x / CH) + ',' + Math.floor(y / CH);
    if (seen.has(k)) continue; seen.add(k);
    const old = chunks.get(k);
    const c = { data: old ? old.data : null }; chunks.set(k, c);
    const cx = Math.floor(x / CH), cy = Math.floor(y / CH);
    api(`/api/region?x0=${cx * CH}&y0=${cy * CH}&x1=${cx * CH + CH - 1}&y1=${cy * CH + CH - 1}`).then(d => { c.data = d; redraw(); });
  }
}
function T(x, y) {
  if (x < 0 || y < 0 || x >= MAPX || y >= MAPX) return null;
  const d = chunk(Math.floor(x / CH), Math.floor(y / CH));
  if (!d) return null;
  const i = (y - d.y0) * d.w + (x - d.x0);
  return { d, i };
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
let g2 = ctx;   // what draw() paints on
function put(n, x, y) {
  const im = sprite(n);
  if (!im) return;
  g2.drawImage(im, wx(x, y) - im.width / 2 + 32, wy(x, y) - im.height + 64);
}
function diamond(x, y, c) {
  c = c || g2;
  const cx = wx(x, y) + 32, cy = wy(x, y) + 56;
  c.beginPath(); c.moveTo(cx - 16, cy); c.lineTo(cx, cy - 8); c.lineTo(cx + 16, cy); c.lineTo(cx, cy + 8); c.closePath();
}
function inRect(x, y) {
  if (!rect) return false;
  return x >= Math.min(rect.a.x, rect.b.x) && x <= Math.max(rect.a.x, rect.b.x) && y >= Math.min(rect.a.y, rect.b.y) && y <= Math.max(rect.a.y, rect.b.y);
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
    const npc = $('#shownpc').checked && zoom >= .35, ovl = +$('#ovl').value, grid = $('#grid').checked;
    // floors
    for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
      const t = T(x, y);
      if (!t) continue;
      const g = t.d.g[t.i];
      if (g && g !== 1008) put(g, x, y);
    }
    // flag overlay and grid, on the floor
    if (ovl >= 0 || grid) {
      g2.lineWidth = 1 / zoom;
      for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
        const t = T(x, y);
        if (!t) continue;
        if (ovl >= 0 && (t.d.fl[t.i] >>> ovl) & 1) { diamond(x, y); g2.fillStyle = 'rgba(80,170,255,.42)'; g2.fill(); }
        if (grid && zoom >= .5) { diamond(x, y); g2.strokeStyle = 'rgba(255,255,255,.12)'; g2.stroke(); }
      }
    }
    // objects, items, characters: back to front like the game
    for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
      const t = T(x, y);
      if (!t) continue;
      const d = t.d, i = t.i;
      if (d.f[i]) put(d.f[i], x, y);
      if (d.it[i]) put(d.it[i], x, y);
      if (npc && d.ch[i]) put(d.ch[i], x, y);
    }
    drawMini(v);
  }
  // on top: the map, then the selection and the tile under the mouse
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.drawImage(base, 0, 0);
  ctx.setTransform(zoom, 0, 0, zoom, W / 2 - cam.x * zoom, H / 2 - cam.y * zoom);
  if (rect) {
    ctx.fillStyle = 'rgba(217,164,65,.35)';
    for (let y = Math.min(rect.a.y, rect.b.y); y <= Math.max(rect.a.y, rect.b.y); y++)
      for (let x = Math.min(rect.a.x, rect.b.x); x <= Math.max(rect.a.x, rect.b.x); x++) { diamond(x, y, ctx); ctx.fill(); }
  }
  if (hover) {
    diamond(hover.x, hover.y, ctx);
    ctx.lineWidth = 2 / zoom; ctx.strokeStyle = '#ffd36a'; ctx.stroke();
  }
}
function loop() { if (needDraw) draw(); requestAnimationFrame(loop); }

// ---------------------------------------------------------------- minimap
const mini = new Image(); let miniOk = false;
function drawMini(v) {
  if (!miniOk) return;
  const m = $('#mcv'), g = m.getContext('2d');
  g.drawImage(mini, 0, 0, 1024, 1024);
  // minimap: column = map y, row = map x
  const c = screenToTile(W / 2, H / 2);
  g.strokeStyle = '#ffd36a'; g.lineWidth = 6;
  g.strokeRect(v.y0, v.x0, Math.max(8, v.y1 - v.y0), Math.max(8, v.x1 - v.x0));
  g.fillStyle = '#ffd36a'; g.fillRect(c.y - 6, c.x - 6, 12, 12);
}
$('#mcv').addEventListener('click', e => {
  const r = e.target.getBoundingClientRect();
  const col = Math.floor((e.clientX - r.left) / r.width * 1024), row = Math.floor((e.clientY - r.top) / r.height * 1024);
  centerOn(row, col);
});

// ---------------------------------------------------------------- tools and palette
const thumbWait = new Map();
function thumb(n, size) {
  const c = document.createElement('canvas'); c.width = size; c.height = size; c.dataset.spr = n;
  paintThumb(c);
  return c;
}
function paintThumb(c) {
  const n = +c.dataset.spr, im = sprite(n), g = c.getContext('2d');
  g.clearRect(0, 0, c.width, c.height);
  if (!im) { if (!thumbWait.has(n)) thumbWait.set(n, []); thumbWait.get(n).push(c); return; }
  const s = Math.min(c.width / im.width, c.height / im.height, 1.5);
  g.imageSmoothingEnabled = false;
  g.drawImage(im, (c.width - im.width * s) / 2, c.height - im.height * s, im.width * s, im.height * s);
}
function thumbsDirty(n) {
  const l = thumbWait.get(n);
  if (!l) return;
  thumbWait.delete(n);
  for (const c of l) paintThumb(c);
}
function lazyList(container, items, make) {   // builds rows as they scroll into view
  container.innerHTML = '';
  let shown = 0;
  const more = () => {
    const end = Math.min(items.length, shown + 120);
    for (; shown < end; shown++) container.appendChild(make(items[shown]));
    if (shown < items.length) {
      const s = document.createElement('div'); s.style.height = '20px'; container.appendChild(s);
      const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { io.disconnect(); s.remove(); more(); } }, { root: $('#pal') });
      io.observe(s);
    }
  };
  more();
}

function setTool(t) {
  tool = t;
  document.querySelectorAll('#tools button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
  buildOpts();
  cv.style.cursor = t === 'inspect' ? 'default' : 'crosshair';
}
function buildOpts() {
  const o = $('#opts'), p = $('#pal');
  o.innerHTML = ''; p.innerHTML = '';
  if (!pal) { p.textContent = 'Loading…'; return; }
  if (tool === 'inspect') {
    o.innerHTML = '<div class="help">Click a tile to see everything on it: floor and object sprites, flags, the item and NPC with their template numbers, the zone.</div>';
  } else if (tool === 'floor') {
    o.innerHTML = `<label><input type="checkbox" id="fset" ${brush.floorSet ? 'checked' : ''}> Random variants (like build mode, e.g. 142 paints 142-145)</label>
      <input id="fsearch" placeholder="Find a floor sprite number">
      <div class="help">Click a floor to paint with it; <kbd>Ctrl</kbd>+click several to paint a random mix. Sorted by how often they're used.</div>`;
    $('#fset').onchange = e => brush.floorSet = e.target.checked;
    const g = document.createElement('div'); g.className = 'grid'; p.appendChild(g);
    const fill = () => {
      const q = $('#fsearch').value.trim();
      const list = pal.floors.filter(([s]) => !q || String(s).startsWith(q));
      if (q && /^\d+$/.test(q) && !list.some(([s]) => String(s) === q)) list.unshift([+q, 0]);
      lazyList(g, list, ([s, n]) => {
        const c = document.createElement('div'); c.className = 'cell' + (brush.floors.includes(s) ? ' sel' : '');
        c.title = `floor ${s}` + (n ? `, on ${n} tiles` : '');
        c.appendChild(thumb(s, 44)); c.append(String(s));
        c.onclick = e => {
          if (e.ctrlKey || e.metaKey) { const i = brush.floors.indexOf(s); if (i >= 0 && brush.floors.length > 1) brush.floors.splice(i, 1); else if (i < 0) brush.floors.push(s); }
          else brush.floors = [s];
          g.querySelectorAll('.cell').forEach(el => el.classList.toggle('sel', brush.floors.includes(+el.textContent)));
        };
        return c;
      });
    };
    $('#fsearch').oninput = fill; fill();
  } else if (tool === 'place') {
    o.innerHTML = `<input id="tsearch" placeholder="Find by name or template number">
      <label><input type="checkbox" id="tfix" checked> Only things that can't be picked up (walls, furniture, doors…)</label>
      <label><input type="checkbox" id="trep" ${brush.replace ? 'checked' : ''}> Replace an item already on the tile</label>
      <div id="rawbox"></div>`;
    $('#trep').onchange = e => brush.replace = e.target.checked;
    const box = document.createElement('div'); p.appendChild(box);
    const fill = () => {
      const q = $('#tsearch').value.trim().toLowerCase(), fix = $('#tfix').checked;
      const list = pal.templates.filter(t => (!fix || !t[3]) && (!q || t[1].toLowerCase().includes(q) || String(t[0]) === q));
      lazyList(box, list, t => {
        const r = document.createElement('div'); r.className = 'row' + (brush.place && brush.place[0] === t[0] ? ' sel' : '');
        r.appendChild(thumb(t[2], 36));
        const s = document.createElement('div');
        s.innerHTML = `<div></div><div class="n">#${t[0]} · ${t[6] ? 'item' : 'drawn into the tile'}${t[5] & 1 ? ' · blocks walking' : ''}${t[5] & 2 ? ' · blocks sight' : ''}</div>`;
        s.firstChild.textContent = t[1];
        r.appendChild(s);
        r.onclick = () => { brush.place = t; brush.raw = null; box.querySelectorAll('.row').forEach(el => el.classList.remove('sel')); r.classList.add('sel'); showRaw(); };
        return r;
      });
    };
    $('#tsearch').oninput = fill; $('#tfix').onchange = fill; fill();
    showRaw();
  } else if (tool === 'erase') {
    o.innerHTML = '<div class="help">Removes the object (wall, table…) and the item on a tile; the floor stays. Drag, or <kbd>Shift</kbd>+drag for an area.</div>';
  } else if (tool === 'flag') {
    o.innerHTML = `<select id="fbit">${pal.flags.map((f, i) => `<option value="${i}" ${i === brush.flag ? 'selected' : ''}>${f}</option>`).join('')}</select>
      <div><label style="display:inline-flex"><input type="radio" name="fm" value="1" ${brush.flagMode === 1 ? 'checked' : ''}> Set</label>
      <label style="display:inline-flex"><input type="radio" name="fm" value="0" ${brush.flagMode === 0 ? 'checked' : ''}> Clear</label>
      <label style="display:inline-flex"><input type="radio" name="fm" value="2" ${brush.flagMode === 2 ? 'checked' : ''}> Toggle</label></div>
      <div class="help">The tiles with this flag are shown in blue.</div>`;
    $('#fbit').onchange = e => { brush.flag = +e.target.value; $('#ovl').value = brush.flag; redraw(); };
    document.querySelectorAll('input[name=fm]').forEach(r => r.onchange = e => brush.flagMode = +e.target.value);
    $('#ovl').value = brush.flag; redraw();
  }
}
function showRaw() {
  const b = $('#rawbox');
  if (!b) return;
  if (!brush.raw) { b.innerHTML = ''; return; }
  b.innerHTML = `<div class="row sel"><span></span><div>Picked object sprite ${brush.raw}<div class="n">
    <label style="display:inline-flex"><input type="checkbox" id="rb1" ${brush.rawBlock & 1 ? 'checked' : ''}> blocks walking</label>
    <label style="display:inline-flex"><input type="checkbox" id="rb2" ${brush.rawBlock & 2 ? 'checked' : ''}> blocks sight</label></div></div></div>`;
  b.querySelector('span').replaceWith(thumb(brush.raw, 36));
  $('#rb1').onchange = e => brush.rawBlock = (brush.rawBlock & ~1) | (e.target.checked ? 1 : 0);
  $('#rb2').onchange = e => brush.rawBlock = (brush.rawBlock & ~2) | (e.target.checked ? 2 : 0);
}

// ---------------------------------------------------------------- editing
function opFor(x, y) {
  if (tool === 'floor') return { op: 'floor', x, y, s: brush.floors[Math.floor(Math.random() * brush.floors.length)], set: brush.floorSet };
  if (tool === 'place') {
    if (brush.raw) return { op: 'object', x, y, s: brush.raw, block: brush.rawBlock };
    if (brush.place) return { op: 'place', x, y, t: brush.place[0], replace: brush.replace };
    return null;
  }
  if (tool === 'erase') return { op: 'erase', x, y };
  if (tool === 'flag') return { op: 'flag', x, y, bit: brush.flag, mode: brush.flagMode };
  return null;
}
function preview(op) {   // show it right away; the server's answer replaces it
  const t = T(op.x, op.y);
  if (!t) return;
  const d = t.d, i = t.i;
  if (op.op === 'floor') d.g[i] = op.s;
  else if (op.op === 'object') d.f[i] = op.s;
  else if (op.op === 'place') { if (brush.place[6]) { if (!d.it[i] || op.replace) { d.it[i] = brush.place[2]; d.f[i] = 0; } } else d.f[i] = brush.place[2]; }
  else if (op.op === 'erase') { d.f[i] = 0; d.it[i] = 0; }
  else if (op.op === 'flag') { const b = 1 << op.bit; d.fl[i] = op.mode === 1 ? (d.fl[i] | b) : op.mode === 0 ? (d.fl[i] & ~b) : (d.fl[i] ^ b); }
  redraw();
}
async function send(ops) {
  if (!ops.length) return;
  if (info.running) { toast('The game server is running: view only.', true); refetch(ops.map(o => [o.x, o.y])); return; }
  const r = await api('/api/edit', { ops });
  if (r.error) toast(r.error, true);
  else if (r.msgs && r.msgs.length) toast(r.msgs.slice(0, 3).join('\n') + (r.msgs.length > 3 ? ` (+${r.msgs.length - 3} more)` : ''), true);
  Object.assign(info, { dirty: r.dirty ?? info.dirty, undo: r.undo ?? info.undo, redo: r.redo ?? info.redo });
  status();
  refetch(ops.map(o => [o.x, o.y]));
}
async function undoRedo(w) {
  const r = await api('/api/' + w, {});
  if (r.error) return toast(r.error, true);
  Object.assign(info, { dirty: r.dirty, undo: r.undo, redo: r.redo }); status();
  if (r.tiles && r.tiles.length) { refetch(r.tiles); toast((w === 'undo' ? 'Undone: ' : 'Redone: ') + r.tiles.length + ' tile(s)'); }
}
async function inspect(x, y) {
  const r = await api(`/api/tile?x=${x}&y=${y}`);
  const e = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  let h = `<b>${x}, ${y}</b> ${r.zone ? '· ' + e(r.zone) : ''}<br>`;
  h += `<span class="k">floor</span> ${r.floor} &nbsp; <span class="k">object</span> ${r.object || '-'} &nbsp; <span class="k">light</span> ${r.light}<br>`;
  h += `<span class="k">flags</span> ${r.flags.length ? e(r.flags.join(', ')) : '-'}<br>`;
  if (r.item) h += `<span class="k">item</span> ${e(r.item.name)} <span class="k">(template ${r.item.temp}, driver ${r.item.driver}, #${r.item.index})</span><br>` +
                   (r.item.desc ? `<span class="k">${e(r.item.desc)}</span><br>` : '') +
                   (r.item.driver ? `<span class="k">data ${r.item.data.join(' ')}</span><br>` : '');
  if (r.char) h += `<span class="k">character</span> ${e(r.char.name)} <span class="k">(template ${r.char.temp}, #${r.char.index})</span><br>`;
  $('#info').innerHTML = h;
}
async function pick(x, y) {   // right-click: take what's on the tile into the tool
  const r = await api(`/api/tile?x=${x}&y=${y}`);
  if (tool === 'floor' || tool === 'inspect' || tool === 'erase' || tool === 'flag') {
    if (tool !== 'flag') { brush.floors = [r.floor]; setTool('floor'); toast('Floor ' + r.floor + ' picked'); }
    return;
  }
  if (tool === 'place') {
    if (r.item) {
      const t = pal.templates.find(t => t[0] === r.item.temp);
      if (t) { brush.place = t; brush.raw = null; setTool('place'); $('#tsearch').value = String(t[0]); $('#tfix').checked = false; $('#tsearch').oninput(); toast('Picked ' + t[1]); return; }
    }
    if (r.object) {
      brush.raw = r.object; brush.rawBlock = (r.flags.includes('move block') ? 1 : 0) | (r.flags.includes('sight block') ? 2 : 0);
      showRaw(); toast('Picked object sprite ' + r.object); return;
    }
    toast('Nothing to pick on that tile');
  }
}

// ---------------------------------------------------------------- input
function resize() {
  const r = $('#view').getBoundingClientRect();
  W = cv.width = Math.floor(r.width); H = cv.height = Math.floor(r.height); redraw();
}
window.addEventListener('resize', resize);
cv.addEventListener('contextmenu', e => e.preventDefault());
cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
  const px = (sx - W / 2) / zoom + cam.x, py = (sy - H / 2) / zoom + cam.y;
  zoom = Math.min(3, Math.max(.2, zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
  cam.x = px - (sx - W / 2) / zoom; cam.y = py - (sy - H / 2) / zoom;
  redraw();
}, { passive: false });
cv.addEventListener('mousedown', e => {
  const r = cv.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
  const t = screenToTile(sx, sy);
  if (e.button === 1 || (e.button === 0 && spaceDown)) { panning = { sx, sy, cx: cam.x, cy: cam.y }; e.preventDefault(); return; }
  if (e.button === 2) { pick(t.x, t.y); return; }
  if (e.button !== 0) return;
  if (tool === 'inspect') { inspect(t.x, t.y); panning = { sx, sy, cx: cam.x, cy: cam.y, click: true }; return; }
  if (info.running) { toast('The game server is running: the map is view-only.', true); return; }
  if (e.shiftKey) { rect = { a: t, b: t }; redrawTop(); return; }
  const op = opFor(t.x, t.y);
  if (!op) { toast(tool === 'place' ? 'Pick something to place first (list on the left)' : 'Nothing to paint', true); return; }
  stroke = { ops: [op], seen: new Set([t.x + ',' + t.y]) };
  preview(op);
});
window.addEventListener('mousemove', e => {
  const r = cv.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
  if (panning) { cam.x = panning.cx - (sx - panning.sx) / zoom; cam.y = panning.cy - (sy - panning.sy) / zoom; redraw(); return; }
  if (e.target !== cv && !stroke && !rect) return;
  const t = screenToTile(sx, sy);
  if (!hover || hover.x !== t.x || hover.y !== t.y) {
    hover = t; redrawTop();
    const d = T(t.x, t.y);
    let s = `${t.x}, ${t.y}`;
    if (d) { s += ` · floor ${d.d.g[d.i]}`; if (d.d.f[d.i]) s += ` · object ${d.d.f[d.i]}`; if (d.d.it[d.i]) s += ` · item`; if (d.d.ch[d.i]) s += ` · NPC`; }
    $('#hover').textContent = s;
  }
  if (rect) { rect.b = t; redrawTop(); return; }
  if (stroke && !stroke.seen.has(t.x + ',' + t.y)) {
    stroke.seen.add(t.x + ',' + t.y);
    const op = opFor(t.x, t.y);
    if (op) { stroke.ops.push(op); preview(op); }
  }
});
window.addEventListener('mouseup', e => {
  if (panning) { panning = null; return; }
  if (rect) {
    const x0 = Math.min(rect.a.x, rect.b.x), x1 = Math.max(rect.a.x, rect.b.x), y0 = Math.min(rect.a.y, rect.b.y), y1 = Math.max(rect.a.y, rect.b.y);
    rect = null;
    if ((x1 - x0 + 1) * (y1 - y0 + 1) > 40000) { toast('That area is too big (at most 200x200 at once).', true); redraw(); return; }
    const ops = [];
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const op = opFor(x, y); if (op) { ops.push(op); preview(op); } }
    send(ops); return;
  }
  if (stroke) { const s = stroke; stroke = null; send(s.ops); }
});
window.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') { if (e.key === 'Enter' && e.target.id === 'goto') go(); return; }
  const k = e.key.toLowerCase();
  if (e.ctrlKey || e.metaKey) {
    if (k === 'z' && !e.shiftKey) { e.preventDefault(); undoRedo('undo'); }
    else if (k === 'y' || (k === 'z' && e.shiftKey)) { e.preventDefault(); undoRedo('redo'); }
    else if (k === 's') { e.preventDefault(); save(); }
    return;
  }
  if (k === ' ') { spaceDown = true; e.preventDefault(); return; }
  const step = 160 / zoom;
  if (k === 'arrowleft' || k === 'a') { cam.x -= step; redraw(); }
  else if (k === 'arrowright' || k === 'd') { cam.x += step; redraw(); }
  else if (k === 'arrowup' || k === 'w') { cam.y -= step; redraw(); }
  else if (k === 'arrowdown' || k === 's') { cam.y += step; redraw(); }
  else if (k === 'g') { $('#grid').checked = !$('#grid').checked; redraw(); }
  else if ('12345'.includes(k)) setTool(['inspect', 'floor', 'place', 'erase', 'flag'][+k - 1]);
});
window.addEventListener('keyup', e => { if (e.key === ' ') spaceDown = false; });

// ---------------------------------------------------------------- top bar
function go() {
  const m = $('#goto').value.match(/(\d+)\D+(\d+)/);
  if (!m) return toast('Type a position like 512 512', true);
  centerOn(+m[1], +m[2]);
}
$('#gobtn').onclick = go;
$('#zones').onchange = e => { const a = info.areas[+e.target.value]; if (a) centerOn(Math.round((a[0] + a[2]) / 2), Math.round((a[1] + a[3]) / 2)); e.target.value = ''; };
$('#grid').onchange = redraw; $('#ovl').onchange = redraw; $('#shownpc').onchange = redraw;
$('#undo').onclick = () => undoRedo('undo');
$('#redo').onclick = () => undoRedo('redo');
async function save() {
  if (info.running) return toast('Stop the game server first.', true);
  const r = await api('/api/save', {});
  if (r.error) return toast(r.error, true);
  info.dirty = r.dirty; status(); toast(r.msg, r.dirty !== 0);
}
$('#save').onclick = save;
$('#relight').onclick = async () => {
  if (info.dirty) return toast('Save first.', true);
  if (!confirm('Recompute the lighting of the whole world (./server light)? It takes a minute or two.')) return;
  toast('Relighting… this takes a minute or two.');
  const r = await api('/api/relight', {});
  if (r.error) return toast(r.error, true);
  chunks.clear(); redraw(); toast(r.msg); refreshInfo();
};
$('#reload').onclick = async () => {
  if (info.dirty && !confirm('Throw away the unsaved changes and load the world from disk again?')) return;
  const r = await api('/api/reload', {});
  chunks.clear(); redraw(); toast(r.msg); refreshInfo();
};
document.querySelectorAll('#tools button').forEach(b => b.onclick = () => setTool(b.dataset.t));
function status() {
  $('#status').textContent = (info.running ? 'Server running · view only' : (info.dirty ? info.dirty + ' unsaved change' + (info.dirty === 1 ? '' : 's') : 'All saved'));
  $('#status').style.color = info.running ? 'var(--bad)' : info.dirty ? 'var(--accent)' : 'var(--dim)';
  $('#undo').disabled = info.running || !info.undo; $('#redo').disabled = info.running || !info.redo;
  $('#save').disabled = info.running || !info.dirty; $('#relight').disabled = info.running || !!info.dirty;
  $('#banner').style.display = info.running ? 'block' : 'none';
}
async function refreshInfo() {
  const r = await api('/api/info');
  const first = !info.areas.length;
  Object.assign(info, r); status();
  if (first && info.areas.length) {
    const z = $('#zones');
    info.areas.map((a, i) => [a, i]).sort((p, q) => p[0][4].localeCompare(q[0][4])).forEach(([a, i]) => {
      const o = document.createElement('option'); o.value = i; o.textContent = `${a[4]} (${a[0]},${a[1]})`; z.appendChild(o);
    });
  }
  if (r.minimap && !miniOk && !mini.src) { mini.onload = () => { miniOk = true; $('#mini').style.display = 'block'; redraw(); }; mini.src = '/minimap.png'; }
}

// ---------------------------------------------------------------- start
(async function start() {
  resize();
  const ovl = $('#ovl');
  await refreshInfo();
  pal = await api('/api/palette');
  pal.flags.forEach((f, i) => { const o = document.createElement('option'); o.value = i; o.textContent = f; ovl.appendChild(o); });
  const m = location.hash.match(/(\d+),(\d+)/);
  if (m) centerOn(+m[1], +m[2]); else centerOn(512, 512);
  setTool('inspect');
  setInterval(refreshInfo, 5000);
  setInterval(() => { const c = screenToTile(W / 2, H / 2); history.replaceState(null, '', '#' + c.x + ',' + c.y); }, 1000);
  loop();
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main()
