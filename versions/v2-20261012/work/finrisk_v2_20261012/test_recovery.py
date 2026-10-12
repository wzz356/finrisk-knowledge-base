import copy
import hashlib
import unittest
try:
    from recovery import reconstruct_inputs
except ImportError:
    reconstruct_inputs=None

class RecoveryInputs(unittest.TestCase):
    def fixture(self):
        from run_v2 import sha_json
        draft={'file_id':'F000001','cases':[],'behaviors':[]}
        effective={**draft,'semantic_status':'candidate','human_review_status':'pending'}
        text='机构违规事实。';digest=hashlib.sha256(text.encode()).hexdigest()
        wrapper={'file_id':'F000001','draft_json_sha256':sha_json(draft),'batch':'early30'}
        source={'file_id':'F000001','source_sha256':digest,'text_sha256':digest,'text_version':1}
        snapshot={'file_id':'F000001','base_draft':draft,'effective_draft':effective,
                  'base_draft_json_sha256':sha_json(draft),'effective_draft_json_sha256':sha_json(effective),
                  'wrapper_metadata':wrapper,'source_record_metadata':source,'document_metadata':{'encoding':'utf-8'}}
        document={'official_file_id':'F000001','full_text':text,'text_sha256':digest}
        return snapshot,document

    def test_restores_original_and_effective_separately_without_source_repo(self):
        self.assertIsNotNone(reconstruct_inputs)
        s,d=self.fixture();saved=copy.deepcopy([s,d]);c,src,ov=reconstruct_inputs([s],[d])
        self.assertEqual(c['F000001']['draft'],s['base_draft'])
        self.assertEqual(ov['F000001'],s['effective_draft'])
        self.assertEqual(src['F000001']['full_text'],d['full_text'])
        self.assertEqual([s,d],saved)

    def test_refuses_source_drift_or_duplicate_snapshots(self):
        self.assertIsNotNone(reconstruct_inputs)
        s,d=self.fixture();d['full_text']='另一文书'
        with self.assertRaises(ValueError):reconstruct_inputs([s],[d])
        s,d=self.fixture()
        with self.assertRaises(ValueError):reconstruct_inputs([s,s],[d])

if __name__=='__main__':unittest.main()
