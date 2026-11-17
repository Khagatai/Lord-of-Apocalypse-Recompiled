"""Flag literal drafting artifacts for local review; never approve prose quality."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATTERNS={
 'literal-protected-placeholder':r'\{protected\}|<fixed:\d+>',
 'model-instruction':r'(?i)as an ai|here is (?:the|your) translation|output only|source sentence|target sentence|```',
 'unreviewed-bracket-placeholder':r'(?i)\[(?:insert|translation|your name|name here)[^\]]*\]',
 'fantasy-festival-mistranslation':r'(?i)\bChristmas\b',
}
def inspect(entry):
    text='\n'.join(entry.get('english_lines',[]));flags=[]
    for name,pattern in PATTERNS.items():
        if name=='fantasy-festival-mistranslation' and '聖誕祭' not in ''.join(entry.get('original_lines',[])):continue
        if re.search(pattern,text):flags.append(name)
    return flags
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('manifest',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();private=(ROOT/'private').resolve()
    if not args.manifest.resolve().is_relative_to(private) or not args.output.resolve().is_relative_to(private):raise ValueError('Keep game text and audits private')
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'));rows=[];total=0
    for bundle in manifest['bundles']:
        for entry in bundle['entries']:
            total+=1;flags=inspect(entry)
            if flags:rows.append(dict(resource_id=bundle['resource_id'],message_index=entry['message_index'],flags=flags,original_lines=entry.get('original_lines'),english_lines=entry.get('english_lines')))
    report=dict(scope='draft-artifact-triage-not-semantic-approval',entries_checked=total,flagged=len(rows),semantic_quality_validated=False,findings=rows)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='findings'}))
if __name__=='__main__':main()
