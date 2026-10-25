#!/usr/bin/env python3
"""Upgrade stone sprite 18229: the soulstone (16972, a blue four-pointed star) recoloured gold.
Uses the sprite loader in ~/tq/sprload.py; writes into the client GFX folder."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/tq'))
from sprload import load
import numpy as np
from PIL import Image
a = np.array(load(16972)).astype(float)
al = a[..., 3] > 0
lum = a[..., :3].mean(-1, keepdims=True)
gold = np.array([255, 200, 70.])
o = a.copy()
o[..., :3] = np.where(al[..., None], np.clip(lum / 255 * gold * 1.25 + (lum > 200) * 40, 0, 255), 0)
o = o.astype(int); o[..., 0] = (o[..., 0] >> 3) << 3; o[..., 1] = (o[..., 1] >> 2) << 2; o[..., 2] = (o[..., 2] >> 3) << 3
Image.fromarray(o.astype(np.uint8), 'RGBA').save(os.path.expanduser('~/mnt/Client/GFX/18229.png'))
