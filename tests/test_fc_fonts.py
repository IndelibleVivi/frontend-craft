"""Synthetic font operations and the bundled OFL specimen; no network calls."""
import importlib.util
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fc_fonts

HAS_TOOLS = importlib.util.find_spec('fontTools') is not None


@unittest.skipUnless(HAS_TOOLS, 'optional fonttools[woff] environment required')
class FontTests(unittest.TestCase):
    def setUp(self):
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'synthetic.ttf'
        glyphs = ['.notdef', 'space', 'A', 'B', 'uni4E2D', 'uni0301']
        fb = FontBuilder(1000, isTTF=True)
        fb.setupGlyphOrder(glyphs)
        fb.setupCharacterMap({32: 'space', 65: 'A', 66: 'B', 0x4E2D: 'uni4E2D', 0x301: 'uni0301'})
        outlines = {}
        for name in glyphs:
            pen = TTGlyphPen(None)
            if name not in ('.notdef', 'space'):
                pen.moveTo((80, 0)); pen.lineTo((300, 700)); pen.lineTo((520, 0)); pen.closePath()
            outlines[name] = pen.glyph()
        fb.setupGlyf(outlines)
        fb.setupHorizontalMetrics({name: (600, 0) for name in glyphs})
        fb.setupHorizontalHeader(ascent=800, descent=-200)
        fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
        fb.setupNameTable({'familyName': 'FC Synthetic', 'styleName': 'Regular',
                          'psName': 'FCSynthetic-Regular', 'version': 'Version 1.000',
                          'licenseDescription': 'Synthetic test only'})
        fb.setupPost(); fb.setupMaxp(); fb.save(self.source)
        self.text = self.root / 'copy.txt'
        self.text.write_text('A中\nA\u0301', encoding='utf-8')

    def test_inspect_actual_font_and_missing_glyphs(self):
        self.text.write_text('A中界', encoding='utf-8')
        result = fc_fonts.inspect_font(self.source, [self.text])
        self.assertEqual(result['family'], ['FC Synthetic'])
        self.assertEqual(result['missing_codepoints'], ['U+754C'])
        self.assertEqual(result['unicode_count'], 5)

    def test_subset_retains_exact_text_original_and_license(self):
        from fontTools.ttLib import TTFont
        original = self.source.read_bytes()
        result = fc_fonts.subset_font(self.source, [self.text], self.root / 'v1')
        with TTFont(self.root / 'v1/font.woff2') as font:
            self.assertEqual(set(font.getBestCmap()), {65, 0x4E2D, 0x301})
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(result['output']['license_description'], ['Synthetic test only'])
        self.assertEqual(result['source']['sha256'], fc_fonts.digest(original))
        self.assertEqual(result['missing_codepoints'], [])
        self.assertEqual(json.loads((self.root / 'v1/manifest.json').read_text()), result)

    def test_new_copy_rebuilds_from_original_and_preserves_old_variant(self):
        from fontTools.ttLib import TTFont
        fc_fonts.subset_font(self.source, [self.text], self.root / 'v1')
        prior = (self.root / 'v1/font.woff2').read_bytes()
        self.text.write_text('AB中', encoding='utf-8')
        fc_fonts.subset_font(self.source, [self.text], self.root / 'v2')
        with TTFont(self.root / 'v2/font.woff2') as font:
            self.assertIn(66, font.getBestCmap())
        self.assertEqual((self.root / 'v1/font.woff2').read_bytes(), prior)
        with self.assertRaises(fc_fonts.FontError):
            fc_fonts.subset_font(self.source, [self.text], self.root / 'v1')

    def test_missing_glyph_fails_before_publication_unless_explicit(self):
        self.text.write_text('A界', encoding='utf-8')
        with self.assertRaisesRegex(fc_fonts.FontError, r'U\+754C'):
            fc_fonts.subset_font(self.source, [self.text], self.root / 'v1')
        self.assertFalse((self.root / 'v1').exists())
        result = fc_fonts.subset_font(self.source, [self.text], self.root / 'v1', allow_missing=True)
        self.assertEqual(result['missing_codepoints'], ['U+754C'])

    def test_multiple_text_inputs_and_no_implicit_source_code_scan(self):
        extra = self.root / 'extra.txt'; extra.write_text('B', encoding='utf-8')
        result = fc_fonts.subset_font(self.source, [self.text, extra], self.root / 'v1')
        self.assertEqual(len(result['text_inputs']), 2)
        self.assertIn('U+0042', result['requested_codepoints'])

    def test_failed_publish_cleans_only_owned_staging(self):
        keep = self.root / 'unrelated.txt'; keep.write_text('keep')
        with mock.patch.object(fc_fonts.os, 'replace', side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):
                fc_fonts.subset_font(self.source, [self.text], self.root / 'v1')
        self.assertFalse((self.root / 'v1').exists())
        self.assertEqual(list(self.root.glob('.fc-fonts-*')), [])
        self.assertEqual(keep.read_text(), 'keep')

    def test_cli_json_and_error_exit(self):
        script = str(Path(fc_fonts.__file__))
        good = subprocess.run([sys.executable, script, 'inspect', '--font', str(self.source),
                               '--text-file', str(self.text)], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)['missing_codepoints'], [])
        bad = subprocess.run([sys.executable, script, 'subset', '--font', str(self.source),
                              '--text-file', str(self.text), '--out', str(self.root)], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn('already exists', json.loads(bad.stderr)['error'])

    def test_packaged_specimen_has_all_actual_glyphs_and_weight_axis(self):
        from fontTools.ttLib import TTFont
        class SampleText(HTMLParser):
            def __init__(self):
                super().__init__(); self.active = False; self.text = ''
            def handle_starttag(self, tag, attrs):
                if tag == 'p':
                    self.active = 'sample' in dict(attrs).get('class', '').split()
            def handle_endtag(self, tag):
                if tag == 'p':
                    self.active = False
            def handle_data(self, data):
                if self.active:
                    self.text += data
        root = Path(__file__).resolve().parents[1] / 'examples/materials'
        parser = SampleText(); parser.feed((root / 'index.html').read_text())
        required = {ord(char) for char in parser.text if char not in '\n\r\t'}
        self.assertIn(0x4E2D, required)
        with TTFont(root / 'noto-sans-sc-specimen.woff2') as font:
            self.assertEqual(required - set(font.getBestCmap()), set())
            self.assertEqual([(a.axisTag, a.minValue, a.maxValue) for a in font['fvar'].axes],
                             [('wght', 100, 900)])
        record = json.loads((root / 'ASSETS.json').read_text())
        self.assertEqual(record['output']['sha256'],
                         fc_fonts.digest((root / record['output']['path']).read_bytes()))


if __name__ == '__main__':
    unittest.main()
