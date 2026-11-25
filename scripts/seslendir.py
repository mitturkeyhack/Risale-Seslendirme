#!/usr/bin/env python3
"""
Risale Seslendirme
------------------
metinler/ klasöründeki .txt dosyalarını MP3 seslendirmeye ve SRT altyazıya çevirir.

İki seslendirme motoru vardır:
    dogal  (varsayılan) Chatterbox — hikâye anlatır gibi, doğal ses; daha yavaş üretir
    hizli  Microsoft Edge sesleri (Ahmet / Emel) — çok hızlı üretir, daha yapay

Metin dosyasının en üstüne isteğe bağlı ayarlar yazılabilir:
    motor: dogal      (dogal | hizli)
    ses: varsayilan   (dogal motorda: varsayilan ya da sesler/ klasöründeki bir kaydın adı;
                       hizli motorda: ahmet | emel)
    hiz: -5           (yüzde; eksi = yavaş, artı = hızlı)
    ton: 0            (Hz; sadece hizli motorda; eksi = kalın, artı = ince)
    duygu: 65         (sadece dogal motorda; 0-100, yükseldikçe daha duygulu)
    ---
Ayarlar ile metin arasına '---' satırı konur. Ayar yazılmazsa varsayılanlar kullanılır.

Metin içinde özel işaretler:
    [ar] ... [/ar]   Arapça kısım, Arapça sesle okunur
    [dur 2]          2 saniye sessizlik (1.5 gibi küsurat da olur)
    [dur]            1 saniye sessizlik
    [baslik] ... [/baslik]  Önünde ve arkasında kısa duraklama olan başlık

telaffuz.txt dosyasındaki 'kelime = okunuş' satırları okunurken uygulanır
(altyazıda metnin aslı görünür).
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import edge_tts

KOK = Path(__file__).resolve().parent.parent

SESLER = {
    "ahmet": {"tr": "tr-TR-AhmetNeural", "ar": "ar-SA-HamedNeural"},
    "emel": {"tr": "tr-TR-EmelNeural", "ar": "ar-SA-ZariyahNeural"},
}

ALTYAZI_KELIME = 6        # bir altyazı satırında en fazla kelime
ALTYAZI_KARAKTER = 42     # bir altyazı satırında en fazla karakter
DENEME = 4                # servis hata verirse kaç kere tekrar denensin


# ---------------------------------------------------------------- yardımcılar

def ascii_ad(ad: str) -> str:
    """Dosya adını GitHub'ın sorunsuz kabul edeceği hâle getirir."""
    tablo = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")
    ad = ad.translate(tablo)
    ad = unicodedata.normalize("NFKD", ad).encode("ascii", "ignore").decode()
    ad = re.sub(r"[^A-Za-z0-9._-]+", "-", ad).strip("-")
    return ad or "ses"


def calistir(komut):
    s = subprocess.run(komut, capture_output=True, text=True)
    if s.returncode != 0:
        raise RuntimeError(f"Komut başarısız: {' '.join(komut)}\n{s.stderr[-2000:]}")
    return s.stdout


def sure_ol(dosya: Path) -> float:
    cikti = calistir([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(dosya),
    ])
    return float(cikti.strip())


def sessizlik(dosya: Path, saniye: float):
    calistir([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono", "-t", f"{saniye:.3f}",
        "-c:a", "libmp3lame", "-b:a", "64k", str(dosya),
    ])


def zaman(sn: float) -> str:
    ms = int(round(max(sn, 0) * 1000))
    s, ms = divmod(ms, 1000)
    d, s = divmod(s, 60)
    sa, d = divmod(d, 60)
    return f"{sa:02d}:{d:02d}:{s:02d},{ms:03d}"


# ---------------------------------------------------------------- metni okuma

@dataclass
class Ayar:
    motor: str = "dogal"
    ses: str = "varsayilan"
    hiz: int = -5
    ton: int = 0
    duygu: int = 65


# Doğal motorda noktalama işaretlerinden sonra bırakılacak sessizlik (saniye)
DURAKLAMA = {
    "…": 0.9, "...": 0.9,
    ".": 0.55, "?": 0.65, "!": 0.65,
    ":": 0.45, ";": 0.45,
    ",": 0.2,
}
PARCA_UZUNLUK = 220   # doğal motorda bir seferde okunacak en uzun parça (karakter)


@dataclass
class Parca:
    tur: str              # "tr" | "ar" | "dur"
    metin: str = ""
    saniye: float = 0.0
    altyazi: bool = True


