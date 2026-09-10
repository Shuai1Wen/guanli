#!/usr/bin/env python3
from pathlib import Path
import argparse,json,collections
ap=argparse.ArgumentParser(); ap.add_argument("projects_dir"); ap.add_argument("--output",default="failure_candidates.json"); args=ap.parse_args()
root=Path(args.projects_dir); groups=collections.defaultdict(list)
for f in root.glob("*/FAILURES.jsonl"):
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        try:r=json.loads(line)
        except Exception:continue
        groups[r.get("pattern_code","UNKNOWN")].append(r)
out=[]
for code,rows in sorted(groups.items()):
    projects=sorted({r.get("project") for r in rows if r.get("project")}); sev={r.get("severity") for r in rows}; promotable=(len(projects)>=2 or "P0" in sev)
    out.append({"pattern_code":code,"occurrences":len(rows),"independent_projects":projects,"severities":sorted(sev),"promotable":promotable,"rule_change_status":"CANDIDATE" if promotable else "LOCAL_ONLY","note":"Promotion still requires human/agent review and regression testing; this script never edits Skill rules."})
Path(args.output).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(out,ensure_ascii=False,indent=2))
