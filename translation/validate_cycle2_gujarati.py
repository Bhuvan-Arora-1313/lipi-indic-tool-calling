import json, openpyxl
from collections import Counter
D="data/human_review/"
FILES={"Samarth":(D+"Gujarati_review_Samarth_Patel.xlsx","Gujarati Review Samarth Patel"),
       "Dhruv":(D+"Gujarati Review - Dhruv Kunvarani.xlsx","Dhruv Kunvarani Gujarati Review")}
SENT={"Samarth":"data/review_sheets/cycle2/Gujarati_Cycle2_Samarth.xlsx","Dhruv":"data/review_sheets/cycle2/Gujarati_Cycle2_Dhruv.xlsx"}
H=["base_id","English Source","Translation","Automated check","Correctness","Number/Value Issue","Wrong Word/Mistranslation","Grammar Error","Meaning Changed","Missing Content","Added Content","Script/Formatting","Invalid Swap","Other","Corrected version","Notes"]
B3H=["base_id","English Source","Original Translation (you marked this Correct)","Other reviewer's proposed fix","Other reviewer's reasoning","Decision","Corrected version (only if 'Neither')","Notes"]
B4H=["base_id","English Source","Original Translation (both flagged Incorrect)","Version A","Version B","Decision","Corrected version (only if 'Neither')","Notes"]
VB3={"Original stands","Accept fix","Neither - write new"}; VB4={"Version A","Version B","Neither - write new"}
norm=lambda s:"" if s is None else str(s).rstrip()
key=lambda b:int(b.rsplit("_",1)[-1])
problems=[]; notes=[]
def rows(ws,hdr):
    out={}; extra=0
    for r in range(2,ws.max_row+1):
        v=[ws.cell(row=r,column=c).value for c in range(1,len(hdr)+1)]
        if v[0]:
            if v[0] in out: problems.append(f"{ws.title}: duplicate {v[0]}")
            out[v[0]]=dict(zip(hdr,v))
        elif any(x not in (None,"") for x in v): extra+=1
    for r in range(1,ws.max_row+1):
        for c in range(len(hdr)+1,ws.max_column+1):
            if ws.cell(row=r,column=c).value not in (None,""): problems.append(f"{ws.title}: stray value at row {r} col {c}: {ws.cell(row=r,column=c).value!r}"[:160])
    if extra: problems.append(f"{ws.title}: {extra} non-empty rows without base_id")
    return out
# ---------- A. Cycle 1 integrity ----------
c1={}; wbs={}
for rv,(f,sh) in FILES.items():
    wbs[rv]=openpyxl.load_workbook(f,data_only=True); c1[rv]=rows(wbs[rv][sh],H)
    bad=[b for b,x in c1[rv].items() if x["Correctness"] not in ("Correct","Incorrect")]
    print(f"[C1] {rv}: {len(c1[rv])} rows; invalid/empty Correctness: {bad}")
    if len(c1[rv])!=200 or bad: problems.append(f"C1 {rv}: rows={len(c1[rv])} bad={bad}")
if set(c1["Samarth"])!=set(c1["Dhruv"]): problems.append("C1 id sets differ")
cls=json.load(open("data/reviews/gujarati_cycle1_classification.json"))
def bucket(b):
    a,d=c1["Samarth"][b],c1["Dhruv"][b]
    if a["Correctness"]=="Correct" and d["Correctness"]=="Correct": return 1
    if a["Correctness"]=="Incorrect" and d["Correctness"]=="Incorrect": return 2 if norm(a["Corrected version"])==norm(d["Corrected version"]) else 4
    return 3
now={b:bucket(b) for b in c1["Samarth"]}
diff={b:(cls["buckets"][b],now[b]) for b in now if cls["buckets"][b]!=now[b]}
print(f"[C1] buckets recomputed {dict(sorted(Counter(now.values()).items()))} vs saved {cls['bucket_counts']}; changed items: {diff}")
if diff: problems.append(f"C1 bucket changes: {diff}")
s154=c1["Samarth"]["multiple_154"]["English Source"]; print("[C1] multiple_154 fingerprint (Samarth copy starts):", str(s154)[:40])
for b,v in cls["prefer_dhruv_better_translation"].items():
    if now[b]!=1 or norm(c1["Dhruv"][b]["Corrected version"])!=v["final_text"]: problems.append(f"prefer-Dhruv item {b} no longer matches")
