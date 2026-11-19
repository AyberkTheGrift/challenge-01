#!/usr/bin/env bash
# Değerlendirme betiği. olcum/calistir.py bu dosyayı takım klasöründe çalıştırır
# (ayrıntılar: olcum/README.md). Betik internet bağlantısı olmadan çalışır; gereken her şey
# kurulum aşamasında (requirements.txt, apt.txt, model/indir.txt, kurulum.sh) hazırlanmış olmalıdır.
#
# Tanımlı ortam değişkenleri:
#   TAKIM_DIZINI   takım klasörünün çalışma kopyası (betik bu klasörde başlar)
#   TEST_SETI      test-seti/ klasörünün yolu
#   CIKTI_DIZINI   sonuçların yazılacağı klasör
#
# Betik, modeli TEST_SETI'ndeki veriyle çalıştırıp CIKTI_DIZINI/sonuc.json dosyasını yazmalıdır:
#   {
#     "metrik_adi": "mAP@0.5",                 zorunlu
#     "metrik_degeri": 0.71,                   zorunlu, sayı
#     "fps": 24.3,                             isteğe bağlı
#     "gecikme_ort_ms": 41.2,                  isteğe bağlı
#     "gecikme_p95_ms": 55.0,                  isteğe bağlı
#     "ornek_sayisi": 500,                     isteğe bağlı
#     "ek_metrikler": {"precision": 0.80}      isteğe bağlı
#   }
set -euo pipefail

# Örnek:
# python3 src/degerlendir.py --test-seti "$TEST_SETI" --sonuc "$CIKTI_DIZINI/sonuc.json"

echo "degerlendir.sh henüz doldurulmadı" >&2
exit 1