def sayi(deger: str, varsayilan: int) -> int:
    m = re.search(r"[-+]?\d+", deger)
    return int(m.group()) if m else varsayilan


def ayarlari_ayir(ham: str):
    ayar = Ayar()
    motor_yazildi = hiz_yazildi = False
    satirlar = ham.splitlines()
    if "---" in [s.strip() for s in satirlar[:10]]:
        ayrac = [s.strip() for s in satirlar].index("---")
        for s in satirlar[:ayrac]:
            if ":" not in s:
                continue
            anahtar, deger = [x.strip() for x in s.split(":", 1)]
            anahtar = ascii_ad(anahtar).lower()
            deger_k = ascii_ad(deger).lower()
            if anahtar == "motor":
                ayar.motor = "hizli" if deger_k.startswith("hiz") else "dogal"
                motor_yazildi = True
            elif anahtar == "ses" and deger:
                ayar.ses = deger_k
            elif anahtar == "hiz":
                ayar.hiz = sayi(deger, ayar.hiz)
                hiz_yazildi = True
            elif anahtar == "ton":
                ayar.ton = sayi(deger, 0)
            elif anahtar == "duygu":
                ayar.duygu = max(0, min(100, sayi(deger, ayar.duygu)))
        ham = "\n".join(satirlar[ayrac + 1:])
    # "ses: ahmet / emel" yazıldıysa ve motor belirtilmediyse hızlı motor kastedilmiştir
    if not motor_yazildi and ayar.ses in SESLER:
        ayar.motor = "hizli"
    if ayar.motor == "hizli":
        if ayar.ses not in SESLER:
            ayar.ses = "ahmet"
        if not hiz_yazildi:
            ayar.hiz = 0
    return ayar, ham


def telaffuz_oku():
    dosya = KOK / "telaffuz.txt"
    kurallar = []
    if dosya.exists():
        for s in dosya.read_text(encoding="utf-8").splitlines():
            s = s.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            kelime, okunus = [x.strip() for x in s.split("=", 1)]
            if kelime:
                kurallar.append((kelime, okunus))
    # uzun kelimeler önce uygulansın
    kurallar.sort(key=lambda k: -len(k[0]))
    return kurallar


def telaffuz_uygula(metin: str, kurallar):
    for kelime, okunus in kurallar:
        metin = re.sub(rf"(?<!\w){re.escape(kelime)}(?!\w)", okunus, metin)
    return metin


ISARET = re.compile(
    r"\[ar\](.*?)\[/ar\]|\[baslik\](.*?)\[/baslik\]|\[dur(?:\s+([0-9]+(?:[.,][0-9]+)?))?\]",
    re.S | re.I,
)


def temizle(metin: str) -> str:
    return re.sub(r"\s+", " ", metin).strip()


def parcala(govde: str):
    parcalar = []
    konum = 0
    for m in ISARET.finditer(govde):
        once = temizle(govde[konum:m.start()])
        if once:
            parcalar.append(Parca("tr", once))
        if m.group(1) is not None:
            ar = temizle(m.group(1))
            if ar:
                parcalar.append(Parca("ar", ar))
        elif m.group(2) is not None:
            baslik = temizle(m.group(2))
            if baslik:
                parcalar.append(Parca("dur", saniye=0.6, altyazi=False))
                parcalar.append(Parca("tr", baslik))
                parcalar.append(Parca("dur", saniye=1.0, altyazi=False))
        else:
            sn = float((m.group(3) or "1").replace(",", "."))
            parcalar.append(Parca("dur", saniye=min(sn, 30.0), altyazi=False))
        konum = m.end()
    son = temizle(govde[konum:])
    if son:
        parcalar.append(Parca("tr", son))
    # Paragraf boşlukları için kısa duraklama: boş satırlar
    return parcalar


def paragraflara_bol(govde: str):
    """Boş satırla ayrılmış paragraflar arasına kısa duraklama ekler."""
    paragraflar = [p for p in re.split(r"\n\s*\n", govde) if p.strip()]
    sonuc = []
    for i, p in enumerate(paragraflar):
        sonuc.extend(parcala(p))
        if i < len(paragraflar) - 1:
            sonuc.append(Parca("dur", saniye=0.7, altyazi=False))
    return sonuc


# ---------------------------------------------------------------- seslendirme

