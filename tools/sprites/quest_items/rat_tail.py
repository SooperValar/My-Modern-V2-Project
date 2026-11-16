"""44522 Broodmother's Tail (Nov 16): a long bald rat tail, curled, with a tuft of grey fur at the cut end."""
import numpy as np, math, sys
from PIL import Image
a = np.zeros((32, 32, 4), np.uint8)
def put(x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < 32 and 0 <= y < 32: a[y, x] = (*c, 255)
# the tail: from the fur at the lower left, sweeping right and curling up at the tip
pts = []
for k in range(220):
    t = k / 219
    x = 7 + 18 * t + 3 * math.sin(t * 3.0)
    y = 22 - 9 * t ** 1.6 + 2.5 * math.sin(t * 5.5)
    pts.append((x, y, t))
for x, y, t in pts:
    w = 1.6 * (1 - t) + 0.5                      # thick at the base, thin at the tip
    base = np.array([196, 140, 128]) * (1 - .25 * t) + np.array([150, 120, 115]) * .25 * t
    for dx in np.arange(-w, w + .01, .5):
        for dy in np.arange(-w, w + .01, .5):
            if dx * dx + dy * dy <= w * w:
                sh = 1.0 if dy < 0 else .72       # lit from above
                put(x + dx, y + dy, tuple(int(v * sh) for v in base))
for x, y, t in pts[::14]:                        # ring scales
    if t < .8: put(x, y + .8, (130, 90, 85))
# the fur at the cut
for dx, dy, c in [(-2, 0, (120, 115, 110)), (-1, -1, (150, 145, 140)), (-2, 1, (100, 95, 90)), (-1, 1, (135, 130, 125)), (-3, 0, (90, 86, 82)),
                  (-1, 0, (165, 160, 152)), (-2, -1, (110, 105, 100)), (0, 1, (120, 112, 108)), (-3, 1, (80, 76, 72))]:
    put(7 + dx, 22 + dy, c)
put(6, 21, (200, 70, 60)); put(6, 22, (170, 50, 45))     # where it was cut
Image.fromarray(a, 'RGBA').save(sys.argv[1] if len(sys.argv) > 1 else 'out2/44522.png')
