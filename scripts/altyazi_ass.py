#!/usr/bin/env python3
"""
SRT altyazıyı, okunan kelimenin altın rengine döndüğü (karaoke) ASS altyazıya çevirir.
Arapça satırlar ayrı bir stille, ekranın ortasında gösterilir.

Kullanım: altyazi_ass.py girdi.srt cikti.ass
"""
import re
import sys


def zaman_oku(z):
    s, ms = z.strip().split(",")
    sa, dk, sn = s.split(":")
    return int(sa) * 3600 + int(dk) * 60 + int(sn) + int(ms) / 1000


def ass_zaman(t):
    t = max(t, 0)
    cs = int(round(t * 100))
    sa, cs = divmod(cs, 360000)
    dk, cs = divmod(cs, 6000)
    sn, cs = divmod(cs, 100)
    return f"{sa}:{dk:02d}:{sn:02d}.{cs:02d}"


def srt_oku(yol):
    metin = open(yol, encoding="utf-8").read().replace("\r", "")
    kayitlar = []
    for blok in re.split(r"\n\s*\n", metin.strip()):
        satirlar = [s for s in blok.split("\n") if s.strip()]
        if len(satirlar) < 3 or "-->" not in satirlar[1]:
            continue
        bas, son = satirlar[1].split("-->")
        kayitlar.append((zaman_oku(bas), zaman_oku(son), " ".join(satirlar[2:]).strip()))
    return kayitlar


ARAPCA = re.compile(r"[؀-ۿ]")

BASLIK = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Altyazi,Be Vietnam Pro,92,&H004EC1F2,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,5,3,2,90,90,430,1
Style: Arapca,Amiri,140,&H0096E2FF,&H0096E2FF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,4,4,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def karaoke(bas, son, metin):
    """Kelime sürelerini harf sayısına göre paylaştırır, {\\k} etiketleri üretir."""
    kelimeler = metin.split()
    if not kelimeler:
        return ""
    uzunluk = [len(k) + 2 for k in kelimeler]
    toplam = sum(uzunluk)
    sure_cs = max(int(round((son - bas) * 100)), len(kelimeler))
    parcalar, kalan = [], sure_cs
    for i, (k, u) in enumerate(zip(kelimeler, uzunluk)):
        d = kalan if i == len(kelimeler) - 1 else max(1, int(round(sure_cs * u / toplam)))
        kalan -= d
        k = k.replace("{", "(").replace("}", ")")
        parcalar.append(f"{{\\k{d}}}{k}")
    return " ".join(parcalar)


def main():
    girdi, cikti = sys.argv[1], sys.argv[2]
    satirlar = [BASLIK]
    for bas, son, metin in srt_oku(girdi):
        if ARAPCA.search(metin):
            satirlar.append(
                f"Dialogue: 0,{ass_zaman(bas)},{ass_zaman(son + 0.6)},Arapca,,0,0,0,,"
                f"{{\\fad(300,300)}}{metin}\n")
        else:
            satirlar.append(
                f"Dialogue: 0,{ass_zaman(bas)},{ass_zaman(son)},Altyazi,,0,0,0,,"
                f"{{\\fad(120,120)}}{karaoke(bas, son, metin)}\n")
    open(cikti, "w", encoding="utf-8").write("".join(satirlar))


if __name__ == "__main__":
    main()
