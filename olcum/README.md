# Değerlendirme betiği

`calistir.py`, [`takimlar/`](../takimlar/) altındaki her takım klasörünü sırayla kurar, takımın `degerlendir.sh` betiğini çalıştırır ve sonuçları kaydeder. Jüri Heyeti betiği referans ortamdaki kartta çalıştırır; takımlar da kendi klasörlerini kendi kartlarında deneyebilir.

## Kullanım

TIDL hızlandırıcısı root yetkisi istediği için betiği repo kök dizininden `sudo` ile çalıştırın:

```bash
# Tüm takımlar
sudo python3 olcum/calistir.py

# Yalnızca bir takım (ör. takımın kendi kartında denemesi için)
sudo python3 olcum/calistir.py --takim ornek-takim
```

Betik `/opt/t3-edgeai-env` dosyasındaki Edge AI ortam değişkenlerini kendisi yükler; dosyayı önceden `source` etmeniz gerekmez.

Gereksinimler: Python 3.10 ya da üstü ve `requirements.txt` içeren takımlar için `pip`. İnternetsiz çalıştırma için `unshare` ve `ip` komutları gerekir. Bunların hepsi referans ortamda hazır gelir; `python3-venv` paketi gerekmez.

| Seçenek | Açıklama | Varsayılan |
|---|---|---|
| `--takim AD` | Yalnızca bu takımı çalıştırır; birden çok kez verilebilir. | tüm takımlar |
| `--cikti DIZIN` | Sonuçların yazılacağı klasör. | `sonuclar/<tarih-saat>/` |
| `--zaman-asimi SN` | `degerlendir.sh` için süre sınırı. | 1800 |
| `--kurulum-zaman-asimi SN` | Her kurulum adımı için süre sınırı. | 3600 |
| `--apt-kur` | `apt.txt`'deki eksik paketleri `sudo apt-get` ile kurar. | kapalı |
| `--internet-acik` | `degerlendir.sh`'ı internet bağlantısıyla çalıştırır. | kapalı |
| `--sakla` | Takımların çalışma kopyalarını ve sanal ortamlarını silmez. | kapalı |
| `--takimlar-dizini DIZIN` | Takım klasörlerinin bulunduğu klasör. | `takimlar/` |

Bir takımın değerlendirmesi başarısız olsa da betik diğer takımlarla devam eder. Tüm takımlar başarılıysa çıkış kodu 0, en az biri başarısızsa 1'dir.

## Her takım için yapılanlar

1. Takım klasöründe `degerlendir.sh` ve `test-seti/` bulunduğu denetlenir.
2. Takım klasörü bir çalışma kopyasına alınır; repodaki dosyalar değişmez.
3. Kurulum yapılır (internet açık):
   - `apt.txt`'deki paketlerin kurulu olduğu denetlenir; `--apt-kur` verilmişse eksikler kurulur.
   - Takıma özel bir Python sanal ortamı açılır ve `requirements.txt` bu ortama kurulur. Sanal ortam referans ortamdaki paketleri (Edge AI paketi dahil) görür; bir takımın kurduğu paketler diğer takımları etkilemez.
   - `model/indir.txt`'deki dosyalar indirilir ve SHA256 özetleri doğrulanır. Yalnızca HuggingFace ve Kaggle adreslerine izin verilir (şartname md. 4).
   - Takım klasöründe `kurulum.sh` varsa çalıştırılır (ör. modeli hızlandırıcı için derlemek).
4. `degerlendir.sh` internet bağlantısı olmadan çalıştırılır (şartname md. 4) ve süresi ölçülür. Betik bittiğinde arka planda bıraktığı süreçler de durdurulur.
5. `sonuc.json` okunur ve doğrulanır.

## degerlendir.sh

Betik takım klasörünün çalışma kopyasında, takımın sanal ortamı etkinken başlar. Şu ortam değişkenleri tanımlıdır:

| Değişken | İçerik |
|---|---|
| `TAKIM_DIZINI` | Takım klasörünün çalışma kopyası |
| `TEST_SETI` | `test-seti/` klasörünün yolu |
| `CIKTI_DIZINI` | Sonuçların yazılacağı klasör |

Betik, modeli `TEST_SETI`'ndeki veriyle çalıştırıp `$CIKTI_DIZINI/sonuc.json` dosyasını yazmalıdır. `CIKTI_DIZINI`'ne yazılan diğer dosyalar (ör. tahminler) de sonuçlarla birlikte saklanır.

```json
{
  "metrik_adi": "mAP@0.5",
  "metrik_degeri": 0.71,
  "fps": 24.3,
  "gecikme_ort_ms": 41.2,
  "gecikme_p95_ms": 55.0,
  "ornek_sayisi": 500,
  "ek_metrikler": {"precision": 0.80, "recall": 0.66}
}
```

| Alan | Zorunlu | Tür |
|---|---|---|
| `metrik_adi` | evet | metin |
| `metrik_degeri` | evet | sayı |
| `fps`, `gecikme_ort_ms`, `gecikme_p95_ms`, `ornek_sayisi` | hayır | sayı |
| `ek_metrikler` | hayır | metrik adından sayıya eşleme |

