#!/usr/bin/env bash
# Değerlendirme betiği (olcum/calistir.py çağırır): modeli test-seti/ ile çalıştırıp sonuc.json yazar.
# Ortam değişkenleri: TAKIM_DIZINI, TEST_SETI, CIKTI_DIZINI (olcum/README.md)
set -euo pipefail

python3 src/degerlendir.py --test-seti "$TEST_SETI" --model-dizini model --sonuc "$CIKTI_DIZINI/sonuc.json"
