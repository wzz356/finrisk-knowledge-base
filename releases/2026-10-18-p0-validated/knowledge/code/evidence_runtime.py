"""Pinned, read-only case/law tools for an external Agentic RAG orchestrator."""
import copy
from pathlib import Path
from runtime_common import read,sha
from knowledge_assets import KnowledgeAssets
from full_reader import FullKnowledgeReader
from scope_table import load_scopes
from scope_selector import validate_scope_facts,match_article
from evidence_packer import assemble_legal
from risk_coverage import analyze_coverage

def _ids(values,known,label):
    if not isinstance(values,(list,tuple)) or any(not isinstance(v,str) or v not in known for v in values) or len(set(values))!=len(values):raise ValueError('unique registered '+label+' required')
    return list(values)

def assemble_policy(assets,scopes,mechanism_ids,*,current_text=None,scope_facts=None,law_budget=4000):
    mechanism_ids=_ids(mechanism_ids,assets.cards,'mechanism IDs')
    facts=validate_scope_facts(scope_facts,current_text)
    decisions={aid:match_article(row,facts) for aid,row in scopes.items()}
    roots=[];guides=[]
    for mid in mechanism_ids:
        card=assets.cards[mid]
        roots.extend(a for a in card['article_ids'] if a not in roots)
        predicates='\n'.join(p['predicate_id']+'：'+p['description'] for p in card['predicates'] if p.get('required_for_risk'))
        guides.append((mid,'[解释性筛查指南 '+mid+'；模型整理，非法律原文、非当前事实]\n'+card['title']+'\n'+card['overview']+'\n需核事实：\n'+predicates+'\n资料覆盖：'+card['coverage']['status']))
    law=assemble_legal(roots,assets.legal,decisions,guides,budget_chars=law_budget)
    return law,facts,decisions