async def tts(metin: str, ses: str, ayar: Ayar, hedef: Path):
    """Metni seslendirir, kelime zamanlarını döndürür."""
    son_hata = None
    for deneme in range(DENEME):
        try:
            kelimeler = []
            c = edge_tts.Communicate(
                metin, ses,
                rate=f"{ayar.hiz:+d}%", pitch=f"{ayar.ton:+d}Hz",
                boundary="WordBoundary",
                proxy=os.environ.get("HTTPS_PROXY") or None,
            )
            with open(hedef, "wb") as f:
                async for parca in c.stream():
                    if parca["type"] == "audio":
                        f.write(parca["data"])
                    elif parca["type"] == "WordBoundary":
                        kelimeler.append((
                            parca["offset"] / 1e7,
                            (parca["offset"] + parca["duration"]) / 1e7,
                            parca["text"],
                        ))
            if hedef.stat().st_size == 0:
                raise RuntimeError("boş ses döndü")
            return kelimeler
        except Exception as e:  # noqa: BLE001
            son_hata = e
            await asyncio.sleep(3 * (deneme + 1))
    raise RuntimeError(f"Seslendirme başarısız: {son_hata}")


# ---------------------------------------------------------------- doğal motor (Chatterbox)

class DogalMotor:
    """Chatterbox Multilingual ile hikâye anlatır gibi seslendirme."""

    def __init__(self):
        self.model = None
        self.referanslar = {}

    def yukle(self):
        if self.model is None:
            import torch  # noqa: F401  (yavaş yüklendiği için burada)
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            print("  Doğal ses modeli yükleniyor (ilk seferde birkaç dakika sürebilir)...", flush=True)
            self.model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
        return self.model

    def referans(self, ses: str, gecici: Path):
        """sesler/ klasöründeki kaydı WAV'a çevirir. 'varsayilan' ise None döner."""
        if ses in ("", "varsayilan", "default"):
            return None
        if ses in self.referanslar:
            return self.referanslar[ses]
        klasor = KOK / "sesler"
        aday = None
        if klasor.exists():
            for d in sorted(klasor.iterdir()):
                if ascii_ad(d.stem).lower() == ses and d.is_file():
                    aday = d
                    break
        if aday is None:
            print(f"  ⚠ sesler/ klasöründe '{ses}' adlı kayıt yok, varsayılan ses kullanılıyor.")
            self.referanslar[ses] = None
            return None
        wav = gecici / f"referans-{ses}.wav"
        # en fazla 20 saniye, tek kanal, 24 kHz
        calistir(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aday), "-t", "20",
                  "-ac", "1", "-ar", "24000", str(wav)])
        self.referanslar[ses] = str(wav)
        return str(wav)

    def oku(self, metin: str, dil: str, ayar: Ayar, hedef_mp3: Path, gecici: Path, sira: str):
        import torch
        import torchaudio
        model = self.yukle()
        ref = self.referans(ayar.ses, gecici)

        metin = metin.strip()
        if not re.search(r"[.!?…:;,]$", metin):
            metin += "."   # noktalamasız kısa parçalarda model sonuna ses uyduruyor
        # Harf sayısına göre olabilecek en uzun süre (Arapça harekeler sayılmaz).
        # Model bazen kısa metinlerin sonuna anlamsız ses ekliyor; bu sınır onu yakalar.
        harf = sum(1 for ch in metin if not ch.isspace() and unicodedata.category(ch) != "Mn")
        en_uzun = 0.13 * harf + 0.9

        en_iyi = None
        for deneme in range(3):
            torch.manual_seed(1234 + deneme)
            dalga = model.generate(
                metin, language_id=dil, audio_prompt_path=ref,
                exaggeration=0.25 + ayar.duygu / 100 * 0.6,   # 65 → ~0.64
                cfg_weight=0.3, temperature=0.8,
            )
            sure = dalga.shape[-1] / model.sr
            if en_iyi is None or sure < en_iyi[1]:
                en_iyi = (dalga, sure)
            if sure <= en_uzun:
                break
            print(f"    ↻ fazladan ses algılandı ({sure:.1f} sn > {en_uzun:.1f} sn), yeniden okunuyor", flush=True)
        dalga, sure = en_iyi

        ham = gecici / f"{sira}-ham.wav"
        torchaudio.save(str(ham), dalga, model.sr)
        tempo = max(0.7, min(1.3, 1 + ayar.hiz / 100))
        filtre = ""
        if sure > en_uzun:
            # üç denemede de uzun çıktıysa fazlasını yumuşakça kes
            filtre = f"atrim=0:{en_uzun:.2f},afade=t=out:st={max(en_uzun - 0.2, 0):.2f}:d=0.2,"
        # baştaki/sondaki sessizliği kırp, tempoyu ayarla
        calistir([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(ham), "-af",
            filtre +
            "silenceremove=start_periods=1:start_threshold=-45dB,"
            "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
            f"atempo={tempo:.3f}",
            "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k", str(hedef_mp3),
        ])


