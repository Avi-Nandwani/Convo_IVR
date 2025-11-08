#!/usr/bin/env python3
"""
Generate a demo WAV for the IVR POC.
Usage:
  python demo/make_wav.py --text "hello i want my account balance" --out demo/recordings/sample.wav
"""
import argparse
from pathlib import Path

def synthesize_pyttsx3(text: str, out_path: Path) -> bool:
    try:
        import pyttsx3
        out_path.parent.mkdir(parents=True, exist_ok=True)
        eng = pyttsx3.init()
        eng.save_to_file(text, str(out_path))
        eng.runAndWait()
        return out_path.exists()
    except Exception as e:
        print("[error] pyttsx3 synthesis failed:", e)
        return False

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--text", default="hello i want my account balance")
    p.add_argument("--out", default="demo/recordings/sample.wav")
    args = p.parse_args()

    out = Path(args.out)
    ok = synthesize_pyttsx3(args.text, out)
    if ok:
        # also drop a matching .txt so ASR fallback can use it
        txt = out.with_suffix(".txt")
        txt.write_text(args.text, encoding="utf-8")
        print(f"[ok] wrote: {out} and {txt}")
    else:
        print("[fail] could not create WAV. Install pyttsx3 or use OS tools (see below).")

if __name__ == "__main__":
    main()