class EvidenceRuntime:
    def __init__(self,root,expected_manifest_sha256,*,case_reader=None):
        self.root=Path(root).resolve();manifest_path=self.root/'contracts/runtime_manifest.json'
        if not expected_manifest_sha256 or sha(manifest_path)!=expected_manifest_sha256:raise ValueError('runtime manifest fingerprint mismatch')
        self.manifest=read(manifest_path)
        if self.manifest.get('schema')!='finrisk-evidence-runtime-v1':raise ValueError('unknown evidence runtime schema')
        for name,meta in self.manifest['files'].items():
            p=(self.root/name).resolve()
            if not p.is_relative_to(self.root) or p.stat().st_size!=meta['bytes'] or sha(p)!=meta['sha256']:raise ValueError('runtime policy/lock changed: '+name)
        self.assets=KnowledgeAssets(self.root/'assets',read(self.root/'contracts/asset_lock.json'))
        self.scopes=load_scopes(self.root/'policy/article_scopes.jsonl',self.manifest['files']['policy/article_scopes.jsonl']['sha256'],self.assets)
        config=self.manifest['full_reader'];reader_root=(self.root/config['root']).resolve()
        if not reader_root.is_relative_to(self.root):raise ValueError('reader root outside runtime')
        if self.assets.versions!=config['versions']:raise ValueError('case/law organization base versions differ')
        self._owns_reader=case_reader is None
        if case_reader is None:self.reader=FullKnowledgeReader(reader_root,config['manifest_sha256'],config['versions'])
        else:
            if not isinstance(case_reader,FullKnowledgeReader) or case_reader.root!=reader_root or case_reader.versions!=config['versions'] or sha(reader_root/'manifest.json')!=config['manifest_sha256']:raise ValueError('persistent reader does not match runtime pin')
            self.reader=case_reader
        if len(self.reader.units)!=110878 or len(self.reader.sources)!=9639:raise ValueError('full corpus reader required')
        for link in self.assets.links:
            if link.get('unit_id') and link['unit_id'] not in self.reader.units:raise ValueError('case guide unit absent from full reader')

    def list_mechanisms(self):return self.assets.list_mechanisms()
    def read_mechanism(self,mechanism_id,level='L0'):return self.assets.read_mechanism(mechanism_id,level)
    def read_article(self,article_id,include_dependencies=True,as_of=None):return self.assets.read_article(article_id,include_dependencies,as_of)
    def read_case(self,unit_id,layer='hit'):return self.reader.read(unit_id,layer=layer)
    def read_span(self,span_id):return self.reader.read_span(span_id)
    def get_coverage(self,mechanism_id):return self.assets.coverage(mechanism_id)
    def coverage(self,mechanism_id):return self.get_coverage(mechanism_id)
    def get_dependencies(self,article_ids,limit=32):return self.assets.legal.dependency_closure(article_ids,limit)
    def get_input_coverage(self,text,*,read_ids=(),checked_ids=()):return analyze_coverage(text,self.assets.cards,read_ids,checked_ids)

    def get_evidence_bundle(self,mechanism_ids,case_unit_ids,*,budget_chars=8000,case_budget=None,law_budget=None,current_text=None,scope_facts=None,checked_mechanism_ids=()):
        if isinstance(mechanism_ids,str):mechanism_ids=[mechanism_ids]
        mids=_ids(mechanism_ids,self.assets.cards,'mechanism IDs');uids=_ids(case_unit_ids,self.reader.units,'case unit IDs')
        _ids(checked_mechanism_ids,self.assets.cards,'caller checked mechanism IDs')
        if type(budget_chars) is not int or not 2<=budget_chars<=8000:raise ValueError('total text budget must be 2..8000 chars')
        case_budget=budget_chars//2 if case_budget is None else case_budget
        law_budget=budget_chars-case_budget if law_budget is None else law_budget
        if type(case_budget) is not int or type(law_budget) is not int or case_budget<0 or law_budget<1 or case_budget+law_budget>budget_chars:raise ValueError('case/law text budgets exceed total')
        law,facts,decisions=assemble_policy(self.assets,self.scopes,mids,current_text=current_text,scope_facts=scope_facts,law_budget=law_budget)
        case_text='';records=[];omitted=[]
        for uid in uids:
            record=self.read_case(uid)
            block='[历史案例 '+record['file_id']+'；单元 '+uid+'；不证明当前输入事实]\n'+record['text']
            proposed=(case_text+'\n\n' if case_text else '')+block
            if len(proposed)<=case_budget:case_text=proposed;records.append(record)
            else:omitted.append(uid)
        coverage=self.get_input_coverage(current_text,read_ids=law['included_guide_ids'],checked_ids=checked_mechanism_ids) if current_text else None
        return dict(schema='finrisk-evidence-bundle-v2',versions=copy.deepcopy(self.assets.versions),case_text=case_text,
            mechanism_ids=mids,requested_case_unit_ids=uids,included_case_unit_ids=[r['unit_id'] for r in records],
            law_and_guide_text=law['text'],included_legal_and_guide_ids=law['included_article_ids']+['GUIDE:'+m for m in law['included_guide_ids']],
            case_records=records,omitted_case_unit_ids=omitted,next_read_case_unit_ids=omitted,
            case_budget_chars=case_budget,case_used_chars=len(case_text),legal_assembly=law,
            requested_mechanism_ids=mids,scope_facts=facts,article_scope_decisions=decisions,input_coverage=coverage,
            used_text_chars=len(case_text)+len(law['text']),budget_chars=budget_chars,
            model_payload_fields=['case_text','legal_assembly.text'],metadata_is_additional_evidence=False,
            current_business_facts_verified=False,full_input_risk_free_supported=False,human_approved=False,
            production_active=False,source_originals_complete=False,
            limitations=['按主体/产品/环节选择阅读范围；未独立核准调用方的语义分类','预算不足整组省略并列出补读ID；不能按资料缺失得出无风险','法规效力/历史适用仍按来源标记；本工具不作法律结论'])
    def close(self):
        if self._owns_reader:self.reader.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
