#!/usr/bin/env python3
"""
videolar/<ad>/ klasöründen Reels videosu üretir.

Klasörde olması gerekenler:
    metin.txt          seslendirilecek metin (seslendirme ayarları en üstte yazılabilir)
    görseller          .jpg / .jpeg / .png / .webp — ada göre sırayla gösterilir (1.jpg, 2.jpg ...)

Adımlar:
    1) metin.txt  → doğal sesle MP3 + birebir SRT   (scripts/seslendir.py)
    2) görseller + ses → hareketli video            (MoneyPrinterTurbo)
    3) SRT → kelime kelime yanan altyazı videoya basılır (ffmpeg + ASS)

Kullanım: video_yap.py videolar/ad --cikti cikti --mpt /tmp/mpt --mpt-python /tmp/mptenv/bin/python
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
GORSEL_UZANTI = {".jpg", ".jpeg", ".png", ".webp"}


def calistir(komut, **kw):
    print("$", " ".join(str(k) for k in komut)[:300], flush=True)
    subprocess.run([str(k) for k in komut], check=True, **kw)


def sure_ol(dosya):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(dosya)]).strip())


def dogal_sira(p: Path):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", p.name)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("klasor")
    ap.add_argument("--cikti", default="cikti")
    ap.add_argument("--mpt", default="/tmp/mpt")
    ap.add_argument("--mpt-python", default="/tmp/mptenv/bin/python")
    ap.add_argument("--fontlar", default="/tmp/fontlar")
    args = ap.parse_args()

    klasor = Path(args.klasor).resolve()
    ad = klasor.name
    metin = klasor / "metin.txt"
    if not metin.exists():
        adaylar = sorted(klasor.glob("*.txt"))
        if not adaylar:
            sys.exit(f"{klasor}: metin.txt bulunamadı")
        metin = adaylar[0]
    gorseller = sorted([p for p in klasor.iterdir() if p.suffix.lower() in GORSEL_UZANTI], key=dogal_sira)
    if not gorseller:
        sys.exit(f"{klasor}: hiç görsel yok (jpg/png/webp ekle)")

    cikti = Path(args.cikti).resolve()
    cikti.mkdir(parents=True, exist_ok=True)
    is_klasoru = cikti / f".is-{ad}"
    is_klasoru.mkdir(parents=True, exist_ok=True)

    # 1) Seslendirme — çıktı adını klasör adına sabitle
    gecici_metin = is_klasoru / f"{ad}.txt"
    shutil.copy(metin, gecici_metin)
    calistir([sys.executable, KOK / "scripts" / "seslendir.py", gecici_metin, "--cikti", is_klasoru,
              "--ozet", is_klasoru / "ozet.json"])
    ozet = json.loads((is_klasoru / "ozet.json").read_text(encoding="utf-8"))
    if not ozet["sonuclar"]:
        sys.exit("Seslendirme başarısız")
    mp3 = is_klasoru / ozet["sonuclar"][0]["mp3"]
    srt = is_klasoru / ozet["sonuclar"][0]["srt"]
    ses_suresi = sure_ol(mp3)

    # 2) MoneyPrinterTurbo: görseller + ses → hareketli video (altyazısız)
    klip = max(3, math.ceil(ses_suresi / len(gorseller)) + 1)
    gorev = str(uuid.uuid4())
    calistir([
        args.mpt_python, "cli.py",
        "--video-script", "video",            # altyazıyı biz basıyoruz, senaryo sadece zorunlu alan
        "--video-language", "tr-TR",
        "--video-source", "local",
        "--video-materials", ",".join(str(g) for g in gorseller),
        "--video-concat-mode", "sequential",
        "--image-motion", "zoom",
        "--video-transition-mode", "fade-in",
        "--video-clip-duration", str(klip),
        "--video-aspect", "9:16",
        "--custom-audio-file", mp3,
        "--bgm-type", "none",
        "--no-subtitle-enabled",
        "--task-id", gorev,
    ], cwd=args.mpt)
    ham_video = Path(args.mpt) / "storage" / "tasks" / gorev / "final-1.mp4"
    if not ham_video.exists():
        sys.exit("MoneyPrinterTurbo video üretemedi")

    # 3) Kelime kelime yanan altyazı + hafif kenar karartması
    ass = is_klasoru / f"{ad}.ass"
    calistir([sys.executable, KOK / "scripts" / "altyazi_ass.py", srt, ass])
    ass_yol = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    font_yol = str(args.fontlar).replace(":", "\\:")
    son_video = cikti / f"{mp3.stem}.mp4"
    calistir([
        "ffmpeg", "-y", "-loglevel", "error", "-i", ham_video,
        "-vf", f"subtitles='{ass_yol}':fontsdir='{font_yol}',vignette=PI/6,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "10M", "-bufsize", "20M",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", son_video,
    ])
    shutil.copy(mp3, cikti / mp3.name)
    shutil.copy(srt, cikti / srt.name)
    sure = sure_ol(son_video)
    print(f"✔ {ad}: {son_video.name} ({sure:.1f} sn)")
    (cikti / f"{mp3.stem}.json").write_text(json.dumps(
        {"ad": ad, "mp4": son_video.name, "mp3": mp3.name, "srt": srt.name, "sure": round(sure, 1),
         "gorsel": len(gorseller)}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
