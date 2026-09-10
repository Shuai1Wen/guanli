#!/usr/bin/env python3
from pathlib import Path
import re, json, yaml, sys
ROOT=Path(__file__).resolve().parents[1]
REG=json.loads((ROOT/'registry.json').read_text(encoding='utf-8'))
errors=[]
for rec in REG['skills']:
    d=ROOT/rec['path']; smd=d/'SKILL.md'
    if not smd.exists(): errors.append(f"{rec['name']}: missing SKILL.md"); continue
    txt=smd.read_text(encoding='utf-8')
    m=re.match(r'^---\n(.*?)\n---\n',txt,re.S)
    if not m: errors.append(f"{rec['name']}: invalid frontmatter"); continue
    fm=yaml.safe_load(m.group(1))
    if set(fm)!={'name','description'}: errors.append(f"{rec['name']}: frontmatter keys")
    if fm.get('name')!=rec['name']: errors.append(f"{rec['name']}: name mismatch")
    if not (d/'agents'/'openai.yaml').exists(): errors.append(f"{rec['name']}: missing agents/openai.yaml")
    if not (d/'references'/'project-memory.md').exists(): errors.append(f"{rec['name']}: missing project-memory reference")
    for ref in re.findall(r'\]\((references/[^)]+)\)',txt):
        if not (d/ref).exists(): errors.append(f"{rec['name']}: missing {ref}")
    if (d/'README.md').exists(): errors.append(f"{rec['name']}: README inside skill folder")
    if txt.count('\n')+1>500: errors.append(f"{rec['name']}: SKILL.md >500 lines")
for p in (ROOT/'projects').iterdir():
    if p.is_dir():
        for req in ['PAPER_STATE.md','CONCEPT_LEDGER.md','LITERATURE_LEDGER.md','EVIDENCE_LEDGER.md','FAILURE_MEMORY.md','FAILURES.jsonl']:
            if not (p/req).exists(): errors.append(f"{p.name}: missing {req}")
        if not (p/'runs').is_dir(): errors.append(f"{p.name}: missing runs/")
print(json.dumps({'valid':not errors,'errors':errors,'skills':len(REG['skills'])},ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)
