#!/usr/bin/env python3
"""Install a recoloured sprite set as an appearance tier.

    install_variant.py <recolour folder> <client folder> [tier]

<recolour folder> holds NNNNN.png named by the ORIGINAL sprite numbers (the
V2 Sprite Recolor Tool output, e.g. ArchTemplar/Blue/Male). Each file is copied
to <client folder>/gfx/ as sprite NNNNN + 448*tier: the unused block right
after each character's 448 frames. The server's #looktier <player> <tier>
then switches a character to it.
"""
import os, shutil, sys

def main():
    src, client = sys.argv[1], sys.argv[2]
    tier = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    dst = os.path.join(client, 'gfx')
    os.makedirs(dst, exist_ok=True)
    nums = sorted(int(f[:-4]) for f in os.listdir(src) if f.lower().endswith('.png') and f[:-4].isdigit())
    for n in nums:
        shutil.copyfile(os.path.join(src, '%05d.png' % n), os.path.join(dst, '%05d.png' % (n + 448 * tier)))
    if nums:
        print('%d sprites installed as %05d-%05d (tier %d)' % (len(nums), nums[0] + 448 * tier, nums[-1] + 448 * tier, tier))

if __name__ == '__main__':
    main()
