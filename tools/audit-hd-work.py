"""Audit recipe necessity without guessing that unseen textures are unused."""
import argparse,collections,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import remaster_policy

def audit(recipe):
    jobs=recipe['jobs'];used={g['job'] for g in recipe['groups']}
    missing=sorted(used-set(jobs));unreferenced=sorted(set(jobs)-used)
    portraits=[key for key,j in jobs.items() if remaster_policy.original_portrait(j['reference']['name'])]
    ui=[key for key,j in jobs.items() if re.match(r'^(?:CO_|ME_|ICO_|LOAD_|LOGO|TITLE|CAUTION|MENU_)',j['reference']['name'])]
    levels=sum(len(j['dimensions']) for j in jobs.values())
    return dict(status='PASS' if not missing and not portraits else 'FAIL',groups=len(recipe['groups']),unique_jobs=len(jobs),
        source_mip_levels=levels,unreferenced_jobs=unreferenced,missing_jobs=missing,portrait_jobs=portraits,
        runtime_identity_aliases=len(recipe['groups'])-len(used),methods=dict(collections.Counter(j['method'] for j in jobs.values())),
        UI_named_jobs=len(ui),UI_named_jobs_are_proven_unused=False,
        conclusion='Aliases share processing jobs. Retain ambiguous/shared assets; original 2D draws bypass replacements. Optimise duplicate processing, not campaign coverage.',
        removed_game_assets=0,game_pixels_included=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=audit(json.loads(a.recipes.read_text()));a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    raise SystemExit(result['status']!='PASS')
