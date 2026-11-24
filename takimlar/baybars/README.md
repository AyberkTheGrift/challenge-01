# Baybars: duba (şamandıra) tespiti

T3 Gemstone O1 üzerinde, kameradan alınan görüntüde dubaları gerçek zamanlı tespit eden ve çıkarımı tamamen kartın TIDL hızlandırıcısında yapan bir nesne tespiti uygulaması.

> Durum: iskelet kuruldu (değerlendirme betiği, metrik hesabı ve testleri hazır). Model, veri seti ve çıkarım kodu henüz eklenmedi; bu yüzden aşağıdaki bazı bölümler "henüz doldurulmadı" olarak işaretlidir.

## Problem ve kullanım senaryosu

Henüz doldurulmadı: insansız deniz aracı için parkur dubalarının tespiti; görüntünün araç üzerinde (uçta) işlenmesinin gerekçesi (iletişim bağlantısına ve buluta bağımlı olmadan, düşük gecikmeyle karar verme).

## Donanım düzeneği

Henüz doldurulmadı: kamera modeli ve bağlantı şekli (MIPI CSI ya da USB).

![Düzenek](docs/duzenek.jpg)

## Kurulum ve çalıştırma

Referans ortam: T3 Gemstone OS Minimal v2026.1 (Ubuntu 22.04) + t3-gem-o1-edgeai 11.0.

Kurulum tamamlandıktan sonra uygulama internet bağlantısı olmadan çalışmalıdır.

```bash
# Kurulum (requirements.txt, apt.txt, varsa model dosyalarının indirilmesi ve kurulum.sh)
# Henüz doldurulmadı: model eklendiğinde kurulum.sh ve requirements.txt yazılacak

# Uygulamayı çalıştırma
# Henüz doldurulmadı: src/ altındaki kamera uygulaması eklendiğinde yazılacak

# test-seti/ ile değerlendirme (repo kök dizininden; degerlendir.sh'ı çalıştırır)
sudo python3 olcum/calistir.py --takim baybars
```

Kartsız denenebilen testler (metrik hesabı ve değerlendirme akışı, yalnızca numpy):

```bash
python3 takimlar/baybars/src/test_olcum.py
```

## Model

- **Mimari:** Henüz doldurulmadı (YOLOX-nano-lite ile başlanması planlanıyor)
- **Model biçimi:** Henüz doldurulmadı (ONNX + TIDL artifact)
- **Model dosyaları:** Henüz doldurulmadı
- **Görev türü:** nesne tespiti (tek sınıf: duba)
- **Başarım metriği ve gerekçesi:** mAP@0.5. Tespit görevinde hem kaçırılan hem yanlış tespit edilen nesneyi cezalandırır; güven eşiğine bağlı değildir. Ek olarak mAP@0.5:0.95, belirli güven eşiğinde precision/recall, FPS ve gecikme (ortalama ve p95) raporlanır. Hesap `src/olcum.py` içindedir ve pycocotools'un COCOeval akışıyla aynı sonucu verir: geçerli kutulu rastgele veride 8 farklı denemede en büyük fark 1e-16 mertebesinde ölçüldü.
- **Eğitim verisi:** Henüz doldurulmadı
- **Test verisi:** Henüz doldurulmadı. Plan: eğitimde hiç kullanılmayan, farklı gün ve sahnelerde çekilmiş gerçek görüntüler (en fazla 500 örnek); biçim: Edge AI nesne tespiti test seti biçimi (`goruntuler/`, `etiketler/` YOLO, `siniflar.txt`).
- **Eğitim süreci:** Henüz doldurulmadı
- **Hızlandırıcıya derleme:** Henüz doldurulmadı
- **Hızlandırıcıda / CPU'da çalışan kısım:** Henüz doldurulmadı
- **Hazır model kullanıldıysa:** Henüz doldurulmadı

## Sonuçlar

Henüz doldurulmadı. `sudo python3 olcum/calistir.py --takim baybars` çıktısındaki `sonuc.json` değerleri buraya yazılacak.

| | Değer |
|---|---|
| mAP@0.5 | |
| FPS | |
| Gecikme ortalama / p95 (ms) | |

## Demo videosu

Henüz doldurulmadı: YouTube bağlantısı (30-90 saniye, kesintisiz ve kurgusuz canlı çalışma çekimi).

## Bu yarışmadaki katkı

Proje bu yarışma için geliştirilmektedir.

## Kullanılan yapay zekâ araçları

Geliştirme sırasında Claude (Anthropic) ile kod taslağı, belge okuma ve test yazımı yapıldı; üretilen kod ve sonuçlar takım tarafından çalıştırılıp doğrulanır.

## Takım ve lisans

- **Takım:** Baybars
- **Takım Kaptanı:** Henüz doldurulmadı
- **Üyeler:** Henüz doldurulmadı
- **Danışman:** Henüz doldurulmadı
- **Lisans:** Bu repodaki çalışmalar referans repodaki lisans koşullarına tabidir; [LICENSE](LICENSE) dosyasına bakın.
- **Üçüncü taraf model, veri seti ve kütüphaneler:** Henüz doldurulmadı
