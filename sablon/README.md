<!--
README şablonu. Köşeli parantezli alanları doldurun ve bu açıklamayı silin.
README Türkçe yazılır (şartname md. 3: yarışmanın resmî dili Türkçedir).

Aşağıdaki başlıklar, şartnamenin repoda belirtilmesini istediği bilgileri kapsar: kurulum ve çalıştırma adımları,
başarım metriği ve gerekçesi, veri setinin niteliği, hızlandırıcıda ve CPU'da çalışan kısımlar, kullanılan üçüncü
taraf model, veri seti ve kütüphanelerin lisansları. Jüri Heyeti'nin aradığı bilgiyi her repoda aynı yerde
bulabilmesi için başlıkları silmeyin.

Repoda ad soyad gibi kişiyi tanımlayabilecek bilgi bulunmamalıdır (şartname md. 8).

Bu klasörü takimlar/<takim-adi>/ olarak kopyalayın. Klasör yapısı:
  README.md          bu dosya
  LICENSE            referans repodaki lisans; lisans türünü değiştirmeyin
  degerlendir.sh     modeli test-seti/ ile çalıştırıp sonuc.json yazan betik (olcum/README.md)
  kurulum.sh         isteğe bağlı: requirements.txt ve apt.txt dışındaki kurulum adımları (ör. model derleme)
  src/               kart üzerinde çalışan uygulama ve çıkarım kodu
  model/             model dosyaları (repo dışında barındırılacaksa HuggingFace/Kaggle bağlantıları indir.txt'de)
  training/          eğitim, ince ayar ve dönüştürme betikleri
  test-seti/         Jüri Heyeti'nin modeli test etmesi için gereken test verisi
  requirements.txt   Python bağımlılıkları, sürümleriyle
  apt.txt            varsa sistem paketleri, sürümleriyle
  docs/              düzenek fotoğrafları, şemalar
-->

# [Proje adı]

[Bir cümlelik özet.]

## Problem ve kullanım senaryosu

[Çözülen problem ve uygulamanın bulut ya da bilgisayar yerine kart üzerinde (uçta) çalışmasının gerekçesi.]

## Donanım düzeneği

[Kullanılan kamera, mikrofon ya da sensör, model adı, bağlantı şekli (MIPI CSI, USB, I2C, kart üstü sensör vb.).]

![Düzenek](docs/duzenek.jpg)

## Kurulum ve çalıştırma

Referans ortam: T3 Gemstone OS Minimal v2026.1 (Ubuntu 22.04) + t3-gem-o1-edgeai 11.0.

Kurulum tamamlandıktan sonra uygulama internet bağlantısı olmadan çalışmalıdır.

```bash
# Kurulum (requirements.txt, apt.txt, varsa model dosyalarının indirilmesi ve kurulum.sh)
[komutlar]

# Uygulamayı çalıştırma
[komut]

# test-seti/ ile değerlendirme (repo kök dizininden; degerlendir.sh'ı çalıştırır)
sudo python3 olcum/calistir.py --takim [takim-adi]
```

## Model

- **Mimari:** [ör. YOLOX-nano-lite, giriş boyutu 416×416]
- **Model biçimi:** [ör. ONNX, TFLite]
- **Model dosyaları:** [`model/` altında ya da HuggingFace/Kaggle bağlantısı]
- **Görev türü:** [ör. nesne tespiti]
- **Başarım metriği ve gerekçesi:** [ör. mAP@0.5; bu metriğin problem için neden uygun olduğu]
- **Eğitim verisi:** [kaynağı, boyutu, içeriği, etiketleme biçimi, lisansı; kendi topladığınız veriyse nasıl toplandığı. Veri setini paylaşmak zorunlu değildir.]
- **Test verisi:** [`test-seti/` klasöründeki verinin kaynağı, boyutu, biçimi ([Test Seti Biçimleri](https://docs.t3gemstone.org/tr/competitions/t3-gemstone-challenge/edge-ai/test-set-formats)) ve eğitim verisinden nasıl ayrıldığı]
- **Eğitim süreci:** [ortam, süre, önemli ayarlar; betikler `training/` altında. Model eğitilmediyse ya da yalnızca ince ayar yapıldıysa belirtin.]
- **Hızlandırıcıya derleme:** [kullanılan araç ve adımlar]
- **Hızlandırıcıda / CPU'da çalışan kısım:** [hızlandırıcıda çalışan katmanlar ve CPU'da kalan katmanlar]
- **Hazır model kullanıldıysa:** [kaynağı ve lisansı]

## Sonuçlar

[`olcum/calistir.py` ile `test-seti/` üzerinde elde edilen sonuçlar (`sonuc.json`).]

| | Değer |
|---|---|
| [Başarım metriği] | |
| FPS | |
| Gecikme ortalama / p95 (ms) | |

[Varsa hızlandırıcılı ve yalnız CPU çalışmanın karşılaştırması: hız kazanımı, doğruluk farkı ve nedenleri.]

## Demo videosu

[YouTube bağlantısı (liste dışı ya da herkese açık); aynı bağlantı başvuru formunda da paylaşılır. 30–90 saniye uzunluğunda, kesintisiz ve kurgusuz canlı çalışma çekimi olmalıdır. Kart, düzenek ve modelin gerçek bir ortamda gerçek zamanlı çalışması anlaşılır biçimde gösterilmeli; test verisi olarak sunulan içeriğin modelin başarımında avantaj yaratmadığı gösterilmelidir. Anlatım ya da altyazı eklenebilir.]

## Bu yarışmadaki katkı

[Proje önceki bir çalışmadan (TEKNOFEST vb.) türetildiyse: önceki çalışma neydi ve bu yarışma süresinde ne yapıldı (O1'e taşıma, hızlandırıcıya uyarlama, yeni model vb.). Yeni bir projeyse "Proje bu yarışma için geliştirilmiştir." yazın.]

## Kullanılan yapay zekâ araçları

[Geliştirmede kullanılan yapay zekâ asistanları ve ne için kullanıldıkları. Kullanılmadıysa "Kullanılmadı." yazın.]

## Takım ve lisans

- **Takım:** [takım adı]
- **Takım Kaptanı:** [GitHub kullanıcı adı]
- **Üyeler:** [GitHub kullanıcı adları]
- **Danışman:** [var / yok; lise takımları için zorunludur]
- **Lisans:** Bu repodaki çalışmalar referans repodaki lisans koşullarına tabidir; [LICENSE](LICENSE) dosyasına bakın.
- **Üçüncü taraf model, veri seti ve kütüphaneler:** [adı, kaynağı, lisansı]
