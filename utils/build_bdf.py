#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
#
#  FreeType high-level python API - Copyright 2011 Nicolas P. Rougier
#  Distributed under the terms of the new BSD license.
#
# -----------------------------------------------------------------------------
'''
Glyph bitmap monochrome rendring
'''
from freetype import Face, FT_LOAD_RENDER, FT_LOAD_TARGET_MONO
from argparse import ArgumentParser
import json
import os
import sys
import re
import logging

def main():
    parser = ArgumentParser()
    parser.add_argument("-c", "--config-file", "--cfg-file", action="store", dest="cfg_file", required=True,
        help="Configuration file for font generation")
    args = parser.parse_args()
    with open(args.cfg_file) as _fh:
        cfg = json.loads(json_preparse(_fh.read()))

    target_size = cfg.get("target_size")
    max_ascent = cfg.get("max_ascent")
    space = cfg.get("space")
    if not target_size:
        logging.error("Must specify target_size")
        sys.exit(1)
    if not max_ascent:
        logging.error("Must specify max_ascent")
        sys.exit(1)
    if not space:
        logging.error("Must specify space")
        sys.exit(1)
    max_descent = target_size - max_ascent

    chardata = {}
    for chr_range in cfg.get('ranges', []):
        for char in parse_range(chr_range):
            chardata[char] = None
        
    for font in cfg.get('fonts', []):
        fontfile = font.get("file", "")
        if not os.path.exists(fontfile):
            logging.error("Could not locate " + fontfile + "Skipping\n")
            continue
        logging.info("Using TTF file: " + fontfile)
        fontsize = font.get("size", target_size+1)
        face = Face(fontfile)
        for chr_range in font.get("ranges", []):
            for char in parse_range(chr_range):
                if ('ranges' in cfg and char not in chardata) or chardata.get(char):
                    continue
                if face.get_char_index(unichr(char)) == 0:
                    continue
                for size in range(fontsize, target_size-8, -1):  # FIXME: Why '-8'?
                    data = get_character(
                        face, size, char,
                        max_ascent=max_ascent, max_descent=max_descent,
                        space=space, ignore_ascent=chr_range.get("ignore_ascent"))
                    if data:
                        chardata[char] = data
                        break

    for missing in [_c for _c in sorted(chardata.keys(), key=int) if not chardata[_c]]:
        logging.warning("No character found for " + `missing`)

    write_bdf(chardata,
              name=cfg.get("name", "deviation"),
              target_size=target_size,
              max_ascent=max_ascent)

def parse_range(chr_range):
    if chr_range.get("list"):
        return [int(_c, 0) for _c in chr_range['list']]
    return range(int(chr_range['start'], 0), int(chr_range['end'], 0)+1)

def write_bdf(chardata, name=None, target_size=None, max_ascent=None):
    matched = [_c for _c in sorted(chardata.keys(), key=int) if chardata[_c]]
    data = ""
    data += "STARTFONT 2.1\n"
    data += "FONT -" + name + "--" + `target_size` + "-" + `target_size * 10` + "-75-75\n"
    data += "SIZE " + `target_size` + " 75 75\n"
    data += "FONTBOUNDINGBOX " + `target_size` + " " + `target_size` \
             + " 0 " + `max_ascent - target_size` + "\n"
    data += "STARTPROPERTIES 8\n"
    data += "FONT_NAME \"" + name + "\"\n"
    data += "FONT_ASCENT " + `max_ascent` + "\n"
    data += "FONT_DESCENT " + `target_size - max_ascent` + "\n"
    data += "PIXEL_SIZE " + `target_size` + "\n"
    data += "POINT_SIZE " + `target_size * 10` + "\n"
    data += "RESOLUTION_X 75\n"
    data += "RESOLUTION_Y 75\n"
    data += "RESOLUTION 75\n"
    data += "ENDPROPERTIES\n"
    data += "CHARS {}\n".format(len(matched))
    with open(name + ".bdf", "w") as _fh:
        _fh.write(data)
        for char in matched:
            _fh.write(chardata[char])
        _fh.write("ENDFONT\n")

def get_character(face, size, c, max_ascent=None, max_descent=None, space=None, ignore_ascent=False,):
    uc = unichr(c)
    found = False
    face.set_char_size( size*64 )
    face.load_char(uc, FT_LOAD_RENDER | FT_LOAD_TARGET_MONO )
    rows   = face.glyph.bitmap.rows
    top    = face.glyph.bitmap_top
    ascent = top
    descent = rows - top
    if ignore_ascent:
        if rows > size:
            print "Ignoring {} due to {} > {}".format(c, rows, size)
            return
    else:
        if ascent > max_ascent or descent > max_descent:
            print "Ignoring {} due to {} > {}".format(c, ascent, max_ascent);
            return
    width  = face.glyph.bitmap.width
    bitmap = face.glyph.bitmap
    pitch  = face.glyph.bitmap.pitch
    logging.debug("(%s %02d) %05d/%04x: w:%d, a:%d, d:%d p:%d",face.family_name, size, c, c, width, ascent, descent, pitch)
    if c == 32:
        width = space
    chardata = ""
    chardata += "STARTCHAR uni%04X\n" % (c)
    chardata += "ENCODING " + `c` + "\n"
    chardata += "SWIDTH 500 0\n"
    chardata += "DWIDTH 6 0\n"
    chardata += "BBX %d %d 0 %d\n" % (width, rows, top - rows)
    chardata += "BITMAP\n"
    idx = 0
    for i in bitmap.buffer:
        if (idx % pitch) < int((width + 7) / 8):
            chardata += "%02X" % (i)
        idx += 1
        if (idx % pitch) == 0:
            chardata += "\n"
    chardata += "ENDCHAR\n"
    return chardata

def show_character(bitmap):
    print bitmap.width
    print bitmap.rows
    print bitmap.pitch
    data = []
    for i in range(bitmap.rows):
        row = []
        for j in range(bitmap.pitch):
            row.extend(bits(bitmap.buffer[i*bitmap.pitch+j]))
        data.extend(row[:bitmap.width])
    Z = numpy.array(data).reshape(bitmap.rows, bitmap.width)
    plt.imshow(Z, interpolation='nearest', cmap=plt.cm.gray)
    plt.show()

def json_preparse(json_like):
    """
    This is a crude function to prevent us from needing to depend on JSMin
    Removes C-style comments from *json_like* and returns the result.
    Removes trailing commas from *json_like* and returns the result.
    https://gist.github.com/liftoff/ee7b81659673eca23cd9fc0d8b8e68b7
    """
    comments_re = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    trailing_object_commas_re = re.compile(
        r'(,)\s*}(?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    trailing_array_commas_re = re.compile(
        r'(,)\s*\](?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    def comment_replacer(match):
        s = match.group(0)
        if s[0] == '/': return ""
        return s
    json_like = comments_re.sub(comment_replacer, json_like)
    # Fix objects {} first
    json_like = trailing_object_commas_re.sub("}", json_like)
    # Now fix arrays/lists [] and return the result
    return trailing_array_commas_re.sub("]", json_like)

main()
