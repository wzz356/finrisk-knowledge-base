import json
import tempfile
import unittest
from pathlib import Path
from v2_payloads import pack_file, verify_payload, restore_payloads


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.version = self.base / 'version'
        self.version.mkdir()

    def test_split_preserves_unicode_blank_lines_and_final_line(self):
        source = self.base / 'input.jsonl'
        raw = '{"正文":"中文"}\r\n\n{"x":2}\n{"末行":true}'.encode('utf-8')
        source.write_bytes(raw)
        meta = pack_file(source, self.version, 'data/正文.jsonl', limit=24)
        self.assertGreater(len(meta['parts']), 1)
        self.assertTrue((self.version / 'data/正文.jsonl').is_dir())
        self.assertTrue(verify_payload(self.version, meta))
        (self.version / 'payload_map.json').write_text(json.dumps({'payloads': [meta]}), encoding='utf-8')
        restore_payloads(self.version, self.base / 'restored')
        self.assertEqual((self.base / 'restored/data/正文.jsonl').read_bytes(), raw)

    def test_empty_copy_and_nonempty_destination_refused(self):
        source = self.base / 'empty.jsonl'
        source.write_bytes(b'')
        meta = pack_file(source, self.version, 'empty.jsonl', limit=24)
        self.assertTrue(verify_payload(self.version, meta))
        (self.version / 'payload_map.json').write_text(json.dumps({'payloads': [meta]}), encoding='utf-8')
        destination = self.base / 'occupied'
        destination.mkdir()
        (destination / 'owned.txt').write_text('keep', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            restore_payloads(self.version, destination)
        self.assertEqual((destination / 'owned.txt').read_text(), 'keep')

    def test_tamper_and_path_escape_refused(self):
        source = self.base / 'input.jsonl'
        source.write_bytes(b'{"a":1}\n' * 10)
        meta = pack_file(source, self.version, 'data/a.jsonl', limit=24)
        part = self.version / meta['parts'][0]['path']
        part.write_bytes(part.read_bytes() + b'changed')
        with self.assertRaises(ValueError):
            verify_payload(self.version, meta)
        meta['path'] = '../outside.jsonl'
        (self.version / 'payload_map.json').write_text(json.dumps({'payloads': [meta]}), encoding='utf-8')
        with self.assertRaises(ValueError):
            restore_payloads(self.version, self.base / 'restored')
        self.assertFalse((self.base / 'outside.jsonl').exists())

    def test_existing_copy_never_overwritten_on_source_drift(self):
        source = self.base / 'input.jsonl'
        source.write_bytes(b'{"a":1}\n')
        pack_file(source, self.version, 'data/a.jsonl', limit=24)
        source.write_bytes(b'{"a":2}\n')
        with self.assertRaises(ValueError):
            pack_file(source, self.version, 'data/a.jsonl', limit=24)
        self.assertEqual((self.version / 'data/a.jsonl').read_bytes(), b'{"a":1}\n')


if __name__ == '__main__':
    unittest.main()
