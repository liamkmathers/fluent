#!/usr/bin/env python3
"""
Speech-to-text for the Fluent tutor — records the learner's spoken Italian and
transcribes it so the skill can evaluate content + (via pronounce.py) accuracy.

Recording auto-stops on silence, so it works when launched non-interactively by
the tutor: the learner just speaks, then stops; the script detects the pause,
transcribes, and prints JSON to stdout.

Backends (--backend / FLUENT_STT_BACKEND, default "faster-whisper"):
  faster-whisper   local, offline, free. Model via FLUENT_WHISPER_MODEL (base).
  openai           OpenAI Whisper API (needs OPENAI_API_KEY).
  azure            Azure Speech STT   (needs AZURE_SPEECH_KEY + AZURE_SPEECH_REGION).

Usage:
  python3 stt.py --record --lang it            # record from mic, transcribe
  python3 stt.py --file answer.wav --lang it    # transcribe an existing file
  python3 stt.py --check                         # verify deps without a mic

Output (stdout): {"transcript": "...", "backend": "...", "audio_path": "..."}
"""
import argparse
import json
import os
import sys
import tempfile
import wave

SAMPLE_RATE = 16000
DEFAULT_BACKEND = os.environ.get("FLUENT_STT_BACKEND", "faster-whisper")
DEFAULT_MODEL = os.environ.get("FLUENT_WHISPER_MODEL", "base")


# ---------- recording (silence auto-stop) ----------

def record_until_silence(max_seconds=15.0, silence_seconds=1.5,
                         start_timeout=5.0, threshold=0.015):
    """Record mono 16k audio, auto-stopping after a pause. Returns WAV path."""
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as e:
        raise RuntimeError(
            f"recording needs sounddevice+numpy ({e}); "
            "pip install -r voice/requirements.txt, or use --file"
        )

    block = int(SAMPLE_RATE * 0.1)  # 100 ms blocks
    frames, silent_run, elapsed, started = [], 0.0, 0.0, False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while elapsed < max_seconds:
            data, _ = stream.read(block)
            frames.append(data.copy())
            rms = float(np.sqrt(np.mean(data ** 2)))
            elapsed += 0.1
            if rms >= threshold:
                started = True
                silent_run = 0.0
            else:
                silent_run += 0.1
            if not started and elapsed >= start_timeout:
                break  # learner never spoke
            if started and silent_run >= silence_seconds:
                break  # learner finished

    import numpy as np
    audio = (np.concatenate(frames) * 32767).astype("int16") if frames else np.array([], dtype="int16")
    path = tempfile.mktemp(suffix=".wav", prefix="fluent_stt_")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return path


# ---------- transcription backends ----------

def tx_faster_whisper(path, lang):
    from faster_whisper import WhisperModel
    model = WhisperModel(DEFAULT_MODEL, device="auto", compute_type="int8")
    segments, _ = model.transcribe(path, language=lang)
    return "".join(s.text for s in segments).strip()


def tx_openai(path, lang):
    from openai import OpenAI
    client = OpenAI()
    with open(path, "rb") as fh:
        r = client.audio.transcriptions.create(model="whisper-1", file=fh, language=lang)
    return r.text.strip()


def tx_azure(path, lang):
    import azure.cognitiveservices.speech as speechsdk
    cfg = speechsdk.SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
    )
    cfg.speech_recognition_language = "it-IT" if lang == "it" else lang
    audio_cfg = speechsdk.audio.AudioConfig(filename=path)
    rec = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio_cfg)
    return rec.recognize_once().text.strip()


TX = {"faster-whisper": tx_faster_whisper, "openai": tx_openai, "azure": tx_azure}


def check(backend):
    problems = []
    try:
        import numpy  # noqa
        import sounddevice  # noqa
    except ImportError as e:
        problems.append(f"recording: {e} (pip install -r voice/requirements.txt)")
    if backend == "faster-whisper":
        try:
            import faster_whisper  # noqa
        except ImportError as e:
            problems.append(f"faster-whisper: {e}")
    elif backend == "openai" and not os.environ.get("OPENAI_API_KEY"):
        problems.append("openai: set OPENAI_API_KEY")
    elif backend == "azure" and not (os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION")):
        problems.append("azure: set AZURE_SPEECH_KEY + AZURE_SPEECH_REGION")
    return problems


def main():
    ap = argparse.ArgumentParser(description="Fluent STT")
    ap.add_argument("--record", action="store_true", help="record from mic (auto-stop on silence)")
    ap.add_argument("--file", default=None, help="transcribe an existing audio file")
    ap.add_argument("--lang", default="it")
    ap.add_argument("--backend", default=DEFAULT_BACKEND, choices=list(TX))
    ap.add_argument("--max-seconds", type=float, default=15.0)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        problems = check(args.backend)
        if problems:
            print("NOT READY:")
            for p in problems:
                print("  - " + p)
            sys.exit(1)
        print(f"OK: STT backend '{args.backend}' ready.")
        sys.exit(0)

    if args.file:
        audio_path = args.file
    elif args.record:
        audio_path = record_until_silence(max_seconds=args.max_seconds)
    else:
        ap.error("pass --record, --file PATH, or --check")

    try:
        transcript = TX[args.backend](audio_path, args.lang)
    except Exception as e:
        print(json.dumps({"error": str(e), "backend": args.backend, "audio_path": audio_path}))
        sys.exit(1)

    print(json.dumps({"transcript": transcript, "backend": args.backend, "audio_path": audio_path},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
