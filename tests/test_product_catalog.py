"""Keep the operated Side A specimen connected to its editable source.

No browser or npm dependency is needed for these file/identity checks.
"""
import json
from pathlib import Path
import unittest
from test_fc_catalog import run_cli

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'examples/products/music-library/catalog.json'
BINDING = f'fc-side-a:package={ROOT / "examples/products"}'

class ProductContinuationTests(unittest.TestCase):
    def test_real_product_catalog_resolves_without_media_gaps(self):
        code, result = run_cli('validate', '--catalog', str(CATALOG), '--root', BINDING)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['missing_media'], [])
        code, bundle = run_cli('resolve', '--catalog', str(CATALOG), '--root', BINDING,
                              '--id', 'library-continuation')
        self.assertEqual(code, 0, bundle)
        self.assertEqual(bundle['kind'], 'use')
        self.assertEqual(bundle['use']['status'], 'in-use')
        self.assertEqual(bundle['unresolved_references'], [])
        self.assertTrue(bundle['references'])
        self.assertTrue(bundle['evidence_previews'])

    def test_continuation_retains_source_rights_and_actual_bilingual_states(self):
        document = json.loads(CATALOG.read_text())
        items = {item['id']: item for item in document['items']}
        source = items['side-a-source']['assets']
        self.assertTrue({'App-tsx', 'LibraryTransfer-tsx', 'domain-ts', 'player-ts',
                         'transfer-ts', 'prepare-media', 'render-covers'}.issubset(
                            {asset['id'] for asset in source}))
        states = items['preview-before-transfer']['previews']
        self.assertEqual({tuple(p['capture']['viewport']) for p in states},
                         {(1440, 1000), (390, 844)})
        self.assertTrue(any(p['id'].endswith('zh-CN') for p in states))
        self.assertTrue(any(p['id'].endswith('.en') for p in states))
        self.assertEqual(items['sleeves-and-type']['rights']['status'], 'known')
        # A portable source package must never silently fetch music on build/dev.
        package = json.loads((CATALOG.parents[1] / 'package.json').read_text())
        for command in ['build', 'dev', 'test']:
            self.assertNotIn('media:fetch', package['scripts'][command])
        self.assertIn('music-library/public/assets/audio/',
                      (CATALOG.parents[1] / '.gitignore').read_text())

if __name__ == '__main__':
    unittest.main()
