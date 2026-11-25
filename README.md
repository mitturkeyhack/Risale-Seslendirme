# 🔊 Risale Seslendirme

Metni yapıştırırsın, birkaç dakika içinde **MP3 seslendirme** ve **SRT altyazı** hazır olur.
Her şey GitHub'da kendi kendine çalışır, bilgisayar gerekmez.

---

## 📱 Nasıl kullanılır? (telefondan)

1. Tarayıcıdan bu depoyu aç ve **`metinler`** klasörüne gir.
2. **Add file → Create new file** de.
3. Dosyaya bir ad ver, sonu **`.txt`** olsun. Örnek: `ayet-temsili.txt`
4. Metni yapıştır ve **Commit changes** de.
5. Birkaç dakika bekle (doğal seste 1 dakikalık metin için 5-10 dakika), sonra depo ana sayfasındaki **Releases** kısmına gir.
   En üstteki kayıtta **MP3 indir** ve **Altyazı indir** linkleri olur.

> İlerlemeyi görmek istersen **Actions** sekmesine bak. Yeşil tik = hazır, kırmızı çarpı = hata.

### ⚡ Hızlı yol (dosya açmadan)
**Actions → Seslendir → Run workflow** de, **metin** kutusuna kısa metni yapıştır ve çalıştır.

### 🔁 Aynı metni yeniden seslendirmek
Dosyayı düzenleyip kaydetmen yeterli, yeni ses otomatik üretilir.

---

## 🎙️ İki ses motoru var

| Motor | Nasıl | Süre |
|---|---|---|
| **doğal** (varsayılan) | Hikâye anlatır gibi, sıcak ve akıcı. Cümle sonlarında doğal duraklamalar yapar | 1 dakikalık ses yaklaşık 5-10 dakikada hazır olur |
| **hızlı** | Microsoft sesleri (Ahmet / Emel), daha yapay | Birkaç saniyede hazır |

Hiçbir ayar yazmazsan **doğal** motorla, orta hızda okunur.

## ⚙️ Ayarlar (isteğe bağlı)

Metnin **en üstüne** şunları yazıp altına `---` koyabilirsin:

```
hiz: -10
duygu: 70
---
Metin buradan başlar...
```

| Ayar | Ne işe yarar | Örnek |
|---|---|---|
| `hiz` | Okuma hızı, yüzde olarak. Eksi yavaşlatır, artı hızlandırır (varsayılan -5) | `hiz: -10` |
| `duygu` | Sadece doğal motorda. 0-100 arası, yükseldikçe daha duygulu okur (varsayılan 65) | `duygu: 75` |
| `ses` | Doğal motorda `sesler/` klasörüne koyduğun kaydın adı (bkz. [sesler/BENI-OKU.md](sesler/BENI-OKU.md)). `ahmet` ya da `emel` yazarsan hızlı motorla okunur | `ses: anlatici` |
| `motor` | `dogal` ya da `hizli` | `motor: hizli` |
| `ton` | Sadece hızlı motorda. Eksi kalınlaştırır, artı inceltir | `ton: -5` |

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

Doğal ses: [Chatterbox](https://github.com/resemble-ai/chatterbox) (MIT lisansı). Hızlı ses: Microsoft Edge sesleri ([edge-tts](https://github.com/rany2/edge-tts)).
