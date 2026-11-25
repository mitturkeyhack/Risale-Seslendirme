#!/usr/bin/env python3
"""
Gemini TTS ile seslendirme.

Kullanım:
    gemini_ses.py metin.txt cikti.mp3 --ses Charon [--uslup "..."]
    gemini_ses.py --ornekler metin.txt --cikti klasor --sesler Charon,Algieba,...

GEMINI_API_KEY ortam değişkeni gerekir.
"""
import argparse
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import base64
import json
import urllib.error
import urllib.request

# Denenecek modeller (ilk çalışan kullanılır)
MODELLER = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def istek(anahtar, model, metin, ses, uslup):
    govde = {
        "contents": [{"role": "user", "parts": [{"text": metin, "speech_metadata": {"style": uslup}}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"voice": ses}},
        },
    }
    req = urllib.request.Request(
        API.format(model=model), data=json.dumps(govde).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": anahtar})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            yanit = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} {e.read().decode(errors='ignore')[:600]}") from None
    parca = yanit["candidates"][0]["content"]["parts"][0]["inlineData"]
    return base64.b64decode(parca["data"]), parca.get("mimeType", "")

VARSAYILAN_USLUP = (
    "Read the following Turkish text aloud, word for word, as a warm, wise and deeply calm "
    "storyteller narrating a spiritual parable to listeners who are hanging on every word. "
    "Use a medium-slow pace. Pause briefly at commas, pause longer at full stops, and take a "
    "noticeably longer, reflective pause at ellipses (...). Sincere, gentle, reverent and "
    "captivating; never theatrical or robotic. Pronounce Turkish naturally like a native "
    "Istanbul speaker, and recite any Arabic phrase with correct classical Arabic pronunciation."
)


def metni_hazirla(ham: str) -> str:
    """Seslendirme ayarlarını ve işaretleri temizler, okunacak düz metni döner."""
    satirlar = ham.splitlines()
    temiz = [s.strip() for s in satirlar]
    if "---" in temiz[:10]:
        satirlar = satirlar[temiz.index("---") + 1:]
    metin = "\n".join(satirlar)
    metin = re.sub(r"\[/?(ar|baslik)\]", "", metin, flags=re.I)
    metin = re.sub(r"\[dur[^\]]*\]", "...", metin, flags=re.I)
    return re.sub(r"\n{3,}", "\n\n", metin).strip()


def seslendir(anahtar, metin: str, ses: str, uslup: str, hedef: Path):
    """Önce sesi Gemini'den alır (sadece API hatalarında yeniden dener), sonra MP3'e çevirir."""
    veri = kullanilan = None
    son_hata = None
    for model in MODELLER:
        for deneme in range(2):
            try:
                veri, _ = istek(anahtar, model, metin, ses, uslup)
                kullanilan = model
                break
            except Exception as e:  # noqa: BLE001
                son_hata = e
                mesaj = str(e)
                print(f"  ⚠ {ses} / {model}: {mesaj[:300]}", flush=True)
                if "RESOURCE_EXHAUSTED" in mesaj or mesaj.startswith("429"):
                    if "PerDay" in mesaj or "per day" in mesaj.lower():
                        raise RuntimeError("Gemini günlük ücretsiz sınırı doldu, yarın tekrar dene.") from e
                    time.sleep(35)
                    continue
                if mesaj.startswith(("400", "404")):
                    break   # bu model bu isteği desteklemiyor, sonrakini dene
                time.sleep(5)
        if veri:
            break
    if not veri:
        raise RuntimeError(f"Seslendirilemedi: {son_hata}")

    wav = hedef.with_suffix(".wav")
    if veri[:4] == b"RIFF":
        wav.write_bytes(veri)
    else:  # başlıksız PCM gelirse WAV başlığı ekle
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(veri)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100",
                    "-c:a", "libmp3lame", "-b:a", "160k", str(hedef)], check=True)
    wav.unlink()
    print(f"✔ {ses} ({kullanilan}) → {hedef.name}", flush=True)
    return kullanilan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metin")
    ap.add_argument("hedef", nargs="?")
    ap.add_argument("--ses", default="Charon")
    ap.add_argument("--uslup", default=VARSAYILAN_USLUP)
    ap.add_argument("--ornekler", action="store_true")
    ap.add_argument("--sesler", default="Charon,Algieba,Enceladus,Sadaltager,Iapetus")
    ap.add_argument("--cikti", default="cikti")
    args = ap.parse_args()

    anahtar = os.environ.get("GEMINI_API_KEY")
    if not anahtar:
        sys.exit("GEMINI_API_KEY bulunamadı (GitHub Secrets'a eklenmeli).")
    metin = metni_hazirla(Path(args.metin).read_text(encoding="utf-8-sig"))

    if args.ornekler:
        klasor = Path(args.cikti)
        klasor.mkdir(parents=True, exist_ok=True)
        basarili = 0
        for i, ses in enumerate(s.strip() for s in args.sesler.split(",") if s.strip()):
            try:
                seslendir(anahtar, metin, ses, args.uslup, klasor / f"{i + 1}-{ses}.mp3")
                basarili += 1
            except RuntimeError as e:
                print(f"✖ {ses}: {e}", flush=True)
                if "günlük" in str(e):
                    break
        sys.exit(0 if basarili else 1)
    else:
        seslendir(anahtar, metin, args.ses, args.uslup, Path(args.hedef))


if __name__ == "__main__":
    main()
