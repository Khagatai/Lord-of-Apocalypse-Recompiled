"""Verify an incremental message update changes only explicitly reviewed blocks."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from rgf_archive import parse_index,read_group
from mes_codec import Bundle
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True);parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--allowed',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();private=(ROOT/'private').resolve()
    for path in (args.before,args.after,args.allowed,args.output):
        if not path.resolve().is_relative_to(private):raise ValueError('Keep game-derived checks private')
    allowed={}
    for row in json.loads(args.allowed.read_text())['entries']:
        identity=int(row['resource_id'],16);index=row['message_index']
        if identity>>16!=4 or type(index) is not int or index<0:raise ValueError('Invalid reviewed message identity')
        if index in allowed.setdefault(identity,set()):raise ValueError('Duplicate reviewed message')
        allowed[identity].add(index)
    def load(folder):return parse_index((folder/'REGFILE.RZL').read_bytes(),(folder/'REGFILE.RZP').stat().st_size)
    old,new=load(args.before),load(args.after)
    if len(old)!=len(new):raise ValueError('Group count changed')
    unchanged=0;changed=set();observed=set()
    with (args.before/'REGFILE.RZP').open('rb') as a,(args.after/'REGFILE.RZP').open('rb') as b:
        for first,last in zip(old,new):
            if [id for n,id in first.entries]!=[id for n,id in last.entries]:raise ValueError('Resource membership changed')
            original=read_group(a,first);candidate=read_group(b,last);x=y=0
            for (n,id),(m,_) in zip(first.entries,last.entries):
                before,after=original[x:x+n],candidate[y:y+m];x+=n;y+=m
                if before==after:unchanged+=1;continue
                if id not in allowed:raise ValueError(f'Unreviewed resource changed: {id:08x}')
                left,right=Bundle.parse(before),Bundle.parse(after)
                if left.offsets!=right.offsets or len(left.blocks)!=len(right.blocks):raise ValueError('Message aliases or membership changed')
                indices=allowed[id]
                if max(indices)>=len(left.offsets):raise ValueError('Reviewed message index outside bundle')
                blocks={left.offsets[index] for index in indices}
                for block,(p,q) in enumerate(zip(left.blocks,right.blocks)):
                    if p!=q:
                        if block not in blocks:raise ValueError('Unreviewed message block changed')
                        changed.add((id,block))
                        observed.update((id,index) for index in indices if left.offsets[index]==block)
    expected={(id,index) for id,indices in allowed.items() for index in indices}
    if observed!=expected:raise ValueError('A reviewed edit did not produce a changed block')
    report=dict(scope='reviewed-message-delta-only',reviewed_entries=len(expected),changed_unique_blocks=len(changed),
                unchanged_resource_instances=unchanged,all_other_payloads_byte_identical=True,semantic_quality_validated=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
