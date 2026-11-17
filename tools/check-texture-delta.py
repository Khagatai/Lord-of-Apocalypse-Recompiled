"""Verify that an incremental archive update changes only reviewed text pixels."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from rgf_archive import parse_index,read_group
from texture_text import digest,reconstruct
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('before','after','manifest','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();private=ROOT/'private'
 if any(not getattr(a,n).resolve().is_relative_to(private) for n in ('before','after','manifest','output')):p.error('Keep private inputs and reports local')
 if a.output.exists():raise ValueError('Use a fresh delta report')
 rows=json.loads(a.manifest.read_text(encoding='utf-8-sig'))['resources'];allowed={(int(r['resource_id'],16),r['source_sha256']):r for r in rows}
 if len(allowed)!=len(rows):raise ValueError('Duplicate manifest variant')
 def groups(d):return parse_index((d/'REGFILE.RZL').read_bytes(),(d/'REGFILE.RZP').stat().st_size)
 first,last=groups(a.before),groups(a.after);assert len(first)==len(last);seen=set();unchanged=changed=0
 with (a.before/'REGFILE.RZP').open('rb') as left,(a.after/'REGFILE.RZP').open('rb') as right:
  for old,new in zip(first,last):
   assert [i for n,i in old.entries]==[i for n,i in new.entries]
   x=read_group(left,old);y=read_group(right,new);ox=oy=0
   for (n,i),(m,j) in zip(old.entries,new.entries):
    source,target=x[ox:ox+n],y[oy:oy+m];ox+=n;oy+=m
    if source==target:unchanged+=1;continue
    key=i,digest(source)
    if key not in allowed:raise ValueError(f'Unreviewed resource changed: {i:08x}')
    if reconstruct(source,allowed[key],private)!=target:raise ValueError('Delta exceeds reviewed text pixels')
    seen.add(key);changed+=1
 if seen!=set(allowed):raise ValueError('Reviewed edit missing')
 report=dict(status='PASS',changed_unique_resources=len(seen),changed_instances=changed,unchanged_instances=unchanged,all_other_payloads_byte_identical=True)
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
