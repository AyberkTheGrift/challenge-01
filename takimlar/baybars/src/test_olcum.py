"""Metrik ve değerlendirme akışı testleri (kartsız, yalnızca numpy):
    python3 src/test_olcum.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cikarim import Tespitci  # noqa: E402
from degerlendir import degerlendir_et, sonucu_yaz  # noqa: E402
from olcum import iou_matrisi, kesinlik_anma, tespit_metrikleri, yolo_etiketi_oku  # noqa: E402

KUTU = [0.2, 0.2, 0.6, 0.6]


def gt_dizisi(*kutular, sinif=0):
    return np.array([[sinif, *kutu] for kutu in kutular], dtype=np.float64).reshape(-1, 5)


def tahmin_dizisi(*kayitlar, sinif=0):
    return np.array([[sinif, guven, *kutu] for guven, kutu in kayitlar], dtype=np.float64).reshape(-1, 6)


class IouTesti(unittest.TestCase):
    def test_ayni_kutu_bir(self):
        kutu = np.array([KUTU])
        self.assertAlmostEqual(float(iou_matrisi(kutu, kutu)[0, 0]), 1.0)

    def test_ayrik_kutu_sifir(self):
        self.assertEqual(float(iou_matrisi(np.array([KUTU]), np.array([[0.7, 0.7, 0.9, 0.9]]))[0, 0]), 0.0)

    def test_yarim_ortusme(self):
        # 0.4x0.4 iki kutu, yatayda yarı kayık: kesişim 0.2*0.4, birleşim 2*0.16-0.08 -> 1/3
        kayik = np.array([[0.4, 0.2, 0.8, 0.6]])
        self.assertAlmostEqual(float(iou_matrisi(np.array([KUTU]), kayik)[0, 0]), 1 / 3, places=6)


class MapTesti(unittest.TestCase):
    def test_kusursuz_tahmin(self):
        gt = [gt_dizisi(KUTU), gt_dizisi(KUTU)]
        tahmin = [tahmin_dizisi((0.9, KUTU)), tahmin_dizisi((0.8, KUTU))]
        sonuc = tespit_metrikleri(gt, tahmin, 1)
        self.assertAlmostEqual(sonuc["mAP@0.5"], 1.0)
        self.assertAlmostEqual(sonuc["mAP@0.5:0.95"], 1.0)

    def test_tahmin_yok(self):
        sonuc = tespit_metrikleri([gt_dizisi(KUTU)], [np.zeros((0, 6))], 1)
        self.assertEqual(sonuc["mAP@0.5"], 0.0)

    def test_tekrarli_tespit_kesinligi_dusurmez_ama_fazlalik_yanlis_sayilir(self):
        # aynı nesneye iki tespit: ilki doğru, ikincisi yanlış; anma 1'e ilk tespitte ulaşıldığı için AP = 1
        sonuc = tespit_metrikleri([gt_dizisi(KUTU)], [tahmin_dizisi((0.9, KUTU), (0.8, KUTU))], 1)
        self.assertAlmostEqual(sonuc["mAP@0.5"], 1.0)
        olcu = kesinlik_anma([gt_dizisi(KUTU)], [tahmin_dizisi((0.9, KUTU), (0.8, KUTU))], 1)
        self.assertEqual((olcu["dogru_pozitif"], olcu["yanlis_pozitif"], olcu["kacirilan"]), (1, 1, 0))

    def test_yarim_anma_pycocotools_degeri(self):
        # İki gerçek kutu, biri bulundu, diğeri kaçtı, uzakta bir yanlış alarm var:
        # anma 0.5'e kadar kesinlik 1 -> 101 noktadan 51'i doğru = 51/101 (COCOeval ile aynı)
        gt = [gt_dizisi(KUTU, [0.7, 0.7, 0.9, 0.9])]
        tahmin = [tahmin_dizisi((0.9, KUTU), (0.8, [0.0, 0.7, 0.1, 0.8]))]
        self.assertAlmostEqual(tespit_metrikleri(gt, tahmin, 1)["mAP@0.5"], 51 / 101, places=9)

    def test_iou_esigi_etkisi(self):
        kayik = [0.25, 0.2, 0.65, 0.6]  # IoU ~ 0.78
        sonuc = tespit_metrikleri([gt_dizisi(KUTU)], [tahmin_dizisi((0.9, kayik))], 1)
        self.assertAlmostEqual(sonuc["mAP@0.5"], 1.0)
        self.assertLess(sonuc["mAP@0.5:0.95"], 1.0)
        self.assertGreater(sonuc["mAP@0.5:0.95"], 0.0)

    def test_yanlis_sinif_sayilmaz(self):
        gt = [gt_dizisi(KUTU, sinif=0)]
        tahmin = [tahmin_dizisi((0.9, KUTU), sinif=1)]
        sonuc = tespit_metrikleri(gt, tahmin, 2)
        self.assertEqual(sonuc["mAP@0.5"], 0.0)
        self.assertIsNone(sonuc["sinif_ap50"][1])  # sınıf 1'in gerçek kutusu yok: ortalamaya girmez

    def test_nesnesiz_test_seti_hata(self):
        with self.assertRaises(ValueError):
            tespit_metrikleri([np.zeros((0, 5))], [np.zeros((0, 6))], 1)


class AkisTesti(unittest.TestCase):
    class GtTespitci(Tespitci):
        """Gerçek kutuları aynen döndürür: mAP 1 çıkmalı (akışın uçtan uca doğrulaması)."""

        def __init__(self, etiket_klasoru):
            self.etiket_klasoru = etiket_klasoru

        def yukle(self, goruntu_yolu):
            return goruntu_yolu.stem

        def tespit_et(self, girdi):
            gt = yolo_etiketi_oku(self.etiket_klasoru / (girdi + ".txt"))
            return np.concatenate([gt[:, :1], np.ones((len(gt), 1)), gt[:, 1:]], axis=1)

    def test_uctan_uca(self):
        with tempfile.TemporaryDirectory() as gecici:
            kok = Path(gecici)
            (kok / "goruntuler").mkdir()
            (kok / "etiketler").mkdir()
            (kok / "siniflar.txt").write_text("duba\n", encoding="utf-8")
            for ad, etiket in (("a_001", "0 0.4 0.4 0.4 0.4\n"), ("a_002", ""), ("a_003", "0 0.5 0.5 0.2 0.2\n0 0.2 0.2 0.1 0.1\n")):
                (kok / "goruntuler" / f"{ad}.jpg").write_bytes(b"")
                (kok / "etiketler" / f"{ad}.txt").write_text(etiket, encoding="utf-8")
            sonuc = degerlendir_et(kok, self.GtTespitci(kok / "etiketler"))
            self.assertEqual(sonuc["ornek_sayisi"], 3)
            self.assertAlmostEqual(sonuc["metrik_degeri"], 1.0)
            self.assertEqual(sonuc["metrik_adi"], "mAP@0.5")
            yol = kok / "cikti" / "sonuc.json"
            sonucu_yaz(sonuc, yol)
            self.assertEqual(json.loads(yol.read_text(encoding="utf-8"))["ornek_sayisi"], 3)

    def test_etiketi_eksik_goruntu_hata(self):
        with tempfile.TemporaryDirectory() as gecici:
            kok = Path(gecici)
            (kok / "goruntuler").mkdir()
            (kok / "etiketler").mkdir()
            (kok / "siniflar.txt").write_text("duba\n", encoding="utf-8")
            (kok / "goruntuler" / "a_001.jpg").write_bytes(b"")
            with self.assertRaises(FileNotFoundError):
                degerlendir_et(kok, self.GtTespitci(kok / "etiketler"))

    def test_gecersiz_kutular_elenir(self):
        from degerlendir import gecerli_kutu_mu
        tespit = np.array([[0, 0.9, 0.2, 0.2, 0.6, 0.6],      # geçerli
                           [0, 0.9, 0.6, 0.2, 0.2, 0.6],      # ters x
                           [0, 0.9, 0.2, 0.2, 0.2, 0.6],      # sıfır genişlik
                           [0, 0.9, np.nan, 0.2, 0.6, 0.6]])  # NaN
        self.assertEqual(gecerli_kutu_mu(tespit).tolist(), [True, False, False, False])

    def test_sonsuz_deger_reddedilir(self):
        with tempfile.TemporaryDirectory() as gecici:
            with self.assertRaises(ValueError):
                sonucu_yaz({"metrik_adi": "x", "metrik_degeri": float("nan")}, Path(gecici) / "sonuc.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
