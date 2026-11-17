from PIL import Image, ImageOps
def L(s):
    return s if isinstance(s, Image.Image) else Image.open('/home/claude/decor/%05d.png' % s).convert('RGBA')
def scene(objs, floor=1014, w=6, h=6, walls=()):
    scr = lambda x, y: (16 * (x + y), 8 * (x - y))
    pts = [scr(x, y) for x in (-1, w + 1) for y in (-1, h + 1)]
    mx = min(p[0] for p in pts) - 40; Mx = max(p[0] for p in pts) + 40; my = min(p[1] for p in pts) - 110; My = max(p[1] for p in pts) + 40
    im = Image.new('RGBA', (Mx - mx, My - my), (20, 20, 24, 255))
    def put(s, x, y):
        s = L(s); sx, sy = scr(x, y); W, H = s.size; im.alpha_composite(s, (sx - mx - W // 2, sy - my + 8 - H))
    for x, y in sorted([(x, y) for x in range(w) for y in range(h)], key=lambda p: (p[0] - p[1], p[0])): put(floor, x, y)
    for x, y, s in sorted(list(objs) + [(x, y, s) for x, y, s in walls], key=lambda o: (o[0] - o[1], o[0])): put(s, x, y)
    return im