def cumlelere_bol(metin: str):
    """Doğal motor için metni cümlelere, uzun cümleleri virgül/noktalı virgülden böler.
    Her parça için (metin, ardından bırakılacak sessizlik) döner."""
    cumleler = re.findall(r".+?(?:\.\.\.|…|[.!?]+|$)(?:\s+|$)", metin.strip())
    sonuc = []
    for c in (x.strip() for x in cumleler):
        if not c:
            continue
        parcalar = [c]
        if len(c) > PARCA_UZUNLUK:
            parcalar = []
            simdiki = ""
            for p in re.split(r"(?<=[,;:])\s+", c):
                if simdiki and len(simdiki) + len(p) + 1 > PARCA_UZUNLUK:
                    parcalar.append(simdiki)
                    simdiki = p
                else:
                    simdiki = f"{simdiki} {p}".strip()
            if simdiki:
                parcalar.append(simdiki)
        for p in parcalar:
            son = "…" if p.endswith(("...", "…")) else p[-1]
            sonuc.append((p, DURAKLAMA.get(son, 0.3)))
    return sonuc


def altyazi_gruplari(metin: str):
    """Altyazı için metnin aslını kısa satırlara böler."""
    kelimeler = metin.split()
    gruplar, simdiki = [], []
    for k in kelimeler:
        aday = " ".join(simdiki + [k])
        if simdiki and (len(simdiki) >= ALTYAZI_KELIME or len(aday) > ALTYAZI_KARAKTER):
            gruplar.append(simdiki)
            simdiki = []
        simdiki.append(k)
        if re.search(r"[.!?;:…]$", k) and len(simdiki) >= 2:
            gruplar.append(simdiki)
            simdiki = []
    if simdiki:
        gruplar.append(simdiki)
    return [" ".join(g) for g in gruplar]


def zamanla(satirlar, kelime_zamanlari, toplam_sure):
    """
    Altyazı satırlarını ses zamanlarına oturtur.
    Okunan metin (telaffuz değişmiş olabilir) ile metnin aslı arasında
    karakter oranına göre eşleme yapılır.
    """
    if not satirlar:
        return []
    uzunluklar = [len(s.replace(" ", "")) or 1 for s in satirlar]
    toplam = sum(uzunluklar)

    if kelime_zamanlari:
        k_uz = [len(k[2].replace(" ", "")) or 1 for k in kelime_zamanlari]
        k_toplam = sum(k_uz)
        birikim, k_bas = 0, []
        for u in k_uz:
            k_bas.append(birikim / k_toplam)
            birikim += u

        def oran_zaman(oran):
            # orana karşılık gelen kelimenin başlangıç zamanı
            for i in range(len(k_bas) - 1, -1, -1):
                if k_bas[i] <= oran + 1e-9:
                    return kelime_zamanlari[i][0]
            return kelime_zamanlari[0][0]

        baslar, birikim = [], 0
        for u in uzunluklar:
            baslar.append(oran_zaman(birikim / toplam))
            birikim += u
        sonlar = baslar[1:] + [min(kelime_zamanlari[-1][1] + 0.3, toplam_sure)]
    else:
        baslar, birikim = [], 0
        for u in uzunluklar:
            baslar.append(toplam_sure * birikim / toplam)
            birikim += u
        sonlar = baslar[1:] + [toplam_sure]

    return [(b, max(s, b + 0.3), t) for b, s, t in zip(baslar, sonlar, satirlar)]


DOGAL = DogalMotor()