print("[C1] prefer-Dhruv 6 items:", "OK" if not any("prefer-Dhruv" in p for p in problems) else "CHANGED")
# ---------- B. Cycle 2 ----------
assign=json.load(open("data/reviews/gujarati_cycle2_bucket4_assignment.json"))["bucket4_assignment"]
b3_exp={b for b,v in cls["buckets"].items() if v==3}; b4_exp={b for b,v in cls["buckets"].items() if v==4}
got3={}; got4={}; dec3=Counter(); dec4=Counter(); selfpick=Counter()
for rv in FILES:
    sent=openpyxl.load_workbook(SENT[rv],data_only=True)
    for tab,hdr,valid,store in [("Bucket 3 - Asymmetric",B3H,VB3,got3),("Bucket 4 - Conflicting Fixes",B4H,VB4,got4)]:
        ret=rows(wbs[rv][tab],hdr); snt=rows(sent[tab],hdr)
        if set(ret)!=set(snt): problems.append(f"{rv}/{tab}: ids differ from sent sheet: missing {set(snt)-set(ret)} extra {set(ret)-set(snt)}")
        for b,x in sorted(ret.items(),key=lambda t:key(t[0])):
            store[b]=(rv,x)
            for col in hdr[:5]:
                if norm(x[col])!=norm(snt.get(b,{}).get(col)): problems.append(f"{rv}/{b}: read-only column '{col}' was edited")
            d=x["Decision"]; newtxt=norm(x["Corrected version (only if 'Neither')"])
            if d not in valid: problems.append(f"{rv}/{b} ({tab[:8]}): invalid/empty Decision {d!r}"); continue
            (dec3 if valid is VB3 else dec4)[d]+=1
            if d=="Neither - write new" and not newtxt: problems.append(f"{rv}/{b}: 'Neither' but no corrected text")
            if d!="Neither - write new" and newtxt: notes.append(f"{rv}/{b}: decision {d!r} but corrected text also filled: {newtxt[:80]}")
            if d=="Accept fix" and not norm(x["Other reviewer's proposed fix"]): problems.append(f"{rv}/{b}: 'Accept fix' but the proposed fix is empty")
            if x["Notes"]: notes.append(f"{rv}/{b} note: {str(x['Notes'])[:120]}")
            if valid is VB4:
                a=assign[b]
                if a["adjudicator"]!=rv: problems.append(f"{b}: assigned to {a['adjudicator']} but answered by {rv}")
                if d in ("Version A","Version B"):
                    author=a["version_a_author"] if d=="Version A" else a["version_b_author"]
                    selfpick["own" if author==rv else "other"]+=1
        # also verify sent sheet content == current Cycle 1 content
        for b,x in snt.items():
            if valid is VB3:
                own=rv; other="Dhruv" if rv=="Samarth" else "Samarth"
                if norm(x[hdr[2]])!=norm(c1[own][b]["Translation"]) or norm(x[hdr[3]])!=norm(c1[other][b]["Corrected version"]): problems.append(f"{b}: Cycle 1 text changed since Cycle 2 sheet was built")
            else:
                a=assign[b]
                if norm(x["Version A"])!=norm(c1[a["version_a_author"]][b]["Corrected version"]) or norm(x["Version B"])!=norm(c1[a["version_b_author"]][b]["Corrected version"]): problems.append(f"{b}: Cycle 1 fixes changed since Cycle 2 sheet was built")
print(f"[C2] bucket 3: {len(got3)}/{len(b3_exp)} items, ids match: {set(got3)==b3_exp}; by adjudicator {Counter(v[0] for v in got3.values())}; decisions {dict(dec3)}")
print(f"[C2] bucket 4: {len(got4)}/{len(b4_exp)} items, ids match: {set(got4)==b4_exp}; by adjudicator {Counter(v[0] for v in got4.values())}; decisions {dict(dec4)}; picked own vs other fix: {dict(selfpick)}")
if set(got3)!=b3_exp or set(got4)!=b4_exp: problems.append("C2 item sets do not match classification")
print("\nPROBLEMS:" if problems else "\nPROBLEMS: none"); [print(" -",p) for p in problems]
print("\nNOTES / anomalies to look at:" if notes else "\nNOTES: none"); [print(" -",n) for n in notes]
