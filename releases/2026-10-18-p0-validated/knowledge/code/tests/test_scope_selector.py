import importlib
import importlib.util
import unittest

class ScopeSelectorTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scope_selector'),'scope selector not implemented')
        return importlib.import_module('scope_selector')

    def facts(self,product='universal_life'):
        text='本公司是一家保险公司。这是一份万能型保险。合同订立后由公司电话回访。'
        values={'actor':('insurer','保险公司'),'product':(product,'万能型保险'),'stage':('post_sale_review','合同订立后')}
        return text,{axis:dict(value=value,origin='current_input',quote=quote,start=text.index(quote),end=text.index(quote)+len(quote)) for axis,(value,quote) in values.items()}

    def scope(self):
        return dict(article_id='A',actor_scope=['insurer'],product_scope=['universal_life'],stage_scope=['post_sale_review'],scope_status='direct_literal')

    def test_explicit_scope_matches_but_never_verifies_business_facts(self):
        m=self.module();text,facts=self.facts();validated=m.validate_scope_facts(facts,text)
        got=m.match_article(self.scope(),validated)
        self.assertEqual(got['decision'],'matched');self.assertFalse(got['current_business_facts_verified'])

    def test_universal_requirement_is_not_direct_support_for_investment_linked(self):
        m=self.module();text,facts=self.facts();text=text.replace('万能型保险','投资连结型保险');q='投资连结型保险'
        facts['product'].update(value='investment_linked',quote=q,start=text.index(q),end=text.index(q)+len(q))
        # Rebind later quotation after the longer product name.
        q='合同订立后';facts['stage'].update(start=text.index(q),end=text.index(q)+len(q))
        got=m.match_article(self.scope(),m.validate_scope_facts(facts,text))
        self.assertEqual(got['decision'],'mismatch');self.assertIn('product',got['mismatched_axes'])

    def test_agent_and_insurer_norms_are_distinguished(self):
        m=self.module();text='本公司是保险专业代理机构。';q='保险专业代理机构'
        facts=m.validate_scope_facts({'actor':dict(value='insurance_agent',origin='current_input',quote=q,start=text.index(q),end=text.index(q)+len(q))},text)
        self.assertEqual(m.match_article(self.scope(),facts)['decision'],'mismatch')
        scope=self.scope();scope['actor_scope']=['insurance_agent','insurance_broker']
        self.assertEqual(m.match_article(scope,facts)['decision'],'conditional')

    def test_unknown_or_general_scope_is_conditional_not_discarded(self):
        m=self.module();facts=m.validate_scope_facts({},None)
        self.assertEqual(m.match_article(self.scope(),facts)['decision'],'conditional')
        scope=self.scope();scope.update(actor_scope=['general'],product_scope=['general'],stage_scope=['general'],scope_status='broader')
        text,raw=self.facts();self.assertEqual(m.match_article(scope,m.validate_scope_facts(raw,text))['decision'],'conditional')

    def test_direct_actor_can_exclude_even_when_stage_is_general(self):
        m=self.module();text='本公司是保险专业代理机构。';q='保险专业代理机构'
        facts=m.validate_scope_facts({'actor':dict(value='insurance_agent',origin='current_input',quote=q,start=text.index(q),end=text.index(q)+len(q))},text)
        scope=self.scope();scope.update(stage_scope=['general'],scope_status='conditional',assertion_basis={'actor':'direct_literal','product':'direct_literal','stage':'assistant_interpretation'})
        self.assertEqual(m.match_article(scope,facts)['mismatched_axes'],['actor'])
        scope['assertion_basis']['actor']='assistant_interpretation'
        self.assertEqual(m.match_article(scope,facts)['decision'],'conditional')

    def test_disclosure_stage_can_overlap_pre_sale_or_review(self):
        m=self.module();scope=self.scope();scope.update(stage_scope=['information_disclosure'],assertion_basis={'actor':'direct_literal','product':'direct_literal','stage':'direct_literal'})
        for value,quote in [('pre_sale','售前'),('post_sale_review','回访')]:
            text='保险公司在'+quote+'介绍万能型保险。'
            raw={axis:dict(value=v,origin='current_input',quote=q,start=text.index(q),end=text.index(q)+len(q)) for axis,v,q in [('actor','insurer','保险公司'),('product','universal_life','万能型保险'),('stage',value,quote)]}
            with self.subTest(stage=value):self.assertEqual(m.match_article(scope,m.validate_scope_facts(raw,text))['decision'],'conditional')

    def test_historical_or_bad_literal_scope_evidence_refused(self):
        m=self.module();text,raw=self.facts()
        for field,value in [('origin','historical_case'),('start',True),('end',999),('quote','虚构原句'),('value','invented_product')]:
            facts={k:dict(v) for k,v in raw.items()};facts['product'][field]=value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):m.validate_scope_facts(facts,text)
        with self.assertRaises(ValueError):m.validate_scope_facts(raw,None)

if __name__=='__main__':unittest.main()
