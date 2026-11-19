<p align="center">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset=".meta/logo-dark.png" width="40%" />
        <source media="(prefers-color-scheme: light)" srcset=".meta/logo-light.png" width="40%" />
        <img alt="T3 Foundation" src=".meta/logo-light.png" width="40%" />
    </picture>
</p>

# T3 Gemstone Challenge · Edge AI

 [![T3 Foundation](./.meta/t3-foundation.svg)](https://www.t3vakfi.org) [![Dokümantasyon](https://img.shields.io/badge/Dok%C3%BCmantasyon-gray?style=flat&logo=Mintlify)](https://docs.t3gemstone.org/tr/competitions/t3-gemstone-challenge/edge-ai/overview) [![Lisans](https://img.shields.io/badge/Lisans-MIT-blue.svg)](#lisans) [![Kart](https://img.shields.io/badge/Kart-T3_Gemstone_O1-0b7285?style=flat)](https://docs.t3gemstone.org/tr/boards/o1/introduction) [![SoC](https://img.shields.io/badge/SoC-TI_AM67A_·_J722S-d9480f?style=flat&logo=texasinstruments&logoColor=white)](https://www.ti.com/product/AM67A) [![Edge AI SDK](https://img.shields.io/badge/Edge_AI_SDK-11.0-5f3dc4?style=flat)](https://www.ti.com/tool/PROCESSOR-SDK-AM67A) [![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat&logo=python&logoColor=white)](https://www.python.org/) [![Tema](https://img.shields.io/badge/Tema-Edge_AI-2f9e44?style=flat)](https://docs.t3gemstone.org/tr/competitions/t3-gemstone-challenge/edge-ai/task) [![Son teslim](https://img.shields.io/badge/Son_teslim-20_Aral%C4%B1k_2026-e8590c?style=flat)](#takvim)

## Nedir?

T3 Gemstone Challenge, T3 Vakfı'nın T3 Gemstone O1 geliştirme kartı etrafında düzenlediği
yarışma serisidir; ilk teması **Edge AI**'dır. Takımlar, O1'e kamera, mikrofon, sensör gibi en az
bir çevre birimi bağlayarak ya da kart üzerindeki sensörleri kullanarak, çıkarımı tamamen kart
üzerinde yapan bir yapay zekâ çözümü geliştirir. Çıkarım sırasında harici hızlandırıcı, uzak
sunucu ya da bulut servisi kullanılamaz.

Bu repo yarışmanın referans reposudur. Takımlar repoyu fork eder ve projelerini
`takimlar/<takim-adi>/` altında [`sablon/`](sablon/) yapısıyla geliştirir. Jüri Heyeti her takımın
klasörünü [`olcum/calistir.py`](olcum/) ile aynı kartta, aynı koşullarda kurup çalıştırır.

Kuralların esas belgesi şartnamedir; özeti [dokümantasyon sitesindedir](https://docs.t3gemstone.org/tr/competitions/t3-gemstone-challenge/edge-ai/overview).
Bu repo ile şartname arasında çelişki olursa şartname geçerlidir.

Bir takım klasörü:

```
takimlar/ornek-takim/
├── README.md        proje açıklaması: problem, model, metrik ve gerekçesi, sonuçlar, demo videosu
├── degerlendir.sh   modeli test-seti/ ile çalıştırıp sonuc.json yazan betik
├── kurulum.sh       isteğe bağlı: model derleme gibi ek kurulum adımları
├── src/             kart üzerinde çalışan uygulama ve çıkarım kodu
├── model/           model dosyaları; repo dışındakiler için HuggingFace/Kaggle bağlantıları (indir.txt)
├── test-seti/       Jüri Heyeti'nin modeli test edeceği veri
├── training/        eğitim, ince ayar ve dönüştürme betikleri
└── requirements.txt, apt.txt
```

### Nasıl değerlendirilir

```
 takimlar/<takim>/ ──kopya──> kurulum (internet açık) ──> degerlendir.sh (internetsiz) ──> sonuc.json
                              │ apt.txt denetimi           │ root, /opt/t3-edgeai-env     │ metrik, FPS,
                              │ requirements.txt →         │ TIDL hızlandırıcısı + CPU    │ gecikme
                              │   takıma özel sanal ortam  │ test-seti/ üzerinde          ▼
                              │ model/indir.txt → SHA256   │ süre sınırıyla       sonuclar/<tarih-saat>/
                              │ kurulum.sh                                      ozet.csv · ozet.json · loglar
```

Metriği takım seçer ve README'de gerekçesini açıklar (şartname md. 5). `sonuc.json`'ın biçimi,
çıktılar ve durum kodları [olcum/README.md](olcum/README.md)'dedir.

### Takvim

Tüm saatler Türkiye saatine (TSİ) göredir.

| Aşama | Tarih |
|---|---|
| Başvuruların açılması | 18 Kasım 2026 |
| Çevrim içi tanıtım oturumu | 21 Kasım 2026, 20.00 |
| Çevrim içi soru-cevap oturumu | 2 Aralık 2026, 20.00 |
| Son başvuru ve teslim | 20 Aralık 2026, 23.59 |
| Jüri Heyeti değerlendirmeleri | 21–26 Aralık 2026 |
| Finalistlerin açıklanması | 27 Aralık 2026 |
| Final projesinin teslimi | 21 Ocak 2027, 23.59 |
| Final Günü | 23 Ocak 2027 |

## Katılım

Kart tarafında referans ortam, O1'in eMMC belleğine yazılmış **T3 Gemstone OS Minimal v2026.1
(Ubuntu 22.04)** imajı ve **t3-gem-o1-edgeai 11.0** paketidir. Bu sürümler 20 Aralık'a kadar
değiştirilmeyecektir. Geliştirme Desktop imajında da yapılabilir; kodu teslimden önce referans
ortamda deneyin.

#### 1. T3 Gemstone Forum'a üye olun ve kartı hazırlayın.

Tüm takım üyelerinin [T3 Gemstone Forum](https://community.t3gemstone.org) üyesi olması zorunludur.
Kartı referans ortama göre hazırlamak, Edge AI paketini kurmak ve modeli hızlandırıcı için
derlemek için [Başlangıç Rehberi](https://docs.t3gemstone.org/tr/competitions/t3-gemstone-challenge/edge-ai/getting-started)'ni izleyin.

#### 2. Repoyu fork edin ve takım klasörünü oluşturun.

```bash
user@host:$ git clone https://github.com/<kullanici-adi>/<fork-adi>.git
user@host:$ cd <fork-adi>
user@host:$ cp -r sablon takimlar/<takim-adi>
```

Klasör adında küçük harf, rakam ve tire kullanın. Takımlar yalnızca kendi klasörlerinde
değişiklik yapar.

#### 3. Modeli, test verisini ve değerlendirme betiğini hazırlayın.

- `model/`: model dosyaları. Repo dışında barındırılacaklar yalnızca HuggingFace ya da Kaggle'da
  olabilir; bağlantıları SHA256 özetleriyle `model/indir.txt`'ye yazın.
- `test-seti/`: Jüri Heyeti'nin modeli test edeceği veri, [Test Seti Biçimleri](https://docs.t3gemstone.org/tr/competitions/t3-gemstone-challenge/edge-ai/test-set-formats)'nden
  görev türünüze uyanla. Eğitimde kullanılan veri buraya konmaz.
- `degerlendir.sh`: modeli `test-seti/` ile çalıştırıp `$CIKTI_DIZINI/sonuc.json`'ı yazar
  ([şablon](sablon/degerlendir.sh)).
- `README.md`: şablondaki başlıkları doldurun.

Klasörünüzün şablona uygun olduğunu bilgisayarınızda denetleyin:

```bash
user@host:$ python3 olcum/kontrol.py --takim <takim-adi>
```

Aynı denetim her commit'te GitHub Actions'ta da çalışır
([`.github/workflows/takim-kontrolu.yml`](.github/workflows/takim-kontrolu.yml)). Fork'larda
Actions varsayılan olarak kapalıdır; fork'unuzun **Actions** sekmesinden bir kez etkinleştirin.

#### 4. Kartta deneyin.

TIDL hızlandırıcısı root yetkisi ister. Betik `/opt/t3-edgeai-env`'deki Edge AI ortam
değişkenlerini kendisi yükler. Repo kök dizininden:

```bash
 sudo python3 olcum/calistir.py --takim <takim-adi>
```

Sonuçlar `sonuclar/<tarih-saat>/` altına yazılır. Jüri Heyeti aynı betikle tüm takımları
çalıştırır.

#### 5. Teslim edin.

Fork'unuzun bağlantısını ve demo videosunu, 20 Aralık 2026 23.59'a kadar
[başvuru formu](https://mth.tc/T3GemstoneChallenge) üzerinden tek adımda teslim edin; bu tarihten
sonra teslim kabul edilmez. Video 30–90 saniye uzunluğunda, kesintisiz ve kurgusuz canlı çalışma
çekimi olmalı ve YouTube'a liste dışı ya da herkese açık olarak yüklenmelidir
([Değerlendirme ve Teslim](https://docs.t3gemstone.org/tr/competitions/t3-gemstone-challenge/edge-ai/evaluation)).

## Yerleşim

| Yol | İçerik |
|------|----------|
| `takimlar/` | Takımların proje klasörleri |
| `sablon/` | Takım klasörü şablonu: README şablonu, `degerlendir.sh`, klasör yapısı |
| `olcum/` | Değerlendirme betiği `calistir.py`, şablon denetimi `kontrol.py` (yalnızca Python standart kütüphanesi) ve belgesi |
| `.github/workflows/` | Her commit'te takım klasörlerini `kontrol.py` ile denetleyen GitHub Actions iş akışı |
| `.meta/` | README görselleri |

## Bu sürümün durumu

Kart olmadan denenenler:

- `olcum/calistir.py`, her durumu kapsayan sahte takımlarla: başarılı, eksik dosya, kurulum
  hatası, çalışma hatası, zaman aşımı ve geçersiz sonuç. HuggingFace'ten indirme ve SHA256
  doğrulaması, arka planda bırakılan süreçlerin durdurulması ve Python 3.10 sözdizimi de denendi.
- `olcum/kontrol.py`, her kurala aykırı takım klasörleriyle ve değiştirilmemiş şablonla; iş akışı
  `actionlint` ile denetlendi.

Kartta denenenler (T3 Gemstone O1, Ubuntu 22.04.5, Edge AI 11.0):

- YOLOX-nano-lite ile hazırlanan bir deneme takımı uçtan uca: betik root olarak,
  `/opt/t3-edgeai-env` yüklü ve internetsiz modda; TIDL hızlandırıcısında görüntü başına yaklaşık
  10,4 ms, 67 görüntüde mAP@0.5 0,3749. mAP hesabı `pycocotools` ile aynı sonucu verdi.
  (2026-11-17)

## Kısıtlar

- Metriği takımın kendi `degerlendir.sh` betiği hesaplar. Jüri Heyeti sonucu kendi kartında yeniden
  üretir, ama sayıyı yazan takımın kodudur.
- `--apt-kur` ile kurulan apt paketleri sisteme kurulur ve sonraki takımları da etkileyebilir.
- Edge AI SDK 11.0'a göre hazırlanmıştır; derlenmiş TIDL dosyaları bu sürüme bağlıdır.
- Kartta `git` kurulu değilse takımların commit bilgisi sonuçlara yazılmaz.

## Destek

- Sorular: [community.t3gemstone.org](https://community.t3gemstone.org) forumundaki T3 Gemstone
  Challenge kategorisinin Edge AI alt kategorisi. Yanıtlar herkese açıktır; kurallarla ilgili
  yanıtlar aynı başlıktaki Sıkça Sorulan Sorular gönderisinde toplanır ve şartnamenin parçası sayılır.
- Kişisel konular (veli onayı, kişisel veriler, kayıt sorunları) ve itirazlar:
  [support@t3gemstone.org](mailto:support@t3gemstone.org)
- Kart dokümantasyonu: [docs.t3gemstone.org](https://docs.t3gemstone.org/tr/introduction)

## Lisans

Takımların çalışmaları, şartname gereği referans repodaki lisans koşullarına tabidir: MIT
([sablon/LICENSE](sablon/LICENSE)). Takımların kullandığı üçüncü taraf model, veri seti ve
kütüphanelerin lisansları kendi README dosyalarında belirtilir.
