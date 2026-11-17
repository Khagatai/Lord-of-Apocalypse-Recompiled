"""Compare private locally rendered captions to an existing reviewed bundle.

This diagnostic does not admit a replacement or export any reference pixels.
"""
import argparse, copy, hashlib, json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import movie_captions


def audit(recipe, reference, work, candidate=False):
    if hashlib.sha256(reference).hexdigest() != recipe['expected_bundle_sha256']:
        raise ValueError('Reference bundle identity differs')
    count, total = struct.unpack_from('<2I', reference, 8)
    if reference[:8] != b'LOACAP1\0' or count != len(recipe['movies']):
        raise ValueError('Reference header differs')
    rows = []; position = 0; generated=[]
    for movie, record in enumerate(recipe['movies']):
        for cue in record['cues']:
            row = struct.unpack_from('<8I', reference, 16 + count*144 + position*32)
            position += 1
            if tuple(row[:7]) != (movie, cue['first_frame'], cue['end_frame'], cue['x'], cue['y'], cue['width'], cue['height']):
                raise ValueError('Reference cue layout differs')
            _, _, _, x, y, w, h, offset = row
            expected = reference[offset:offset+w*h*4]
            actual = (work/Path(record['movie']).stem/'rendered'/f"cue-{cue['id']:04}.rgba").read_bytes()
            if not record['credit_pages']:
                actual = b''.join(actual[((yy-224)*448+x-16)*4:((yy-224)*448+x-16+w)*4] for yy in range(y, y+h))
            if len(actual) != len(expected):
                raise ValueError('Rendered cue extent differs')
            differences = [i for i in range(0, len(actual), 4) if actual[i:i+4] != expected[i:i+4]]
            binary_ink_changes = sum((max(actual[i:i+3])>0) != (max(expected[i:i+3])>0) for i in differences)
            alpha_changes = sum(actual[i+3] != expected[i+3] for i in differences)
            delta = max((abs(actual[i+c]-expected[i+c]) for i in differences for c in range(3)), default=0)
            rows.append(dict(movie=record['movie'], id=cue['id'], differing_pixels=len(differences),
                maximum_RGB_delta=delta, ink_mask_changes=binary_ink_changes, alpha_changes=alpha_changes,
                actual_sha256=hashlib.sha256(actual).hexdigest()))
            generated.append((*row[:7],actual))
    if position != total:
        raise ValueError('Reference cue count differs')
    result = dict(status='DIAGNOSTIC_ONLY', cues=rows, exact_matches=sum(not r['differing_pixels'] for r in rows),
        differing_cues=sum(bool(r['differing_pixels']) for r in rows), reference_pixels_exported=False,
        maxima={k:max(r[k] for r in rows) for k in ('differing_pixels','maximum_RGB_delta','ink_mask_changes','alpha_changes')},
        by_movie={m:dict(cues=len(v),differing_cues=sum(bool(r['differing_pixels']) for r in v),
            differing_pixels=sum(r['differing_pixels'] for r in v))
            for m in sorted({r['movie'] for r in rows}) for v in [[r for r in rows if r['movie']==m]]})
    if candidate:
        # This creates a distinct candidate identity. It never claims byte-identical
        # reconstruction, nor changes the active reviewed bundle or launch approval.
        changed=copy.deepcopy(recipe)
        changed['reference_bundle_sha256']=recipe['expected_bundle_sha256']
        for cue,row in zip((c for m in changed['movies'] for c in m['cues']),rows,strict=True):
            cue['expected_pixels_sha256']=row['actual_sha256']
        headers=[reference[16+144*i:16+144*(i+1)] for i in range(count)]
        changed['expected_bundle_sha256']=hashlib.sha256(movie_captions.build(headers,generated)).hexdigest()
        changed['reference_comparison']={k:v for k,v in result.items() if k!='cues'}
        changed['approved_for_launch']=False
        result['candidate_recipe']=changed
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--recipe',type=Path,default=ROOT/'private/local-build/movie-caption-recipe.json')
    p.add_argument('--reference',type=Path,default=ROOT/'private/translation/movie-captions/captions.bin')
    p.add_argument('--candidate-recipe',type=Path,help='Write a distinct local-render candidate identity, without approving it')
    a=p.parse_args()
    for path in (a.work,a.recipe,a.reference,*([a.candidate_recipe] if a.candidate_recipe else [])):
        if not path.resolve().is_relative_to(ROOT/'private'):
            raise ValueError('Keep caption data private')
    result=audit(json.loads(a.recipe.read_text(encoding='utf-8')),a.reference.read_bytes(),a.work,bool(a.candidate_recipe))
    if a.candidate_recipe:
        if a.candidate_recipe.exists():raise FileExistsError('Candidate recipe already exists')
        a.candidate_recipe.write_text(json.dumps(result.pop('candidate_recipe'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (a.work/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cues'},indent=2))


if __name__=='__main__':main()
