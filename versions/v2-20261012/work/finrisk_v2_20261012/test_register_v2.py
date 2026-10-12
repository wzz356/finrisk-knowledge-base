import unittest
import tempfile
from pathlib import Path
try:
    from register_v2 import next_revision
except ImportError:
    next_revision=None

class RegistrationHistory(unittest.TestCase):
    def test_existing_startup_configuration_is_preserved(self):
        import register_v2 as register
        verified=register.runtime.verify_package_bindings('b001')
        batch=register.runtime.batch_record('b001',verified['schedule'])
        original=(Path(batch['planned_run_path'])/'config.json').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder);(run/'config.json').write_bytes(original)
            register.runtime._make_workflow({**batch,'planned_run_path':str(run)},verified)
            self.assertEqual((run/'config.json').read_bytes(),original)
    def test_new_current_and_changed_candidates_preserve_consecutive_revisions(self):
        self.assertIsNotNone(next_revision)
        self.assertEqual(next_revision(None,None,'new'),0)
        self.assertIsNone(next_revision(1,'same','same'))
        self.assertEqual(next_revision(0,'old','new'),1)
        self.assertEqual(next_revision(1,'old','new'),2)
    def test_revision_limit_cannot_be_reset(self):
        self.assertIsNotNone(next_revision)
        with self.assertRaises(ValueError):next_revision(2,'old','new')

if __name__=='__main__':unittest.main()
