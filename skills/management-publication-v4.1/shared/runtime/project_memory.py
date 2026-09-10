#!/usr/bin/env python3
from pathlib import Path
import argparse, json, hashlib, datetime

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
REQ = ["PAPER_STATE.md","CONCEPT_LEDGER.md","LITERATURE_LEDGER.md","EVIDENCE_LEDGER.md","FAILURE_MEMORY.md"]

def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

def state_hash(project):
    p=project/"PAPER_STATE.md"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def init_project(args):
    p=Path(args.project_dir); p.mkdir(parents=True,exist_ok=True); (p/"runs").mkdir(exist_ok=True)
    mapping={"PAPER_STATE_TEMPLATE.md":"PAPER_STATE.md","CONCEPT_LEDGER_TEMPLATE.md":"CONCEPT_LEDGER.md","LITERATURE_LEDGER_TEMPLATE.md":"LITERATURE_LEDGER.md","EVIDENCE_LEDGER_TEMPLATE.md":"EVIDENCE_LEDGER.md","FAILURE_MEMORY_TEMPLATE.md":"FAILURE_MEMORY.md"}
    for src,dst in mapping.items():
        d=p/dst
        if not d.exists():
            text=(TEMPLATES/src).read_text(encoding="utf-8")
            if dst=="PAPER_STATE.md": text=text.replace("PROJECT_NAME:",f"PROJECT_NAME: {args.name}")
            d.write_text(text,encoding="utf-8")
    (p/"FAILURES.jsonl").touch(exist_ok=True); print(p)

def start_run(args):
    p=Path(args.project_dir); (p/"runs").mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); run_id=args.run_id or f"{stamp}-{args.skill}"
    rec={"run_id":run_id,"started_at":now(),"skill":args.skill,"input_summary":args.input_summary,"state_hash_before":state_hash(p),"status":"OPEN"}
    (p/"runs"/f"{run_id}.json").write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding="utf-8")
    (p/"runs"/f"{run_id}.md").write_text(f"# RUN {run_id}\n\nDate: {rec['started_at']}\nSkill: {args.skill}\nInput summary: {args.input_summary}\nState hash before: {rec['state_hash_before']}\nDecision:\nChanged:\nNew risks:\nNext action:\nState hash after:\nFailure IDs:\n",encoding="utf-8")
    print(run_id)

def finish_run(args):
    p=Path(args.project_dir); jp=p/"runs"/f"{args.run_id}.json"
    if not jp.exists(): raise SystemExit(f"Run not found: {args.run_id}")
    rec=json.loads(jp.read_text(encoding="utf-8")); rec.update({"finished_at":now(),"decision":args.decision,"changed":args.changed,"new_risks":args.new_risks,"next_action":args.next_action,"failure_ids":args.failure_id or [],"state_hash_after":state_hash(p),"status":"CLOSED"})
    jp.write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding="utf-8")
    (p/"runs"/f"{args.run_id}.md").write_text(f"# RUN {args.run_id}\n\nDate: {rec['started_at']} → {rec['finished_at']}\nSkill: {rec['skill']}\nInput summary: {rec['input_summary']}\nState hash before: {rec['state_hash_before']}\nDecision: {args.decision}\nChanged: {args.changed}\nNew risks: {args.new_risks}\nNext action: {args.next_action}\nState hash after: {rec['state_hash_after']}\nFailure IDs: {', '.join(args.failure_id or [])}\n",encoding="utf-8"); print(jp)

def log_failure(args):
    p=Path(args.project_dir); p.mkdir(parents=True,exist_ok=True); fpath=p/"FAILURES.jsonl"; existing=[]
    if fpath.exists():
        for line in fpath.read_text(encoding="utf-8").splitlines():
            try: existing.append(json.loads(line))
            except: pass
    fid=args.failure_id or f"F-{datetime.datetime.now().strftime('%Y%m%d')}-{len(existing)+1:03d}"
    rec={"failure_id":fid,"recorded_at":now(),"project":p.name,"pattern_code":args.pattern_code,"severity":args.severity,"skill":args.skill,"summary":args.summary,"cause":args.cause,"prevention":args.prevention,"trigger":args.trigger,"evidence":args.evidence,"status":"OPEN"}
    with fpath.open("a",encoding="utf-8") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
    m=p/"FAILURE_MEMORY.md"
    if not m.exists(): m.write_text((TEMPLATES/"FAILURE_MEMORY_TEMPLATE.md").read_text(encoding="utf-8"),encoding="utf-8")
    with m.open("a",encoding="utf-8") as f: f.write(f"\n### {fid}\nPattern code: {args.pattern_code}\nSeverity: {args.severity}\nSkill: {args.skill}\nWhat happened: {args.summary}\nWhy it happened: {args.cause}\nPreventive rule: {args.prevention}\nFuture trigger: {args.trigger}\nEvidence: {args.evidence}\nStatus: OPEN\n")
    print(fid)

def validate(args):
    p=Path(args.project_dir); missing=[x for x in REQ if not (p/x).exists()]
    if not (p/"runs").is_dir(): missing.append("runs/")
    if not (p/"FAILURES.jsonl").exists(): missing.append("FAILURES.jsonl")
    state=(p/"PAPER_STATE.md").read_text(encoding="utf-8") if (p/"PAPER_STATE.md").exists() else ""; fields=["RESEARCH_OBJECT","ACADEMIC_POSITION","PAPER_THESIS","THEORY_AND_MEASUREMENT","EVIDENCE","STATE_CONTROL"]; missing_fields=[x for x in fields if f"## {x}" not in state]
    out={"project":str(p),"missing":missing,"missing_state_sections":missing_fields,"valid":not missing and not missing_fields}; print(json.dumps(out,ensure_ascii=False,indent=2)); return 0 if out["valid"] else 1

ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
p=sub.add_parser("init"); p.add_argument("project_dir"); p.add_argument("--name",required=True); p.set_defaults(fn=init_project)
p=sub.add_parser("start-run"); p.add_argument("project_dir"); p.add_argument("--skill",required=True); p.add_argument("--input-summary",required=True); p.add_argument("--run-id"); p.set_defaults(fn=start_run)
p=sub.add_parser("finish-run"); p.add_argument("project_dir"); p.add_argument("run_id"); p.add_argument("--decision",required=True); p.add_argument("--changed",default=""); p.add_argument("--new-risks",default=""); p.add_argument("--next-action",default=""); p.add_argument("--failure-id",action="append"); p.set_defaults(fn=finish_run)
p=sub.add_parser("log-failure"); p.add_argument("project_dir"); p.add_argument("--pattern-code",required=True); p.add_argument("--severity",choices=["P0","P1","P2"],required=True); p.add_argument("--skill",required=True); p.add_argument("--summary",required=True); p.add_argument("--cause",required=True); p.add_argument("--prevention",required=True); p.add_argument("--trigger",required=True); p.add_argument("--evidence",default=""); p.add_argument("--failure-id"); p.set_defaults(fn=log_failure)
p=sub.add_parser("validate"); p.add_argument("project_dir"); p.set_defaults(fn=validate)
args=ap.parse_args(); rc=args.fn(args)
if isinstance(rc,int): raise SystemExit(rc)
