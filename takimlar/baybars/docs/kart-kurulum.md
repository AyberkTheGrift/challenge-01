# Kart kurulum rehberi (referans ortam)

Hedef: T3 Gemstone O1'in eMMC'sinde **Minimal v2026.1 (Ubuntu 22.04)** imajı ve **t3-gem-o1-edgeai 11.0** paketi. Jüri ölçümü bu ortamda yapılır. Kaynaklar: şartname md. 4 "Referans Ortam Kurulumu", [Hızlı Başlangıç](https://docs.t3gemstone.org/tr/quickstart), [eMMC Kullanımı](https://docs.t3gemstone.org/tr/imager/emmc), [Edge AI Kurulum](https://docs.t3gemstone.org/tr/boards/o1/ai/installation).

## 0. Hazırlık

- USB Type-C kablo (bilgisayara), Ethernet kablosu (internet için; ya da imajı yazarken Wi-Fi bilgisi girilir), USB-TTL dönüştürücü (isteğe bağlı ama sorun gidermede çok işe yarar).
- Bilgisayara **Gemstone Imager**: https://www.t3gemstone.org/software (ulaşılamazsa https://packages.t3gemstone.org/imager/).
- **Uyarı:** eMMC'ye yazmak kartın mevcut içeriğini siler. Kartta saklanacak bir şey varsa önce yedekle.

## 1. Imajı eMMC'ye yaz (USB DFU)

1. Kartı tamamen kapat, güç bağlantısını kes. (Çalışırken DFU moduna geçmek eMMC'yi bozabilir.)
2. Bootmode switch'i **USB DFU** konumuna getir (switch diyagramı: Hızlı Başlangıç ve eMMC sayfalarında).
3. USB-C kablosunu kartın DFU portuna ve bilgisayara tak, güç ver.
4. Gem Imager'ı **yönetici olarak** çalıştır. Kartı seç, **İşletim Sistemi Seç**'ten **Minimal (Ubuntu 22.04, v2026.1)** imajını seç, **Hedef Seç**'ten **USB DFU**'yu seç.
5. **İleri**'de özelleştirme: kullanıcı adı `gemstone`, 8 karakterlik bir parola, **Enable SSH** açık, internet için Wi-Fi bilgisi (Ethernet kullanacaksan gerekmez). Parolayı bir yere yaz, **repoya veya belgeye koyma** (şartname md. 8).
6. **Yaz**'a bas. Yazma bitene kadar kabloyu çıkarma, güç kesme.
7. Bitince kartı kapat, bootmode switch'i **eMMC** konumuna al, güç ver.

> Boot'u izlemek için UART: 115200 baud.

## 2. İlk bağlantı

- Ethernet ile ağa bağlıysa kartın IP'sini router'dan öğren, `ssh gemstone@<ip>`.
- USB-C ile bilgisayara bağlıyken (Gadgets açıksa) doğrudan `ssh gemstone@192.168.7.2` olabilir (Hızlı Başlangıç §2.3). Bu yolda kartın internete çıkması için ayrıca Ethernet/Wi-Fi gerekir, `apt` internet ister.
- Olmuyorsa USB-TTL ile seri konsol (115200).

## 3. Edge AI paketi ve overlay (şartname adım 2–3)

```bash
sudo apt update
sudo apt install t3-gem-o1-edgeai git
sudo nano /boot/uEnv.txt
```

`/boot/uEnv.txt` içinde `overlays=` satırının **sonuna bir boşlukla** şunu ekle, satırı bölme:

```
k3-am67a-t3-gem-o1-edgeai-apps.dtbo
```

Kaydet ve yeniden başlat:

```bash
sudo reboot
```

## 4. Kurulumu doğrula (şartname adım 4)

```bash
sudo su
source /opt/t3-edgeai-env
python3 -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

Beklenen: `source` komutu `SDK: 11_00_00` yazmalı, son komutun listesinde **`TIDLExecutionProvider`** bulunmalı. Bu çıktıyı kaydet, takıma hem kanıt hem referans olur.

## 5. Repoyu karta al ve denetle (şartname adım 5–7)

Fork'unu klonla (`<kullanici-adi>` ve `<fork-adi>` kendi bilgilerin):

```bash
git clone https://github.com/<kullanici-adi>/<fork-adi>.git
cd <fork-adi>
python3 olcum/kontrol.py --takim baybars
sudo python3 olcum/calistir.py --takim baybars
```

Model eklenmeden `calistir.py` zaten başarısız olur (`eksik_dosya` ya da `kurulum_hatasi`); bu, hattın çalıştığını görmek için yine de faydalı. Gerçek ilk sınama: **organizatörün YOLOX-nano-lite deneme takımı** referans repoda varsa aynı komutla çalıştırıp süreyi (yaklaşık 10,4 ms) ve mAP'i (67 görüntüde 0,3749) kendi kartında yeniden üret.

## 6. Kamera sınaması

Kamera bağlantısı: https://docs.t3gemstone.org/tr/boards/o1/peripherals/camera. Hazır gerçek zamanlı örnek: https://github.com/t3gemstone/examples/tree/main/camera (GStreamer, hızlandırıcıyla tespit, tarayıcıya akış). Önce bu örnek çalışsın; kendi kodumuza sonra geçeriz.

## Sorun giderme

- **`TIDLExecutionProvider` listede yok:** `uEnv.txt`'deki overlay satırını, yeniden başlatıldığını ve `sudo su` + `source /opt/t3-edgeai-env` yapıldığını kontrol et.
- **`apt` paket bulamıyor:** kartın internete çıktığını doğrula (`ping 8.8.8.8`, `apt update` hatasız mı).
- **DFU'da kart görünmüyor:** kartın kapalı olduğundan, switch konumundan ve kablonun doğru porta takılı olduğundan emin ol. Imager'ı yönetici çalıştır.
- **Boot olmuyor:** UART konsolundan çıktıyı izle, switch'in eMMC konumunda olduğuna bak.

## Takıma bildirilecekler (kurulum bitince)

1. `source /opt/t3-edgeai-env` çıktısı (SDK satırı) ve `get_available_providers()` listesi.
2. `uname -a` ve `apt-cache policy t3-gem-o1-edgeai` (sürüm).
3. Varsa karşılaşılan hatalar ve çözümleri.
