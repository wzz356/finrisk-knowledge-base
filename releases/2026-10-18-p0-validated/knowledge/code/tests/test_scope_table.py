import importlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from knowledge_assets import KnowledgeAssets
from runtime_common import read,sha

WORK=Path(__file__).resolve().parents[1]
OUT=Path(os.environ['FINRISK_RUNTIME_TEST_ROOT']).resolve() if os.environ.get('FINRISK_RUNTIME_TEST_ROOT') else WORK.parents[1]/'outputs/FinRisk_知识库P0修复_20261018'

class ScopeTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.assets=KnowledgeAssets(OUT/'assets',read(OUT/'contracts/asset_lock.json'))
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scope_table'),'scope table loader not implemented')
        return importlib.import_module('scope_table')
    def test_original_scope_rows_replay(self):
        p=WORK/'scope_author/article_scopes.jsonl';got=self.module().load_scopes(p,sha(p),self.assets)
        self.assertEqual(len(got),67);self.assertEqual(got['L005-A0016']['product_scope'],['universal_life'])
    def test_wrong_pin_refused(self):
        with self.assertRaises(ValueError):self.module().load_scopes(WORK/'scope_author/article_scopes.jsonl','0'*64,self.assets)
    def test_real_universal_disclosure_not_excluded_at_pre_sale(self):
        from evidence_runtime import assemble_policy
        p=WORK/'scope_author/article_scopes.jsonl';scopes=self.module().load_scopes(p,sha(p),self.assets)
        text='保险公司在售前介绍万能型保险。'
        facts={axis:dict(value=v,origin='current_input',quote=q,start=text.index(q),end=text.index(q)+len(q)) for axis,v,q in [('actor','insurer','保险公司'),('product','universal_life','万能型保险'),('stage','pre_sale','售前')]}
        law,_,decisions=assemble_policy(self.assets,scopes,['M05'],current_text=text,scope_facts=facts,law_budget=8000)
        for aid in ['L005-A0012','L005-A0029']:
            self.assertEqual(decisions[aid]['decision'],'conditional')
            self.assertIn(aid,law['included_article_ids'])
    def test_rehashed_fake_evidence_and_duplicate_rows_refused(self):
        original=(WORK/'scope_author/article_scopes.jsonl').read_text(encoding='utf-8').splitlines()
        for mode in ['fake','duplicate']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory(dir=WORK) as d:
                data=list(original)
                if mode=='fake':
                    row=json.loads(data[0]);row['evidence'][0]['literal']='伪造证据';data[0]=json.dumps(row,ensure_ascii=False)
                else:data[1]=data[0]
                p=Path(d)/'s.jsonl';p.write_text('\n'.join(data)+'\n',encoding='utf-8')
                with self.assertRaises(ValueError):self.module().load_scopes(p,sha(p),self.assets)

if __name__=='__main__':unittest.main()
