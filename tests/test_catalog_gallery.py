"""Navigation and disclosure contracts for the generated, offline gallery.

These assertions inspect the actual generated document, independently of its
renderer helpers. Browser interaction is exercised separately with Playwright.
All records, media and project names below are synthetic.
"""
import base64
import json
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import parse_qs

from test_fc_catalog import Base, run_cli


class GalleryDocument(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.templates = set()
        self.links = []
        self.selectors = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'template' and attrs.get('data-item'):
            self.templates.add(attrs['data-item'])
        if tag == 'a' and 'data-item-link' in attrs:
            self.links.append(attrs['href'])
        if attrs.get('data-selector'):
            self.selectors.add(attrs['data-selector'])


def identity(catalog_id, item_id, revision):
    return base64.urlsafe_b64encode(json.dumps(
        [catalog_id, item_id, revision], ensure_ascii=False).encode()).decode().rstrip('=')


class GalleryNavigationTests(Base):
    def gallery(self, *deps):
        out = self.root / 'gallery'
        args = ['gallery', '--catalog', str(self.catalog), '--out', str(out)]
        for dep in deps:
            args += ['--with-catalog', str(dep)]
        code, payload = run_cli(*args)
        self.assertEqual(code, 0, payload)
        text = (out / 'index.html').read_text()
        return GalleryDocument(text), text

    def test_references_and_history_link_to_exact_records(self):
        dep = self.write_catalog(self.base_document(id='materials', revision=2, items=[
            self.reference_item(id='face', revision=1, assets=[
                {'id': 'web', 'locator': {'root': 'catalog', 'path': 'face.woff2'}}]),
            self.reference_item(id='face', revision=2),
        ]), self.root / 'materials.json')
        self.write('face.woff2', b'synthetic font bytes')
        self.write_catalog(self.base_document(revision=2, items=[
            self.reference_item(id='result', revision=1),
            self.reference_item(id='result', revision=2, materials=[
                {'catalog_id': 'materials', 'item_id': 'face', 'revision': 1, 'asset_id': 'web'}]),
        ]))
        doc, _ = self.gallery(dep)
        self.assertIn(identity('materials', 'face', 1), doc.templates)
        self.assertIn(identity('fc-library', 'result', 1), doc.templates)
        self.assertIn('asset:web', doc.selectors)
        self.assertTrue(doc.links, 'References must be navigable, not metadata-only text.')
        destinations = [parse_qs(href.removeprefix('#')) for href in doc.links]
        self.assertTrue(any(d.get('asset') == ['web'] for d in destinations))
        for dest in destinations:
            self.assertIn(dest['item'][0], doc.templates)

    def test_use_evidence_and_needed_transitive_material_are_reachable(self):
        dep = self.write_catalog(self.base_document(id='materials', items=[
            self.reference_item(id='source'),
            self.reference_item(id='variant', materials=[
                {'catalog_id': 'materials', 'item_id': 'source', 'revision': 1}]),
            self.reference_item(id='unrelated', title='UNRELATED-PRIVATE-COLLECTION-ITEM'),
        ]), self.root / 'materials.json')
        use = {'id': 'composition', 'revision': 1,
               'target': {'project': 'sample-reader', 'location': {'region': 'article'}},
               'references': [{'catalog_id': 'materials', 'item_id': 'variant', 'revision': 1}],
               'relation': 'Keep the material while changing the composition.',
               'status': 'in-use', 'observed_at': '2026-10-24T15:00:00Z',
               'evidence': {'previews': [{'catalog_id': 'fc-library', 'item_id': 'result',
                                         'revision': 1, 'preview_id': 'wide'}]}}
        self.write('result.svg', b'<svg xmlns="http://www.w3.org/2000/svg"/>')
        preview = {'id': 'wide', 'kind': 'screenshot',
                   'locator': {'root': 'catalog', 'path': 'result.svg'}}
        self.write_catalog(self.base_document(revision=2, items=[
            self.reference_item(id='result', revision=1, archived=True, previews=[preview]),
            self.reference_item(id='result', revision=2),
        ], uses=[use]))
        doc, text = self.gallery(dep)
        for key in [('materials', 'source', 1), ('materials', 'variant', 1), ('fc-library', 'result', 1)]:
            self.assertIn(identity(*key), doc.templates)
        self.assertIn('preview:wide', doc.selectors)
        self.assertNotIn('UNRELATED-PRIVATE-COLLECTION-ITEM', text)
        self.assertTrue(any(parse_qs(href[1:]).get('preview') == ['wide'] for href in doc.links))

    def test_missing_dependency_stays_a_gap_without_fabricated_link(self):
        self.write_catalog(self.base_document(items=[self.reference_item(materials=[
            {'catalog_id': 'not-supplied', 'item_id': 'face', 'revision': 7}])]))
        doc, text = self.gallery()
        self.assertIn('unresolved-catalog', text)
        self.assertNotIn(identity('not-supplied', 'face', 7), doc.templates)
        for href in doc.links:
            self.assertIn(parse_qs(href[1:])['item'][0], doc.templates)

    def test_generated_page_is_self_contained_and_exposes_rights(self):
        self.write_catalog(self.base_document(items=[self.reference_item(
            rights={'status': 'known', 'license': 'Synthetic fixture terms',
                    'note': 'No third-party artwork.'})]))
        _, text = self.gallery()
        self.assertIn('Synthetic fixture terms', text)
        self.assertIn('No third-party artwork.', text)
        self.assertNotIn('<script src=', text)
        self.assertNotIn('<link rel="stylesheet"', text)


class PackagedProjectTests(Base):
    def test_reference_desk_source_and_observed_use_remain_resolvable(self):
        package = Path(__file__).resolve().parents[1]
        catalog = package / 'examples/reference-desk/catalog.json'
        binding = 'fc-reference-desk:package=' + str(package)
        code, payload = run_cli('validate', '--catalog', str(catalog), '--root', binding)
        self.assertEqual(code, 0, payload)
        self.assertFalse(payload['missing_media'], payload)
        code, result = run_cli('resolve', '--catalog', str(catalog), '--root', binding,
                               '--id', 'reference-desk-navigation')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['use']['status'], 'in-use')
        self.assertTrue(result['references'] and result['evidence_previews'])
        self.assertTrue(all(entry['status'] == 'available'
                            for entry in result['references'] + result['evidence_previews']))

    def test_real_font_captures_resolve_without_claiming_a_bundled_original(self):
        package = Path(__file__).resolve().parents[1]
        code, payload = run_cli('validate', '--catalog', str(package / 'examples/materials/catalog.json'),
                                '--root', 'fc-material-samples:package=' + str(package))
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload['missing_media'])
        self.assertTrue(all(entry['status'] == 'remote-only' for entry in payload['missing_media']), payload)
