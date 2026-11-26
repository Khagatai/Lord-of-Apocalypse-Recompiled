"""Gate two routine scheduler debug prints in an identity-checked private copy."""
import hashlib
from pathlib import Path

PINNED_SCHED_SHA256='218d64e3300f27da21bc7dfe464270bd9d65aa699e632eaf67e657943720dcfb'
SLEEP='    fprintf(stderr, "DEBUG_SLEEP: thread=0x%x wakeups=%d state=%d\\n", t->uid, t->wakeups, t->state);'
WAKE='''        fprintf(stderr, "DEBUG_WAKEUP: target=0x%x sleeping=%d state=%d wait_obj=0x%x wakeups=%d\\n",
                uid, t->sleeping, t->state, t->wait_obj, t->wakeups);'''

def render(source):
    if hashlib.sha256(source).hexdigest()!=PINNED_SCHED_SHA256:raise ValueError('Pinned scheduler source hash mismatch')
    text=source.decode('utf-8')
    for old in (SLEEP,WAKE):
        if text.count(old)!=1:raise ValueError('Scheduler diagnostic anchor changed')
        indent=old[:len(old)-len(old.lstrip())]
        # Match the pinned SleepThreadCB diagnostic switch; no scheduler branch,
        # clock, priority, wakeup count or error-return expression changes.
        new=indent+'static int loa_wakelog=-1;\n'+indent+'if(sched_env_switch(&loa_wakelog,"SR_WAKELOG")) {\n'+old+'\n'+indent+'}'
        text=text.replace(old,new)
    return text

def prepare(framework,output):
    data=render((Path(framework)/'src/rt/sched.c').read_bytes()).encode()
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    if not output.exists() or output.read_bytes()!=data:output.write_bytes(data)
    return dict(upstream_sha256=PINNED_SCHED_SHA256,generated_sha256=hashlib.sha256(data).hexdigest(),
        adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='routine diagnostic gating only; scheduler decisions unchanged')
