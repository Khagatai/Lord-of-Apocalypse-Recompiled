"""Explicit admission for local translation diagnostics and isolated text tests."""
import hashlib
import json
from pathlib import Path
import title
from iso_edits import extent_hash, survey

def baseline_manifest():
    config=title.CONFIG['translations']['english_v16']
    raw=(title.ROOT/config['file_manifest']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=config['file_manifest_sha256']:
        raise ValueError('Translation baseline manifest hash differs')
    result=json.loads(raw)
    if result.get('schema')!=1 or result.get('source_iso_sha256')!=config['sha256'] or result.get('source_iso_size')!=config['size']:
        raise ValueError('Translation baseline identity differs')
    return result

def verify(image, report_path):
    root = title.ROOT / "private"
    image, report_path = Path(image).resolve(), Path(report_path).resolve()
    if not image.is_relative_to(root) or not report_path.is_relative_to(root):
        raise ValueError("Translation candidates and reports must stay private")
    report_raw = report_path.read_bytes()
    report = json.loads(report_raw)
    baseline = baseline_manifest()
    if report["source_iso_sha256"] != baseline['source_iso_sha256'] or report.get("all_file_payloads_verified") is not True:
        raise ValueError("Candidate lacks verification against the pinned English image")
    if image.stat().st_size != report["candidate_iso_size"]:
        raise ValueError("Candidate size differs from its report")
    with image.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != report["candidate_iso_sha256"]:
        raise ValueError("Candidate hash differs from its report")
    # Diagnostic overrides may change only the message archives, never code,
    # PRXs or other assets. Verify that independently rather than trusting JSON.
    allowed = {"PSP_GAME/USRDIR/UPDATA/REGFILE.RZL", "PSP_GAME/USRDIR/UPDATA/REGFILE.RZP"}
    with image.open("rb") as new:
        before, after = baseline['files'], survey.ISO(new).files()
        if set(before) != set(after):
            raise ValueError("Candidate file list differs")
        for name, record in before.items():
            if name in allowed:
                continue
            changed = after[name]
            if record['size']!=changed['size'] or record['sha256']!=extent_hash(new, changed["lba"] * 2048, changed["size"]):
                raise ValueError(f"Candidate changes a non-message file: {name}")
    return digest, hashlib.sha256(report_raw).hexdigest()