Şablon: [`sablon/degerlendir.sh`](../sablon/degerlendir.sh).

## Çıktılar

```text
sonuclar/<tarih-saat>/
├── ozet.json          ortam bilgisi ve tüm takımların sonuçları
├── ozet.csv           takımların sonuçları, tablo olarak
└── <takim>/
    ├── durum.json     takımın sonucu
    ├── kurulum.log    kurulum adımlarının çıktısı
    ├── calistirma.log degerlendir.sh'ın çıktısı
    └── cikti/         degerlendir.sh'ın yazdığı dosyalar (sonuc.json dahil)
```

Ortam bilgisi; kartı, işletim sistemini, `t3-gem-o1-edgeai` sürümünü ve betiğin commit'ini içerir. Sürümler referans ortamdan farklıysa betik başlarken uyarı verir.

Her takımın sonucunda takım klasörünün son commit'i (`commit`) ve commit edilmemiş değişiklik olup olmadığı (`commit_disi_degisiklik`) da kaydedilir.

| Durum | Anlamı |
|---|---|
| `basarili` | `degerlendir.sh` başarıyla bitti ve geçerli bir `sonuc.json` yazdı. |
| `eksik_dosya` | `degerlendir.sh` ya da `test-seti/` yok. |
| `kurulum_hatasi` | `apt.txt`, `requirements.txt`, `model/indir.txt` ya da `kurulum.sh` adımı başarısız oldu. |
| `calistirma_hatasi` | `degerlendir.sh` sıfırdan farklı bir çıkış koduyla bitti. |
| `zaman_asimi` | `degerlendir.sh` süre sınırı içinde bitmedi. |
| `sonuc_gecersiz` | `sonuc.json` yazılmadı ya da biçimi hatalı. |
| `olcum_hatasi` | Betiğin kendisinden kaynaklanan beklenmeyen bir hata oluştu. |

## Şablon denetimi: kontrol.py

`kontrol.py`, takım klasörlerinin [`sablon/`](../sablon/) yapısına ve şartnameye uygunluğunu modeli
çalıştırmadan denetler. Her commit'te GitHub Actions'ta çalışır
([`.github/workflows/takim-kontrolu.yml`](../.github/workflows/takim-kontrolu.yml)): push'larda tüm
takımlar, pull request'lerde yalnızca değişikliğin dokunduğu takımlar denetlenir. Hatalar commit'i
başarısız gösterir; uyarılar yalnızca bildirilir.

```bash
python3 olcum/kontrol.py                       # tüm takımlar
python3 olcum/kontrol.py --takim ornek-takim   # yalnızca bir takım
```

| Denetim | Hata | Uyarı |
|---|---|---|
| Klasör adı | Küçük harf, rakam ve tire dışında karakter | |
| Zorunlu dosyalar | `README.md`, `LICENSE`, `degerlendir.sh`, `test-seti/` ya da `model/` yok | `src/` boş ya da yok |
| `README.md` | Şablondaki bir `##` başlığı yok | Doldurulmamış yer tutucu, silinmemiş şablon açıklaması, var olmayan dosyaya bağlantı |
| `LICENSE` | Lisans metni değiştirilmiş (yalnızca Copyright satırı değişebilir) | `[takım adı]` doldurulmamış |
| `degerlendir.sh`, `kurulum.sh` | Şablondaki haliyle bırakılmış, bash sözdizimi hatası | |
| `requirements.txt`, `apt.txt` | Sürüm sabitlenmemiş satır (`paket==sürüm`, `paket=sürüm`) | |
| `model/` | Model dosyası da `indir.txt` de yok; `indir.txt`'de HuggingFace/Kaggle dışı adres, hatalı ya da sıfır SHA256 | |
| `test-seti/` | Boş | 500'den fazla örnek, dosya adı kuralına uymayan dosya, etiketi ya da maskesi olmayan örnek, `siniflar.txt`'de olmayan sınıf klasörü |
| Tüm dosyalar | Erişim belirteci, API anahtarı ya da özel anahtar (şartname md. 8) | 50 MB'tan büyük dosya |
| Pull request kapsamı | | Birden çok takımın klasörüne ya da takım klasörü dışına dokunan değişiklik |

## Uyarılar

- Betik takımların kodunu çalıştırır. Yalnızca bu iş için ayrılmış bir kartta çalıştırın.
- `--apt-kur` ile kurulan apt paketleri sisteme kurulur ve sonraki takımları da etkileyebilir.
- Takımlar sırayla, tek tek çalıştırılır. Süre ölçümlerinin karşılaştırılabilir olması için değerlendirme sırasında kartta başka iş çalıştırmayın.
- Betik root olarak çalışmazsa uyarı verir: TIDL hızlandırıcısının kullandığı aygıtlara yalnızca root erişebilir. Root olmayan kullanıcıda internetsiz çalıştırma için ayrıca bir kullanıcı ad alanı açılır.
- Ortam bilgisine Edge AI paketlerinin sürümleri (`t3-gem-o1-edgeai`, `t3-edgeai-dev`, `arm-tidl-j722s`, `t3-onnxruntime`) yazılır. `git` kurulu değilse takımların commit bilgisi boş kalır.
