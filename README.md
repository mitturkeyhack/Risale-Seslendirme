# 🔊 Risale Seslendirme

Metni yapıştırırsın, birkaç dakika içinde **MP3 seslendirme** ve **SRT altyazı** hazır olur.
Her şey GitHub'da kendi kendine çalışır, bilgisayar gerekmez.

---

## 📱 Nasıl kullanılır? (telefondan)

1. Tarayıcıdan bu depoyu aç ve **`metinler`** klasörüne gir.
2. **Add file → Create new file** de.
3. Dosyaya bir ad ver, sonu **`.txt`** olsun. Örnek: `ayet-temsili.txt`
4. Metni yapıştır ve **Commit changes** de.
5. 2-5 dakika bekle, sonra depo ana sayfasındaki **Releases** kısmına gir.
   En üstteki kayıtta **MP3 indir** ve **Altyazı indir** linkleri olur.

> İlerlemeyi görmek istersen **Actions** sekmesine bak. Yeşil tik = hazır, kırmızı çarpı = hata.

### ⚡ Hızlı yol (dosya açmadan)
**Actions → Seslendir → Run workflow** de, **metin** kutusuna kısa metni yapıştır ve çalıştır.

### 🔁 Aynı metni yeniden seslendirmek
Dosyayı düzenleyip kaydetmen yeterli, yeni ses otomatik üretilir.

---

## ⚙️ Ayarlar (isteğe bağlı)

Metnin **en üstüne** şunları yazıp altına `---` koyabilirsin:

```
ses: ahmet
hiz: -5
ton: 0
---
Metin buradan başlar...
```

| Ayar | Ne işe yarar | Örnek |
|---|---|---|
| `ses` | `ahmet` (erkek) ya da `emel` (kadın) | `ses: emel` |
| `hiz` | Okuma hızı, yüzde olarak. Eksi yavaşlatır, artı hızlandırır | `hiz: -10` |
| `ton` | Ses tonu. Eksi kalınlaştırır, artı inceltir | `ton: -5` |

Ayar yazmazsan **Ahmet sesi, normal hız** kullanılır.

---

## ✍️ Metin içinde özel işaretler

| İşaret | Ne yapar |
|---|---|
| `[ar]بِسْمِ اللّٰهِ[/ar]` | Arapça kısım **Arapça sesle** okunur |
| `[baslik]Birinci Söz[/baslik]` | Başlık, önünde ve arkasında duraklamayla okunur |
| `[dur 2]` | 2 saniye sessizlik (`[dur]` = 1 saniye) |
| Boş satır | Paragraflar arasında kısa nefes |

---

## 🗣️ Yanlış okunan kelimeler

Seslendirici bir kelimeyi yanlış okursa **`telaffuz.txt`** dosyasına ekle:

```
Kur'ân-ı Hakîm = Kuranı Hakîm
```

Altyazıda kelimenin aslı görünür, sadece okunuş değişir.

---

## 🎬 Reels / video için
- **MP3** dosyasını CapCut'ta videonun altına koy.
- **SRT** dosyası altyazıdır. CapCut'ın otomatik altyazısını da kullanabilirsin.

Ses: Microsoft Edge sesleri ([edge-tts](https://github.com/rany2/edge-tts)).