async def dosya_isle(kaynak: Path, cikti_klasoru: Path):
    ham = kaynak.read_text(encoding="utf-8-sig")
    ayar, govde = ayarlari_ayir(ham)
    kurallar = telaffuz_oku()
    parcalar = paragraflara_bol(govde)
    if not any(p.tur != "dur" for p in parcalar):
        raise RuntimeError(f"{kaynak.name}: okunacak metin yok")

    ad = ascii_ad(kaynak.stem)
    cikti_klasoru.mkdir(parents=True, exist_ok=True)
    mp3 = cikti_klasoru / f"{ad}.mp3"
    srt = cikti_klasoru / f"{ad}.srt"
    txt_altyazi = []

    with tempfile.TemporaryDirectory() as gecici:
        gecici = Path(gecici)
        dosyalar = []
        zaman_cizelgesi = 0.0
        for i, p in enumerate(parcalar):
            parca_dosya = gecici / f"{i:04d}.mp3"
            if p.tur == "dur":
                sessizlik(parca_dosya, p.saniye)
            elif ayar.motor == "dogal":
                okunacak = telaffuz_uygula(p.metin, kurallar) if p.tur == "tr" else p.metin
                asil_parcalar = cumlelere_bol(p.metin)
                okunan_parcalar = cumlelere_bol(okunacak)
                if len(asil_parcalar) != len(okunan_parcalar):
                    # telaffuz değişikliği bölmeyi bozduysa altyazı için okunanı kullan
                    asil_parcalar = okunan_parcalar
                for j, ((asil, _), (okunan, bosluk)) in enumerate(zip(asil_parcalar, okunan_parcalar)):
                    cumle_dosya = gecici / f"{i:04d}-{j:03d}.mp3"
                    DOGAL.oku(okunan, p.tur, ayar, cumle_dosya, gecici, f"{i:04d}-{j:03d}")
                    sure = sure_ol(cumle_dosya)
                    for b, s, t in zamanla(altyazi_gruplari(asil), [], sure):
                        txt_altyazi.append((zaman_cizelgesi + b, zaman_cizelgesi + s, t))
                    dosyalar.append(cumle_dosya)
                    zaman_cizelgesi += sure
                    bosluk_dosya = gecici / f"{i:04d}-{j:03d}-b.mp3"
                    sessizlik(bosluk_dosya, bosluk)
                    dosyalar.append(bosluk_dosya)
                    zaman_cizelgesi += sure_ol(bosluk_dosya)
                    print(f"  [{i + 1}/{len(parcalar)}] cümle {j + 1}/{len(okunan_parcalar)} tamam", flush=True)
                continue
            else:
                ses = SESLER[ayar.ses][p.tur]
                okunacak = telaffuz_uygula(p.metin, kurallar) if p.tur == "tr" else p.metin
                kz = await tts(okunacak, ses, ayar, parca_dosya)
                sure = sure_ol(parca_dosya)
                for b, s, t in zamanla(altyazi_gruplari(p.metin), kz, sure):
                    txt_altyazi.append((zaman_cizelgesi + b, zaman_cizelgesi + s, t))
            dosyalar.append(parca_dosya)
            zaman_cizelgesi += sure_ol(parca_dosya)
            print(f"  [{i + 1}/{len(parcalar)}] {p.tur} tamam", flush=True)

        liste = gecici / "liste.txt"
        liste.write_text("".join(f"file '{d}'\n" for d in dosyalar), encoding="utf-8")
        calistir([
            "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(liste), "-ar", "44100", "-ac", "1",
            "-c:a", "libmp3lame", "-b:a", "128k", str(mp3),
        ])

    # Altyazı çakışmalarını düzelt
    satirlar = []
    for i, (b, s, t) in enumerate(txt_altyazi):
        if i + 1 < len(txt_altyazi):
            s = min(s, txt_altyazi[i + 1][0])
        satirlar.append(f"{i + 1}\n{zaman(b)} --> {zaman(s)}\n{t}\n")
    srt.write_text("\n".join(satirlar), encoding="utf-8")

    sure = sure_ol(mp3)
    print(f"✔ {kaynak.name} → {mp3.name} ({sure:.1f} sn), {srt.name}")
    return {"kaynak": kaynak.name, "mp3": mp3.name, "srt": srt.name,
            "sure": round(sure, 1),
            "ses": (f"doğal ({ayar.ses})" if ayar.motor == "dogal" else f"hızlı ({ayar.ses})")}


async def ana():
    ap = argparse.ArgumentParser()
    ap.add_argument("dosyalar", nargs="*", help="seslendirilecek .txt dosyaları")
    ap.add_argument("--cikti", default="cikti")
    ap.add_argument("--ozet", default="", help="sonuçların yazılacağı JSON dosyası")
    args = ap.parse_args()

    dosyalar = [Path(d) for d in args.dosyalar if d.endswith(".txt") and Path(d).exists()]
    if not dosyalar:
        print("Seslendirilecek dosya bulunamadı.")
        return 0

    sonuclar, hatalar = [], []
    for d in dosyalar:
        print(f"▶ {d}")
        try:
            sonuclar.append(await dosya_isle(d, Path(args.cikti)))
        except Exception as e:  # noqa: BLE001
            print(f"✖ {d.name}: {e}", file=sys.stderr)
            hatalar.append(d.name)

    if args.ozet:
        Path(args.ozet).write_text(json.dumps(
            {"sonuclar": sonuclar, "hatalar": hatalar}, ensure_ascii=False, indent=2),
            encoding="utf-8")
    return 1 if hatalar and not sonuclar else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(ana()))
