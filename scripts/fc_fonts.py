#!/usr/bin/env python3
"""Inspect and subset explicitly supplied local fonts; never fetch or overwrite.

Optional dependency: fonttools[woff]. See references/material-production.md.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


class FontError(ValueError):
    pass


def font_tools():
    try:
        import fontTools
        from fontTools import subset
        from fontTools.ttLib import TTFont
    except ImportError as exc:
        raise FontError('Optional dependency missing: use a project environment with fonttools[woff].') from exc
    return fontTools, subset, TTFont


def digest(data):
    return hashlib.sha256(data).hexdigest()


def names(font, name_id):
    return sorted({record.toUnicode() for record in font['name'].names
                   if record.nameID == name_id}) if 'name' in font else []


def metadata(font):
    return {
        'family': names(font, 1), 'subfamily': names(font, 2),
        'version': names(font, 5), 'license_description': names(font, 13),
        'license_url': names(font, 14),
        'axes': [{'tag': axis.axisTag, 'min': axis.minValue,
                  'default': axis.defaultValue, 'max': axis.maxValue}
                 for axis in font['fvar'].axes] if 'fvar' in font else [],
        'unicode_count': len(font.getBestCmap() or {}),
    }


def read_inputs(paths, output=None):
    codepoints, inputs = set(), []
    for name in paths:
        path = Path(name).resolve(strict=True)
        data = path.read_bytes()
        content = data.decode('utf-8-sig')
        # Layout controls do not ask the font for a visible glyph. Do not
        # normalize: combining marks and punctuation must retain their identity.
        codepoints.update(ord(char) for char in content if char not in '\n\r\t')
        inputs.append({'path': os.path.relpath(path, output) if output else str(path),
                       'sha256': digest(data)})
    return codepoints, inputs


def unicode_labels(values):
    return [f'U+{value:04X}' for value in sorted(values)]


def open_font(data, font_index):
    _, _, TTFont = font_tools()
    return TTFont(io.BytesIO(data), fontNumber=font_index, recalcTimestamp=False)


def inspect_font(source, text_files=(), font_index=-1):
    path = Path(source).resolve(strict=True)
    data = path.read_bytes()
    required, _ = read_inputs(text_files)
    with open_font(data, font_index) as font:
        available = set(font.getBestCmap() or {})
        return {'source': str(path), 'sha256': digest(data), 'bytes': len(data),
                'font_index': font_index, **metadata(font),
                'requested_codepoints': unicode_labels(required),
                'missing_codepoints': unicode_labels(required - available)}


def subset_font(source, text_files, output, font_index=-1, allow_missing=False):
    fonttools, subset, _ = font_tools()
    source = Path(source).resolve(strict=True)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FontError('Output already exists; choose a new revision directory.')
    required, inputs = read_inputs(text_files, output)
    if not required:
        raise FontError('Text inputs contain no glyph requests.')
    data = source.read_bytes()
    with open_font(data, font_index) as font:
        original = metadata(font)
        missing = required - set(font.getBestCmap() or {})
        if missing and not allow_missing:
            raise FontError('Missing glyphs: ' + ', '.join(unicode_labels(missing)))
        options = subset.Options()
        options.flavor = 'woff2'
        options.layout_features = ['*']
        options.name_IDs = ['*']
        options.name_languages = ['*']
        options.name_legacy = True
        options.recalc_timestamp = False
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(unicodes=required - missing)
        subsetter.subset(font)
        font.flavor = 'woff2'
        encoded = io.BytesIO()
        font.save(encoded)
    result = encoded.getvalue()
    # Reopen the serialized output, not the in-memory source, for coverage.
    with open_font(result, -1) as checked:
        lost = (required - missing) - set(checked.getBestCmap() or {})
        if lost:
            raise FontError('Subset lost requested glyphs: ' + ', '.join(unicode_labels(lost)))
        produced = metadata(checked)
    manifest = {
        'schema_version': 1, 'operation': 'font-subset',
        'source': {'path': os.path.relpath(source, output), 'sha256': digest(data),
                   'bytes': len(data), 'font_index': font_index, **original},
        'text_inputs': inputs,
        'requested_codepoints': unicode_labels(required),
        'missing_codepoints': unicode_labels(missing),
        'output': {'path': 'font.woff2', 'sha256': digest(result),
                   'bytes': len(result), **produced},
        'recipe': {'tool': 'fc_fonts.py', 'fonttools_version': fonttools.__version__,
                   'layout_features': '*', 'names': 'all', 'hinting': 'retained',
                   'allow_missing': allow_missing},
        'limits': 'Coverage is cmap evidence, not shaping, browser loading, visual quality, or a license grant.',
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.fc-fonts-', dir=output.parent))
    reserved = False
    try:
        (staging / 'font.woff2').write_bytes(result)
        (staging / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # mkdir arbitrates concurrent callers without replacing an earlier run.
        output.mkdir()
        reserved = True
        os.replace(staging, output)
        reserved = False
    finally:
        if reserved:
            output.rmdir()  # Only the empty directory this invocation reserved.
        if staging.exists():
            shutil.rmtree(staging)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'subset'):
        sub = commands.add_parser(command)
        sub.add_argument('--font', required=True)
        sub.add_argument('--font-index', type=int, default=-1, help='Required member index for TTC/OTC collections.')
        sub.add_argument('--text-file', action='append', default=[], required=command == 'subset')
        if command == 'subset':
            sub.add_argument('--out', required=True, help='New immutable output directory.')
            sub.add_argument('--allow-missing', action='store_true', help='Explicitly allow known fallback characters; list them in the manifest.')
    args = parser.parse_args(argv)
    try:
        if args.command == 'inspect':
            result = inspect_font(args.font, args.text_file, args.font_index)
        else:
            result = subset_font(args.font, args.text_file, args.out, args.font_index, args.allow_missing)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
