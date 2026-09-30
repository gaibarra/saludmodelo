"""Source integrity and non-overwrite checks; no application or DB required."""
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('review_pack', ROOT / 'tools/build_institutional_review.py')
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


class ReviewPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='salud-review-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        for name in (pack.DOCX, pack.PROMPT, 'imports/source-inventory.json', 'imports/help-drafts-v1.json', 'docs/validacion/GUIA.md', 'docs/validacion/ACTA_MODELO.md'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.output = Path(self.temp.name) / 'output'

    def mutate_draft(self, fn):
        path = self.root / 'imports/help-drafts-v1.json'
        data = json.loads(path.read_text())
        fn(next(iter(data['questions'].values())))
        path.write_text(json.dumps(data))

    def test_complete_pack_counts_integrity_and_no_institutional_decisions(self):
        self.assertEqual(pack.build(self.root, self.output), 177)
        manifest = json.loads((self.output / 'manifest.json').read_text())
        with zipfile.ZipFile(self.output / 'paquete_revision.zip') as archive:
            self.assertEqual(set(archive.namelist()), set(manifest['files']) | {'manifest.json'})
            for name, meta in manifest['files'].items():
                raw = (self.output / name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), meta['sha256'])
                self.assertEqual(archive.read(name), raw)
        for name, expected in [('revision_fichas.csv', 177), ('servicios.csv', 9), ('reglas.csv', 11), ('usabilidad.csv', 27), ('responsables.csv', 1)]:
            rows = list(csv.DictReader((self.output / name).read_text(encoding='utf-8-sig').splitlines()))
            self.assertEqual(len(rows), expected)
            self.assertTrue(all(None not in row and None not in row.values() for row in rows))
            self.assertTrue(all(row.get('estado', row.get('estado_paquete')) == 'pendiente' for row in rows))
        rows = list(csv.DictReader(io.StringIO((self.output / 'revision_fichas.csv').read_text(encoding='utf-8-sig'))))
        self.assertTrue(all(not r['decision_en_gestor'] and not r['servicio'] and not r['revisor_competente'] for r in rows))
        self.assertEqual(len({r['pregunta_id'] for r in rows}), 177)
        self.assertEqual((self.output / 'fichas.html').read_text().count('<article id="ficha-'), 177)

    def test_never_overwrites_completed_notes(self):
        self.output.mkdir()
        notes = self.output / 'revision_fichas.csv'
        notes.write_text('Observación real que se debe conservar')
        with self.assertRaises(FileExistsError):
            pack.build(self.root, self.output)
        self.assertEqual(notes.read_text(), 'Observación real que se debe conservar')

    def test_rejects_changed_source_and_does_not_create_output(self):
        with (self.root / pack.DOCX).open('ab') as file:
            file.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'fuentes cambiaron'):
            pack.build(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_changed_inventory(self):
        path = self.root / 'imports/source-inventory.json'
        data = json.loads(path.read_text())
        data[0]['text'] = 'Alterado'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'inventario no coincide'):
            pack.build(self.root, self.output)

    def test_rejects_broken_citation(self):
        self.mutate_draft(lambda entry: entry['references'][0].update(locator='página inventada'))
        with self.assertRaisesRegex(ValueError, 'Referencia inconsistente'):
            pack.build(self.root, self.output)

    def test_rejects_incomplete_draft(self):
        self.mutate_draft(lambda entry: entry['content'].update(evidence=''))
        with self.assertRaisesRegex(ValueError, 'Ficha incompleta'):
            pack.build(self.root, self.output)

    def test_html_and_csv_do_not_execute_embedded_content(self):
        self.mutate_draft(lambda entry: entry['content'].update(steps='<script>alert(1)</script>'))
        pack.build(self.root, self.output)
        raw = (self.output / 'fichas.html').read_text()
        self.assertNotIn('<script>', raw)
        self.assertIn('&lt;script&gt;', raw)
        rows = list(csv.reader(io.StringIO(pack.csv_bytes(['x'], [[' =1+1'], ['@cmd']]).decode('utf-8-sig'))))
        self.assertEqual(rows[1][0], "' =1+1")
        self.assertEqual(rows[2][0], "'@cmd")


if __name__ == '__main__':
    unittest.main()
