import importlib
import importlib.util
import unittest
from frozen_legal_registry import dependency_closure

class RegistryFixture:
    def __init__(self):
        self.articles={a:dict(article_id=a,source_id='S',version_id='v',text=t) for a,t in [('A','主条原句。'),('B','例外条件，满足时除外。')]}
        self.sources={'S':dict(source_id='S',version_id='v',axes={'current_validity':{'status':'pending'}})}
    def dependency_closure(self,roots):return dependency_closure(roots,{'A':['B']},self.articles)

class PackerTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('evidence_packer'),'evidence packer not implemented')
        return importlib.import_module('evidence_packer')
    def decisions(self):return {a:dict(decision='conditional') for a in ['A','B']}
    def test_whole_root_and_exception_deduplicated(self):
        r=RegistryFixture();got=self.module().assemble_legal(['A','B'],r,self.decisions(),[('GUIDE:M','条件简表')],budget_chars=2000)
        self.assertEqual(set(got['included_article_ids']),{'A','B'})
        self.assertEqual(got['text'].count('主条原句。'),1);self.assertEqual(got['text'].count('例外条件，满足时除外。'),1)
        self.assertEqual(got['text'].count('[来源 S'),1);self.assertIn('效力',got['text'])
    def test_large_exception_never_truncated_or_silently_omitted(self):
        r=RegistryFixture();r.articles['B']['text']='例外条件'*2200
        got=self.module().assemble_legal(['A'],r,self.decisions(),[],budget_chars=500)
        self.assertEqual(got['included_article_ids'],[]);self.assertIn('A',got['next_read_article_ids']);self.assertIn('B',got['next_read_article_ids'])
        self.assertEqual(got['coverage_status'],'partial');self.assertNotIn('主条原句。',got['text'])
    def test_mismatched_roots_are_not_used_as_direct_norms(self):
        d=self.decisions();d['A']['decision']='mismatch'
        got=self.module().assemble_legal(['A','B'],RegistryFixture(),d,[],budget_chars=2000)
        self.assertNotIn('A',got['included_article_ids']);self.assertIn('A',got['scope_excluded_article_ids']);self.assertIn('B',got['included_article_ids'])
    def test_norms_precede_guides_and_budget_is_exact(self):
        got=self.module().assemble_legal(['A'],RegistryFixture(),self.decisions(),[('GUIDE:M','长概览'*2000)],budget_chars=1000)
        self.assertEqual(set(got['included_article_ids']),{'A','B'});self.assertEqual(got['omitted_guide_ids'],['GUIDE:M'])
        self.assertLessEqual(len(got['text']),1000);self.assertEqual(got['used_chars'],len(got['text']))
    def test_invalid_budget_and_unregistered_roots_refused(self):
        m=self.module()
        for roots,budget in [(['A'],True),(['A'],0),(['A'],8001),(['UNKNOWN'],500),(['A','A'],500)]:
            with self.assertRaises(ValueError):m.assemble_legal(roots,RegistryFixture(),self.decisions(),[],budget_chars=budget)

    def test_joint_closure_limit_does_not_request_already_assembled_articles(self):
        r=RegistryFixture();r.articles={str(i):dict(article_id=str(i),source_id='S',text='条文'+str(i)) for i in range(40)}
        r.dependency_closure=lambda roots:dependency_closure(roots,{},r.articles)
        d={a:dict(decision='conditional') for a in r.articles}
        got=self.module().assemble_legal(list(r.articles),r,d,[],budget_chars=8000)
        self.assertEqual(len(got['included_article_ids']),40);self.assertEqual(got['next_read_article_ids'],[])
        self.assertEqual(got['coverage_status'],'complete_for_requested_registered_items')

if __name__=='__main__':unittest.main()
