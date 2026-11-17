"""Run local-only CPU translation drafts. Never installs or approves translations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import time

ROOT = Path(__file__).resolve().parents[1]


def refuse_network(*args, **kwargs):
    raise RuntimeError("Network connections are disabled during game text inference")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, choices=range(1, 9), default=4)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    # Inference has no service endpoint, telemetry or model download path.
    socket.socket.connect = refuse_network
    socket.socket.connect_ex = refuse_network
    socket.create_connection = refuse_network
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    import ctranslate2
    import sentencepiece
    engine = ROOT / "private/tools/translation-engine"
    source = sentencepiece.SentencePieceProcessor(model_file=str(engine / "original/source.spm"))
    target = sentencepiece.SentencePieceProcessor(model_file=str(engine / "original/target.spm"))
    translator = ctranslate2.Translator(str(engine / "ct2-int8"), device="cpu", compute_type="int8",
                                        intra_threads=args.threads, inter_threads=1)
    jobs = list(map(json.loads, args.queue.open(encoding="utf-8")))
    output.mkdir(parents=True)
    begin = time.monotonic()
    completed, blocked = 0, 0
    with (output / "drafts.jsonl").open("w", encoding="utf-8") as destination:
        for start in range(0, len(jobs), 16):
            chunk = jobs[start:start+16]
            tokens = [source.encode(job["source"].strip(), out_type=str) for job in chunk]
            eligible = [(job, token) for job, token in zip(chunk, tokens) if 0 < len(token) <= 512]
            for job, token in zip(chunk, tokens):
                if not 0 < len(token) <= 512:
                    destination.write(json.dumps({**job, "status": "blocked-input-length", "source_tokens": len(token)}) + "\n")
                    blocked += 1
            results = translator.translate_batch([token for _, token in eligible], beam_size=4,
                                                  max_decoding_length=512, max_input_length=0)
            for (job, token), result in zip(eligible, results):
                words = result.hypotheses[0]
                translated = target.decode(words).strip()
                status = "machine-draft-unreviewed" if translated and len(words) < 512 else "blocked-empty-or-length"
                destination.write(json.dumps({**job, "translation": translated, "status": status,
                                              "source_tokens": len(token), "target_tokens": len(words)}, ensure_ascii=True) + "\n")
                completed += status == "machine-draft-unreviewed"
                blocked += status != "machine-draft-unreviewed"
            destination.flush()
            report = {"status": "running" if start+16 < len(jobs) else "drafted-not-reviewed",
                      "translation_complete": False, "inference_network_connections": "blocked",
                      "engine": "CTranslate2", "engine_version": ctranslate2.__version__,
                      "model": "OPUS-MT ja-en opus-2019-12-18", "model_archive_sha256":
                      json.loads((engine / "weights-lock.json").read_text())["archive_sha256_observed"],
                      "queue_sha256": hashlib.sha256(args.queue.read_bytes()).hexdigest(),
                      "total_jobs": len(jobs), "drafted_jobs": completed, "blocked_jobs": blocked,
                      "elapsed_seconds": round(time.monotonic()-begin, 2)}
            (output / "progress.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({"processed": min(start+16, len(jobs)), "total": len(jobs),
                              "seconds": report["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
