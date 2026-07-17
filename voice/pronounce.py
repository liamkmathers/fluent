#!/usr/bin/env python3
"""
Pronunciation scoring for the Fluent tutor.

Given a reference sentence the learner was asked to say and their audio, return
structured scores the speaking skill turns into feedback and logs to
pronunciation-db.json.

Two tiers:

  azure (best)  Azure Speech "Pronunciation Assessment" — per-word and per-phoneme
                accuracy, plus fluency/completeness/prosody. Billed as part of
                Speech-to-Text (no separate charge); free tier ~5 audio-hours/mo.
                Needs AZURE_SPEECH_KEY + AZURE_SPEECH_REGION and
                pip install azure-cognitiveservices-speech.

  heuristic     No Azure key? Fall back to comparing an STT transcript of the
                audio against the reference (word-level match rate). Coarse — it
                catches "did they say the right words", not phoneme accuracy —
                but keeps the feature usable with only local Whisper.

Usage:
  python3 pronounce.py --reference "Vorrei un caffè" --file answer.wav
  python3 pronounce.py --reference "Vorrei un caffè" --record
  python3 pronounce.py --check

Output (stdout): JSON with tier, scores, and per-word detail.
"""
import os
import sys


def _use_project_venv():
    """Re-exec under the project's .venv if present (for the STT-based heuristic
    fallback, which needs faster-whisper). No-op if missing or already active."""
    here = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.abspath(os.path.join(here, "..", ".venv"))
    venv_py = os.path.join(venv_dir, "bin", "python3")
    if os.path.exists(venv_py) and os.path.abspath(sys.prefix) != venv_dir:
        os.execv(venv_py, [venv_py] + sys.argv)


_use_project_venv()

import argparse
import difflib
import json


def azure_assess(reference, audio_path, lang):
    import azure.cognitiveservices.speech as speechsdk

    cfg = speechsdk.SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
    )
    audio_cfg = speechsdk.audio.AudioConfig(filename=audio_path)
    pa_cfg = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=True,
    )
    reco = speechsdk.SpeechRecognizer(
        speech_config=cfg,
        language="it-IT" if lang == "it" else lang,
        audio_config=audio_cfg,
    )
    pa_cfg.apply_to(reco)
    result = reco.recognize_once()
    pa = speechsdk.PronunciationAssessmentResult(result)

    words = []
    for w in pa.words:
        words.append({
            "word": w.word,
            "accuracy": w.accuracy_score,
            "error_type": w.error_type,  # None|Mispronunciation|Omission|Insertion
        })
    return {
        "tier": "azure",
        "recognized_text": result.text,
        "scores": {
            "accuracy": pa.accuracy_score,
            "fluency": pa.fluency_score,
            "completeness": pa.completeness_score,
            "pronunciation": pa.pronunciation_score,  # overall 0-100
        },
        "words": words,
    }


def heuristic_assess(reference, audio_path, lang):
    """No Azure: transcribe with stt.py's backend, compare to reference."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import stt

    backend = os.environ.get("FLUENT_STT_BACKEND", "faster-whisper")
    recognized = stt.TX[backend](audio_path, lang)

    def norm(s):
        return [t for t in "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in s).split()]

    ref, hyp = norm(reference), norm(recognized)
    matcher = difflib.SequenceMatcher(a=ref, b=hyp)
    match_rate = matcher.ratio()  # 0..1 over the two token sequences

    words = []
    ref_matched = set()
    for block in matcher.get_matching_blocks():
        for i in range(block.a, block.a + block.size):
            ref_matched.add(i)
    for i, tok in enumerate(ref):
        words.append({
            "word": tok,
            "accuracy": 100 if i in ref_matched else 0,
            "error_type": None if i in ref_matched else "Mispronunciation|Omission",
        })

    pct = round(match_rate * 100, 1)
    return {
        "tier": "heuristic",
        "recognized_text": recognized,
        "scores": {
            "accuracy": pct,
            "fluency": None,
            "completeness": pct,
            "pronunciation": pct,
        },
        "words": words,
        "note": "Word-match heuristic (no Azure). Catches wrong/missing words, not phoneme accuracy.",
    }


def choose_tier():
    if os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"):
        try:
            import azure.cognitiveservices.speech  # noqa
            return "azure"
        except ImportError:
            return "heuristic"
    return "heuristic"


def main():
    ap = argparse.ArgumentParser(description="Fluent pronunciation scoring")
    ap.add_argument("--reference", help="the sentence the learner was asked to say")
    ap.add_argument("--file", default=None)
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--lang", default="it")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    tier = choose_tier()

    if args.check:
        print(f"Pronunciation tier available: {tier}")
        if tier == "heuristic":
            print("  (set AZURE_SPEECH_KEY + AZURE_SPEECH_REGION and install the Azure SDK for phoneme-level scoring)")
        sys.exit(0)

    if not args.reference:
        ap.error("--reference is required")

    if args.file:
        audio_path = args.file
    elif args.record:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import stt
        audio_path = stt.record_until_silence()
    else:
        ap.error("pass --file PATH or --record")

    try:
        if tier == "azure":
            result = azure_assess(args.reference, audio_path, args.lang)
        else:
            result = heuristic_assess(args.reference, audio_path, args.lang)
    except Exception as e:
        print(json.dumps({"error": str(e), "tier": tier, "audio_path": audio_path}))
        sys.exit(1)

    result["reference"] = args.reference
    result["audio_path"] = audio_path
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
