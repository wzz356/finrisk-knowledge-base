import copy
import hashlib
import importlib
import json
import unittest
from types import SimpleNamespace

try:
    rv = importlib.import_module('run_v2')
except ModuleNotFoundError:
    rv = None


def unit(uid='u1', fid='F000001', cases=None):
    return {'unit_id':uid,'file_id':fid,'case_id':fid+':c1','case_ids':cases or [fid+':c1'],
            'behavior_id':fid+':b1','behavior_ids':[fid+':b1'],'text':'短检索事实',
            'source_text':'短检索事实','prefix':'','source_spans':[{'start':0,'end':5}],
            'context_text':'短检索事实。必要条件及监管回应。','context_source_text':'短检索事实。必要条件及监管回应。',
            'context_spans':[{'start':0,'end':17}],'associations':[]}


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class AdapterRules(unittest.TestCase):
    def feature(self,name):
        self.assertIsNotNone(rv,'V2 adapter module must exist')
        f=getattr(rv,name,None)
        self.assertTrue(callable(f),'V2 adapter is missing '+name)
        return f

    def test_shared_unit_retains_every_case_and_max_score(self):
        f=self.feature('aggregate')
        u=unit(cases=['F000001:c1','F000001:c2']);v=unit('u2');v['text']='另一事实'
        cases,files=f([{'unit_id':'u1','score':3},{'unit_id':'u2','score':7}],{'u1':u,'u2':v})
        self.assertEqual({x['case_id'] for x in cases},{'F000001:c1','F000001:c2'})
        self.assertEqual(files[0]['score'],7)
        self.assertEqual(set(files[0]['case_ids']),{'F000001:c1','F000001:c2'})

    def test_returned_context_is_independent_of_short_model_input(self):
        f=self.feature('aggregate');u=unit()
        _,files=f([{'unit_id':'u1','score':1}],{'u1':u})
        self.assertEqual(files[0]['text'],u['context_text'])
        self.assertEqual(files[0]['source_text'],u['context_source_text'])
        self.assertEqual(files[0]['source_spans'],u['context_spans'])
        self.assertEqual(files[0]['indexed_text'],u['text'])
        self.assertEqual(files[0]['indexed_source_spans'],u['source_spans'])

    def test_returned_context_preserves_qualifier_links(self):
        u=unit();u['qualifier_source_links']=[{'case_id':'stable-c1','behavior_id':'stable-b1',
            'field':'negations','quote':'必要条件','spans':[{'start':6,'end':10}],
            'status':'candidate_behavior_link_not_verified'}]
        _,files=self.feature('aggregate')([{'unit_id':'u1','score':1}],{'u1':u})
        self.assertEqual(files[0]['qualifier_source_links'],u['qualifier_source_links'])

    def test_qualifier_link_ids_match_normalized_associations(self):
        f=self.feature('normalize_unit_links');u=unit()
        u['associations']=[{'case_id':'F000001:c1','behavior_id':'F000001:b1','case_key':'c1','behavior_key':'b1'}]
        u['qualifier_source_links']=[{'case_id':'F000001:c1','behavior_id':'F000001:b1','field':'conditions','quote':'条件'}]
        f(u,{'c1':'stable-c1'},{'b1':'stable-b1'})
        self.assertEqual(u['qualifier_source_links'][0]['case_id'],'stable-c1')
        self.assertEqual(u['qualifier_source_links'][0]['behavior_id'],'stable-b1')
        self.assertEqual(u['qualifier_source_links'][0]['original_behavior_id'],'F000001:b1')

    def test_normalization_does_not_mutate_shared_projection_links(self):
        from projection_v2 import project_document
        text='机构提供办理服务。\n\n客户资料齐全时方可办理。'
        draft={'file_id':'F000001','cases':[{'local_key':'c1','party_name':'机构','party_quote':'机构'}],
            'behaviors':[{'local_key':'b1','case_key':'c1','actor_role':'institution_violation',
                'finding_quote':'机构提供办理服务。','conditions':[{'quote':'客户资料齐全时方可办理。'}]}]}
        units,_=project_document('F000001',text,draft,'sha')
        for u in units:
            self.feature('normalize_unit_links')(u,{'c1':'stable-c1'},{'b1':'stable-b1'})
        links=[x for u in units for x in u.get('qualifier_source_links',[])]
        self.assertTrue(links)
        self.assertTrue(all(x['behavior_id']=='stable-b1' for x in links))
        nested=[x for u in units for a in u['associations'] for x in a.get('qualifier_source_links',[])]
        self.assertTrue(nested)
        self.assertTrue(all(x['case_id']=='stable-c1' and x['behavior_id']=='stable-b1' for x in nested))

    def test_fallback_and_duplicate_hits_do_not_invent_cases(self):
        f=self.feature('aggregate');u=unit();u['case_id']='F000001:SOURCE';u['case_ids']=[]
        cases,files=f([{'unit_id':'u1','score':1},{'unit_id':'u1','score':1}],{'u1':u})
        self.assertEqual(cases,[]);self.assertEqual(len(files),1);self.assertEqual(files[0]['case_ids'],[])

    def test_event_view_preserves_all_files_and_promotes_distinct_events(self):
        f=self.feature('diversify_events')
        files=[{'file_id':x,'score':10-i,'rank':i+1} for i,x in enumerate(['A','B','C','D'])]
        result=f(files,{'A':'event1','B':'event1','C':'event2'})
        self.assertEqual([x['file_id'] for x in result],['A','C','D','B'])
        self.assertEqual({x['file_id']:x['score'] for x in result},{x['file_id']:x['score'] for x in files})
        self.assertEqual(result[3]['rank'],4)

    def test_run_rejects_scope_and_population_mismatch(self):
        check=self.feature('validate_run_scope')
        with self.assertRaises(ValueError):
            check(SimpleNamespace(scope='remaining8509',expected_files=9639),{'scope':'all','source_files':9639})
        with self.assertRaises(ValueError):
            check(SimpleNamespace(scope='remaining8509',expected_files=8509),{'scope':'remaining8509','source_files':9639})
        check(SimpleNamespace(scope='remaining8509',expected_files=8509),{'scope':'remaining8509','source_files':8509})

    def test_punctuation_only_units_are_separate_auditable_records(self):
        split=self.feature('partition_searchable_units')
        units=[dict(unit('slash'),text='/'),dict(unit('plus'),text='（+）'),
               dict(unit('real'),text='客户资料齐全时方可办理。'),dict(unit('amount'),text='0.3万元')]
        original=copy.deepcopy(units);searchable,excluded=split(units)
        self.assertEqual([u['unit_id'] for u in searchable],['real','amount'])
        self.assertEqual([u['unit_id'] for u in excluded],['slash','plus'])
        self.assertEqual(units,original)

    def overlay_fixture(self):
        draft={'file_id':'F000001','cases':[{'local_key':'c1','party_name':'甲公司'}],
               'behaviors':[{'local_key':'b1','case_key':'c1','actor_role':'institution_violation',
                             'finding_quote':'销售误导','risk_tags':[],'zero_tag_reason':'旧门槛'}]}
        source={'full_text':'甲公司销售误导。','text_sha256':hashlib.sha256('甲公司销售误导。'.encode()).hexdigest()}
        wrapper={'draft':draft,'draft_json_sha256':digest(draft)}
        updated=copy.deepcopy(draft);updated.update(label_policy_version='recall-v2',semantic_status='candidate',human_review_status='pending')
        updated['behaviors'][0]['risk_tags']=[{'tag':'销售误导','quotes':['销售误导'],'match_basis':'explicit',
             'assignment_scope':'behavior_context','limitations':[]}]
        updated['behaviors'][0]['zero_tag_reason']=None
        row={'file_id':'F000001','base_draft_json_sha256':digest(draft),'base_text_sha256':source['text_sha256'],
             'updated_draft':updated,'overlay_kind':'label_migration'}
        return wrapper,source,row

    def test_label_migration_retains_every_fact(self):
        f=self.feature('apply_overlays');c,s,row=self.overlay_fixture()
        updated=f({'F000001':c},{'F000001':s},[row])
        self.assertEqual(updated['F000001']['cases'],c['draft']['cases'])
        self.assertEqual(c['draft']['behaviors'][0]['risk_tags'],[])

    def test_label_migration_rejects_fact_rewrite(self):
        f=self.feature('apply_overlays');c,s,row=self.overlay_fixture();row['updated_draft']['cases'][0]['party_name']='乙公司'
        with self.assertRaisesRegex(ValueError,'fact|事实'):
            f({'F000001':c},{'F000001':s},[row])

    def test_overlay_rejects_stale_source_and_faked_human_approval(self):
        f=self.feature('apply_overlays');c,s,row=self.overlay_fixture();row['base_text_sha256']='bad'
        with self.assertRaises(ValueError):f({'F000001':c},{'F000001':s},[row])
        row['base_text_sha256']=s['text_sha256'];row['updated_draft']['human_review_status']='approved'
        with self.assertRaises(ValueError):f({'F000001':c},{'F000001':s},[row])


if __name__=='__main__':
    unittest.main()
