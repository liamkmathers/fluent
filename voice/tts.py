#!/usr/bin/env python3
"""
Text-to-speech for the Fluent tutor — speaks Italian prompts aloud.

Backends (pick via --backend or FLUENT_TTS_BACKEND, default "say"):
  say         macOS built-in `say`. Offline, free, zero-config. Italian voices
              incl. Alice, Eddy, Flo, Reed. This is the default.
  openai      OpenAI TTS API      (needs OPENAI_API_KEY, pip install openai)
  elevenlabs  ElevenLabs API      (needs ELEVENLABS_API_KEY, pip install elevenlabs)
  azure       Azure Speech TTS    (needs AZURE_SPEECH_KEY + AZURE_SPEECH_REGION)

Usage:
  python3 tts.py "Ciao, come stai?"
  python3 tts.py "Buongiorno" --voice Alice
  python3 tts.py "Buongiorno" --backend openai --out reply.mp3
  python3 tts.py --check         # verify the chosen backend is usable
"""
import argparse
import os
import shutil
import subprocess
import sys

DEFAULT_VOICE = os.environ.get("FLUENT_TTS_VOICE", "Alice")  # it_IT on macOS
DEFAULT_BACKEND = os.environ.get("FLUENT_TTS_BACKEND", "say")


def speak_say(text, voice, out):
    if not shutil.which("say"):
        return 1, "`say` not found (macOS only). Choose another --backend."
    if out:
        # say writes AIFF; keep it simple and let the caller convert if needed.
        cmd = ["say", "-v", voice, "-o", out, text]
    else:
        cmd = ["say", "-v", voice, text]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stderr.strip()


def speak_openai(text, voice, out):
    try:
        from openai import OpenAI
    except ImportError:
        return 1, "pip install openai"
    if not os.environ.get("OPENAI_API_KEY"):
        return 1, "set OPENAI_API_KEY"
    client = OpenAI()
    out = out or "/tmp/fluent_tts.mp3"
    # 'alloy' etc. are OpenAI voices; map an Italian-friendly default.
    ov = voice if voice not in ("Alice",) else "alloy"
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts", voice=ov, input=text
    ) as resp:
        resp.stream_to_file(out)
    _play(out)
    return 0, ""


def speak_elevenlabs(text, voice, out):
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import play
    except ImportError:
        return 1, "pip install elevenlabs"
    if not os.environ.get("ELEVENLABS_API_KEY"):
        return 1, "set ELEVENLABS_API_KEY"
    client = ElevenLabs()
    audio = client.text_to_speech.convert(
        text=text, voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "Rachel"),
        model_id="eleven_multilingual_v2",
    )
    if out:
        with open(out, "wb") as fh:
            for chunk in audio:
                fh.write(chunk)
        _play(out)
    else:
        play(audio)
    return 0, ""


def speak_azure(text, voice, out):
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        return 1, "pip install azure-cognitiveservices-speech"
    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION")
    if not (key and region):
        return 1, "set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION"
    cfg = speechsdk.SpeechConfig(subscription=key, region=region)
    cfg.speech_synthesis_voice_name = (
        voice if voice.startswith("it-") else "it-IT-ElsaNeural"
    )
    audio_cfg = speechsdk.audio.AudioOutputConfig(
        filename=out) if out else speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=audio_cfg)
    result = synth.speak_text_async(text).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        return 1, str(result.reason)
    if out:
        _play(out)
    return 0, ""


def _play(path):
    for player in ("afplay", "ffplay", "aplay"):
        if shutil.which(player):
            args = [player, path]
            if player == "ffplay":
                args = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]
            subprocess.run(args, capture_output=True)
            return


BACKENDS = {
    "say": speak_say,
    "openai": speak_openai,
    "elevenlabs": speak_elevenlabs,
    "azure": speak_azure,
}


def main():
    ap = argparse.ArgumentParser(description="Fluent TTS")
    ap.add_argument("text", nargs="?", default="")
    ap.add_argument("--backend", default=DEFAULT_BACKEND, choices=list(BACKENDS))
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--out", default=None, help="save audio to file instead of/again playing")
    ap.add_argument("--check", action="store_true", help="verify backend is usable and exit")
    args = ap.parse_args()

    fn = BACKENDS[args.backend]

    if args.check:
        code, msg = fn("Prova.", args.voice, "/tmp/fluent_tts_check.aiff")
        if code == 0:
            print(f"OK: backend '{args.backend}' is usable.")
        else:
            print(f"NOT READY: backend '{args.backend}' — {msg}")
        sys.exit(code)

    if not args.text:
        ap.error("provide text to speak (or use --check)")

    code, msg = fn(args.text, args.voice, args.out)
    if code != 0:
        print(f"TTS failed ({args.backend}): {msg}", file=sys.stderr)
    sys.exit(code)


if __name__ == "__main__":
    main()
