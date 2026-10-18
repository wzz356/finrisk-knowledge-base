import importlib
import importlib.util
import unittest
import os
from pathlib import Path
from runtime_common import read
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(os.environ['FINRISK_RUNTIME_TEST_ROOT']).resolve() if os.environ.get('FINRISK_RUNTIME_TEST_ROOT') else ROOT/'outputs/FinRisk_知识库P0修复_20261018'

class AssetTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('knowledge_assets'),'asset reader not implemented')
        return importlib.import_module('knowledge_assets')
    def reader(self):return self.module().KnowledgeAssets(OUT/'assets',read(OUT/'contracts/asset_lock.json'))
    def test_twelve_cards_and_all_article_sources_readable(self):
        f=self.reader();self.assertEqual(len(f.cards),12);self.assertEqual(len(f.legal.articles),67)
        for mid in f.cards:
            r=f.read_mechanism(mid,'L2');self.assertFalse(r['human_approved'])
        for aid in f.legal.articles:self.assertFalse(f.read_article(aid)['coverage']['current_business_fact_proof'])
    def test_wrong_pin_or_mixed_base_version_is_refused(self):
        m=self.module();lock=read(OUT/'contracts/asset_lock.json');lock['expanded_manifest_sha256']='0'*64
        with self.assertRaises(ValueError):m.KnowledgeAssets(OUT/'assets',lock)
        lock=read(OUT/'contracts/asset_lock.json');lock['base_versions']['content']='foreign'
        with self.assertRaises(ValueError):m.KnowledgeAssets(OUT/'assets',lock)
    def test_unknown_layer_and_id_refused_and_return_is_copy(self):
        f=self.reader()
        for mid,level in [('M99','L0'),('M11','L9')]:
            with self.assertRaises(ValueError):f.read_mechanism(mid,level)
        result=f.read_mechanism('M11','L1');result['title']='changed'
        self.assertNotEqual(f.read_mechanism('M11','L1')['title'],'changed')

if __name__=='__main__':unittest.main()
