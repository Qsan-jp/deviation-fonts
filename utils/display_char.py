#!/usr/bin/env python

from freetype import Face, FT_LOAD_RENDER, FT_LOAD_TARGET_MONO, FT_FACE_FLAG_SCALABLE
import numpy as np
import matplotlib.pyplot as plt
import sys

BACKGROUND = 0.2

#import pdb; pdb.set_trace()

def prepare_bitmap(glyph):
    bitmap = glyph.bitmap
    ascent = glyph.bitmap_top
    
    data = np.unpackbits(np.array(bitmap.buffer, dtype=np.uint8)).reshape(bitmap.rows, bitmap.pitch * 8)
    Z = np.delete(data, np.s_[bitmap.width:], 1).astype(float)
    if ascent < bitmap.rows:
        ascent_coloring = [1.] * ascent + [0.5] * (bitmap.rows - ascent)
        ascent_coloring = np.array(ascent_coloring).reshape(bitmap.rows,1)
        Z = Z * ascent_coloring
    return Z

def normalize_bitmap(Z, rows):
    height = Z.shape[0]
    width = Z.shape[1]
    if height < rows:
        Z = np.concatenate([Z, BACKGROUND * np.ones((rows-height, width))], 0)
    return Z

def compare_characters(ref_bmps, new_bmps):
    rows = max([Z.shape[0] for Z in ref_bmps + new_bmps])
    line = []
    if len(ref_bmps) != len(new_bmps):
        print "Can't compare lists of different length"
        return
    space = BACKGROUND * np.ones((2*rows+2, 2))
    for idx in range(0, len(ref_bmps)):
        ref = normalize_bitmap(ref_bmps[idx], rows)
        new = normalize_bitmap(new_bmps[idx], rows)
        if ref.shape[1] < new.shape[1]:
            ref = np.concatenate([ref, BACKGROUND * np.ones((rows, new.shape[1] - ref.shape[1]))], 1)
        elif new.shape[1] < ref.shape[1]:
            new = np.concatenate([new, np.zeros((rows, ref.shape[1] - new.shape[1]))], 1)
        line += [np.concatenate([ref, BACKGROUND * np.ones((2, ref.shape[1])), new], 0), space]
    Z = np.concatenate(line, 1)
    
    plt.imshow(Z, interpolation='nearest', cmap=plt.cm.hot)
    plt.show()

def get_best_size(face, size):
    if face.face_flags & FT_FACE_FLAG_SCALABLE:
        return size
    return max([face.available_sizes[0].height] + [_s.height for _s in face.available_sizes if _s.height <= size])

size = int(sys.argv[1], 0)
face1 = Face(sys.argv[2])
face2 = Face(sys.argv[3])
size1 = get_best_size(face1, size)
print size1
size2 = get_best_size(face2, size)
face1.set_char_size( size1 * 64 )
face2.set_char_size( size2 * 64 )
g1 = []
g2 = []
for c in sys.argv[4:]:
    uc = unichr(int(c, 0))
    face1.load_char(uc, FT_LOAD_RENDER | FT_LOAD_TARGET_MONO )
    g1.append(prepare_bitmap(face1.glyph))
    face2.load_char(uc, FT_LOAD_RENDER | FT_LOAD_TARGET_MONO )
    g2.append(prepare_bitmap(face2.glyph))
compare_characters(g1, g2)

