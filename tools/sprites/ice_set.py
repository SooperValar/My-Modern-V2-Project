#!/usr/bin/env python3
"""The Ice set (Helmet, Armor, Leggings, Boots, Gloves of Ice, templates 1272-1276): recoloured from the Fire set
(art/ice_set/: Helmet 893, Armor 894, Sleeves 891, Leggings 892, Boots 890, Cloak 895) towards the Ice Cloak's pale
blue (16770). The Cloak of Ice (template 1407, sprite 18105) completes the set; the older Ice Cloak (909) is separate.
The fire's red-orange becomes ice blue, its bright yellow flecks frost white; the texture stays.

    ice_set.py <client folder>      writes <client>/GFX/18100-18105.png
"""
import colorsys, os, sys
from PIL import Image

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art', 'ice_set')
KEY = (255, 0, 255)
OUT = {18100: 890, 18101: 894, 18102: 891, 18103: 893, 18104: 892,   # boots, armor, gloves (sleeves), helmet, leggings
       18105: 895}                                                   # cloak (the set's own; the old Ice Cloak 16770 stays)


def ice(im):
    out = im.convert('RGBA').copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a == 0 or (r, g, b) == KEY:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            warm = (r - b) / 255                     # how fiery it was: yellow flecks -> frost white
            hue = 0.60 - 0.04 * min(1, max(0, (g - b) / 255 * 2))
            sat = max(0.08, s * 0.55 - 0.25 * max(0, (g / 255) - 0.45))
            val = min(1, 0.32 + v * 0.78)
            r2, g2, b2 = colorsys.hsv_to_rgb(hue, sat, val)
            px[x, y] = (round(r2 * 255), round(g2 * 255), round(b2 * 255), a)
    return out


def main():
    gfx = os.path.join(sys.argv[1], 'GFX')
    os.makedirs(gfx, exist_ok=True)
    for n, src in OUT.items():
        ice(Image.open(os.path.join(ART, '%d.png' % src))).save(os.path.join(gfx, '%05d.png' % n))
    print('%d sprites written to %s' % (len(OUT), gfx))


if __name__ == '__main__':
    main()
