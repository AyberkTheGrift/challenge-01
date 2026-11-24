"""test-seti/ üzerinde modeli çalıştırır, metrikleri hesaplar, sonuc.json yazar.

Kullanım (degerlendir.sh bunu çağırır):
    python3 src/degerlendir.py --test-seti test-seti --model-dizini model --sonuc cikti/sonuc.json

Test seti biçimi (Edge AI test seti biçimleri, nesne tespiti):
    test-seti/siniflar.txt            her satırda bir sınıf adı (sıra = sınıf numarası, 0'dan başlar)
    test-seti/goruntuler/<ad>.jpg|png
    test-seti/etiketler/<ad>.txt      YOLO biçimi; nesne yoksa boş dosya
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cikarim import Tespitci, tespitci_olustur  # noqa: E402
from olcum import kesinlik_anma, tespit_metrikleri, yolo_etiketi_oku  # noqa: E402

GORUNTU_UZANTILARI = (".jpg", ".jpeg", ".png")
ISINMA_TEKRARI = 5
METRIK_GUVEN_ESIGI = 0.25  # precision/recall için; mAP bütün güven değerlerini kullanır


def test_setini_oku(test_seti: Path) -> tuple[list[str], list[Path], list[np.ndarray]]:
    siniflar = [satir.strip() for satir in (test_seti / "siniflar.txt").read_text(encoding="utf-8").splitlines()
                if satir.strip()]
    goruntu_klasoru, etiket_klasoru = test_seti / "goruntuler", test_seti / "etiketler"
    goruntuler = sorted(yol for yol in goruntu_klasoru.iterdir() if yol.suffix.lower() in GORUNTU_UZANTILARI)
    if not goruntuler:
        raise FileNotFoundError(f"{goruntu_klasoru} içinde görüntü yok")
    etiketler = []
    for goruntu in goruntuler:
        etiket_yolu = etiket_klasoru / (goruntu.stem + ".txt")
        if not etiket_yolu.is_file():
            raise FileNotFoundError(f"{goruntu.name} için etiket yok: {etiket_yolu} (nesnesiz görüntünün etiketi boş dosya olmalı)")
        etiketler.append(yolo_etiketi_oku(etiket_yolu))
    kullanilan = {int(sinif) for etiket in etiketler for sinif in etiket[:, 0]}
    if kullanilan and max(kullanilan) >= len(siniflar):
        raise ValueError(f"etiketlerde sinif {max(kullanilan)} var ama siniflar.txt'de {len(siniflar)} sınıf yazılı")
    return siniflar, goruntuler, etiketler


def gecerli_kutu_mu(tespit: np.ndarray) -> np.ndarray:
    """Sonlu değerli ve pozitif alanlı kutuları işaretler (ters ya da sıfır alanlı kutu hiçbir nesneyle
    eşleşemez; mAP hesabını bozmasın diye elenir ve sayısı ek_metrikler'e yazılır)."""
    sonlu = np.isfinite(tespit).all(axis=1)
    return sonlu & (tespit[:, 4] > tespit[:, 2]) & (tespit[:, 5] > tespit[:, 3])


def degerlendir_et(test_seti: Path, tespitci: Tespitci) -> dict:
    siniflar, goruntuler, etiketler = test_setini_oku(test_seti)
    girdiler = [tespitci.yukle(yol) for yol in goruntuler]  # okuma süre ölçümü dışında
    for _ in range(ISINMA_TEKRARI):
        tespitci.tespit_et(girdiler[0])
    tahminler, sureler_ms, gecersiz = [], [], 0
    for girdi in girdiler:
        baslangic = time.perf_counter()
        tespit = np.asarray(tespitci.tespit_et(girdi), dtype=np.float64).reshape(-1, 6)
        sureler_ms.append((time.perf_counter() - baslangic) * 1000.0)
        gecerli = gecerli_kutu_mu(tespit)
        gecersiz += int((~gecerli).sum())
        tahminler.append(tespit[gecerli])
    metrik = tespit_metrikleri(etiketler, tahminler, len(siniflar))
    esikte = kesinlik_anma(etiketler, tahminler, len(siniflar), METRIK_GUVEN_ESIGI)
    ortalama = float(np.mean(sureler_ms))
    return {
        "metrik_adi": "mAP@0.5",
        "metrik_degeri": round(metrik["mAP@0.5"], 4),
        "fps": round(1000.0 / ortalama, 2),
        "gecikme_ort_ms": round(ortalama, 2),
        "gecikme_p95_ms": round(float(np.percentile(sureler_ms, 95)), 2),
        "ornek_sayisi": len(goruntuler),
        "ek_metrikler": {
            "mAP@0.5:0.95": round(metrik["mAP@0.5:0.95"], 4),
            f"precision@conf{METRIK_GUVEN_ESIGI}": round(esikte["precision"], 4),
            f"recall@conf{METRIK_GUVEN_ESIGI}": round(esikte["recall"], 4),
            "elenen_gecersiz_kutu": gecersiz,
        },
    }


def sonucu_yaz(sonuc: dict, yol: Path) -> None:
    def sonlu_mu(deger):
        if isinstance(deger, dict):
            return all(sonlu_mu(alt) for alt in deger.values())
        return not isinstance(deger, float) or math.isfinite(deger)

    if not sonlu_mu(sonuc):
        raise ValueError(f"sonuçta sonsuz ya da NaN değer var: {sonuc}")
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".json.tmp")
    gecici.write_text(json.dumps(sonuc, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(gecici, yol)


def main() -> int:
    ayristirici = argparse.ArgumentParser(description="Baybars: test-seti değerlendirmesi")
    ayristirici.add_argument("--test-seti", type=Path, required=True)
    ayristirici.add_argument("--model-dizini", type=Path, default=Path("model"))
    ayristirici.add_argument("--sonuc", type=Path, required=True)
    ayarlar = ayristirici.parse_args()
    siniflar, _, _ = test_setini_oku(ayarlar.test_seti)
    tespitci = tespitci_olustur(ayarlar.model_dizini, len(siniflar))
    sonuc = degerlendir_et(ayarlar.test_seti, tespitci)
    sonucu_yaz(sonuc, ayarlar.sonuc)
    print(json.dumps(sonuc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
