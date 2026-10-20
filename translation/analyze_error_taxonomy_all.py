# Coarse MLCL-style error breakdown for all 14 open-weights models, HI and TA.
# Same method as translation/analyze_tamil_error_taxonomy.py, generalised; read-only over score files.
import json,re,sys
from collections import Counter
from pathlib import Path
SCRIPT={'hi':re.compile(r'[ऀ-ॿ]'),'ta':re.compile(r'[஀-௿]')}
FUNC={"multiple_function_checker:wrong_count","simple_function_checker:wrong_func_name","parallel_function_checker:wrong_count"}
SYN={"ast_decoder:decoder_failed","ast_decoder:decoder_wrong_output_type"}
MODELS=["Qwen_Qwen3-1.7B-FC","Qwen_Qwen3-8B-FC","Qwen_Qwen3-32B-FC","google_gemma-3-4b-it","google_gemma-3-12b-it","google_gemma-3-27b-it","tiiuae_Falcon3-3B-Instruct-FC","tiiuae_Falcon3-7B-Instruct-FC","tiiuae_Falcon3-10B-Instruct-FC","meta-llama_Llama-3.2-3B-Instruct-FC","meta-llama_Llama-3.1-8B-Instruct-FC","MadeAgents_Hammer2.1-0.5b","MadeAgents_Hammer2.1-1.5b","MadeAgents_Hammer2.1-7b"]
def load(p): return [json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
def has(v,rx):
    if isinstance(v,str): return bool(rx.search(v))
    if isinstance(v,(list,tuple)): return any(has(x,rx) for x in v)
    if isinstance(v,dict): return any(has(k,rx) or has(x,rx) for k,x in v.items())
    return False
prompts={l:{e['id']:e for e in load(f'bfcl_eval/data/BFCL_v4_multiple_{l}.json')} for l in ['hi','ta']}
out={}
for m in MODELS:
    en=load(f'score/{m}/non_live/BFCL_v4_multiple_score.json'); en_fail={e['id'] for e in en[1:]}
    out[m]={}
    for l in ['hi','ta']:
        s=load(f'score/{m}/non_live/BFCL_v4_multiple_{l}_score.json'); fails=s[1:]
        c=Counter(); paired=0
        for e in fails:
            et=e['error_type']
            if et in SYN: b='syntax'
            elif et in FUNC: b='function'
            elif has(e.get('model_result_decoded') or [],SCRIPT[l]): b='lang_mismatch'
            else: b='other_value'
            c[b]+=1
            p=prompts[l][e['id']]; oid=p.get('original_id', e['id'].replace(f'_{l}_','_'))
            if oid not in en_fail: paired+=1
        out[m][l]={'n_fail':len(fails),**c,'en_ok_same_q':paired}
json.dump(out,open(sys.argv[1],'w'),indent=1)
for m in MODELS:
    print(m[:28].ljust(28),' | '.join(f"{l}: F{out[m][l]['n_fail']:3d} syn{out[m][l].get('syntax',0):3d} fn{out[m][l].get('function',0):3d} LM{out[m][l].get('lang_mismatch',0):3d} val{out[m][l].get('other_value',0):3d} enOK{out[m][l]['en_ok_same_q']:3d}" for l in ['hi','ta']))
