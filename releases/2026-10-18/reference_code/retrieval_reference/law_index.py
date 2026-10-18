"""Small independent BM25/BGE index; complete paragraphs encode, complete articles return."""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from source_registry import ROOT, OUT, save, sha
from rule_cards import rows
from regulation_tools import fuse, article_dense_scores

PROJECT=Path('C:/Users/11051/Desktop/金融比赛/复赛/FinRisk_复赛改进/src')
MODEL=Path('C:/Users/11051/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620')
INSTRUCTION='为这个句子生成表示以用于检索相关文章：'
INDEX_DIR=OUT/'indexes'


class Encoder:
    def __init__(self):
        os.environ['HF_HUB_OFFLINE']=os.environ['TRANSFORMERS_OFFLINE']='1'
        import numpy as np
        import torch
        from transformers import AutoTokenizer, AutoModel
        self.np,self.torch=np,torch
        if not torch.cuda.is_available(): raise RuntimeError('frozen CUDA runtime required')
        self.tokenizer=AutoTokenizer.from_pretrained(str(MODEL),local_files_only=True,trust_remote_code=False)
        self.model=AutoModel.from_pretrained(str(MODEL),local_files_only=True,trust_remote_code=False,torch_dtype=torch.float16).to('cuda').eval()
        self.audit=[]

    def encode(self,texts,kind,identifiers):
        import numpy as np
        batches=[]
        values=[INSTRUCTION+t if kind=='query' else t for t in texts]
        for start in range(0,len(values),16):
            batch=values[start:start+16]
            lengths=[len(ids) for ids in self.tokenizer(batch,truncation=False)['input_ids']]
            if any(n>512 for n in lengths): raise ValueError('refuse hidden embedding truncation; split by complete legal paragraph or shorten query explicitly')
            tokens=self.tokenizer(batch,padding=True,truncation=False,return_tensors='pt').to('cuda')
            with self.torch.inference_mode():
                hidden=self.model(**tokens).last_hidden_state[:,0]
                vectors=self.torch.nn.functional.normalize(hidden.float(),p=2,dim=1)
            batches.append(vectors.cpu().numpy())
            self.audit.extend(dict(kind=kind,id=i,input_tokens=n,truncated=False) for i,n in zip(identifiers[start:start+16],lengths))
        return np.concatenate(batches).astype('float32')


def semantic_units(articles,views):
    result=[]
    for article in articles:
        key=article['article_id']; header=article['text'].splitlines()[0]
        prefix=re.match(r'.*?条',header)
        prefix=prefix.group(0).strip() if prefix else '第一部分第（一）项'
        for excerpt in views[key]['spans']:
            for match in re.finditer(r'[^\n]+',excerpt['quote']):
                text=match.group().strip()
                if not text: continue
                # Embedding units are locations only; retrieval always expands original full article or registered excerpts.
                result.append(dict(unit_id=f'{key}-P{len(result):04}',article_id=key,
                       article_start=excerpt['start']+match.start(),article_end=excerpt['start']+match.end(),
                       text=prefix+' '+text))
    return result


class LawIndex:
    def __init__(self):
        import numpy as np
        self.np=np
        self.articles=rows(OUT/'articles.jsonl')
        self.views={v['article_id']:v for v in rows(OUT/'article_model_views.jsonl')}
        self.units=rows(INDEX_DIR/'embedding_units.jsonl')
        meta=json.loads((INDEX_DIR/'metadata.json').read_text(encoding='utf-8'))
        for name,digest in meta['sha256'].items():
            if sha((OUT/name).read_bytes())!=digest: raise ValueError('frozen law index changed: '+name)
        self.vectors=np.load(INDEX_DIR/'vectors.npy',allow_pickle=False,mmap_mode='r')
        if self.vectors.shape!=(len(self.units),512): raise ValueError('index dimension mismatch')
        sys.path.insert(0,str(PROJECT))
        from retrieval.sparse import SparseRetrievalIndex,RetrievalDocument
        self.sparse=SparseRetrievalIndex([RetrievalDocument(unit_id=a['article_id'],case_ids=(a['article_id'],),
             text='\n'.join(s['quote'] for s in self.views[a['article_id']]['spans']),source='regulation') for a in self.articles],k1=1.5,b=.75)
        self.encoder=Encoder()

    def search(self,query):
        qv=self.encoder.encode([query],'query',['tool_query'])[0]
        bm=[h.document.unit_id for h in self.sparse.search(query,top_k=len(self.articles))]
        dense=article_dense_scores([u['article_id'] for u in self.units],self.vectors@qv)
        result=fuse([bm,[key for key,score in dense]])
        ranks_bm={key:i for i,key in enumerate(bm,1)}
        ranks_dense={key:i for i,(key,_) in enumerate(dense,1)}
        return [dict(r,bm25_rank=ranks_bm.get(r['article_id']),bge_rank=ranks_dense[r['article_id']]) for r in result]


def build():
    import numpy as np
    articles=rows(OUT/'articles.jsonl'); views={v['article_id']:v for v in rows(OUT/'article_model_views.jsonl')}
    units=semantic_units(articles,views)
    INDEX_DIR.mkdir(exist_ok=True)
    if (INDEX_DIR/'metadata.json').exists(): raise FileExistsError('refuse overwrite complete index')
    if (INDEX_DIR/'vectors.npy').exists():
        if rows(INDEX_DIR/'embedding_units.jsonl')!=units: raise ValueError('partial index inputs changed')
        vectors=np.load(INDEX_DIR/'vectors.npy',allow_pickle=False)
        audit=rows(INDEX_DIR/'embedding_token_audit.jsonl')
        if len(audit)!=len(units) or any(r['truncated'] for r in audit): raise ValueError('partial audit mismatch')
    else:
        encoder=Encoder()
        vectors=encoder.encode([u['text'] for u in units],'document',[u['unit_id'] for u in units])
        np.save(INDEX_DIR/'vectors.npy',vectors,allow_pickle=False)
        save(INDEX_DIR/'embedding_units.jsonl',units,True)
        save(INDEX_DIR/'embedding_token_audit.jsonl',encoder.audit,True)
    files=['articles.jsonl','article_model_views.jsonl','indexes/vectors.npy','indexes/embedding_units.jsonl']
    save(INDEX_DIR/'metadata.json',dict(articles=len(articles),paragraph_units=len(units),shape=list(vectors.shape),
         bm25={'k1':1.5,'b':.75},bge={'model':str(MODEL),'pooling':'CLS','L2_normalized':True,'max_length':512,
         'hidden_truncation':False,'article_aggregation':'maximum paragraph cosine'},rrf={'weights':[1,1],'k':60},
         document_scope='independent regulation index',case_document_vectors_recomputed=0,
         sha256={name:sha((OUT/name).read_bytes()) for name in files}))
    print(json.dumps(dict(articles=len(articles),semantic_paragraphs=len(units),hidden_truncation=0),ensure_ascii=False))


if __name__=='__main__': build()
