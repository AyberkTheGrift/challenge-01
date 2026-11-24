"""Nesne tespiti metrikleri (yalnızca numpy).

Hesap pycocotools'un COCOeval akışını izler: sınıf bazında AP, 101 noktalı anma örneklemesi,
görüntü başına en çok 100 tespit, açgözlü eşleştirme (en yüksek güvenli tespit önce).
Kutular normalleştirilmiş (0-1) xyxy biçimindedir; IoU eksen ölçeklemesinden etkilenmediği
için piksel koordinatlarıyla aynı sonucu verir.

Veri biçimleri
  gt_listesi[i]     (G, 5)  [sinif, x1, y1, x2, y2]            i. görüntünün gerçek kutuları
  tahmin_listesi[i] (M, 6)  [sinif, guven, x1, y1, x2, y2]     i. görüntünün tespitleri
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

ANMA_NOKTALARI = np.linspace(0.0, 1.0, 101)
IOU_ESIKLERI = np.linspace(0.5, 0.95, 10)
EN_COK_TESPIT = 100


def iou_matrisi(kutular_a: np.ndarray, kutular_b: np.ndarray) -> np.ndarray:
    """(A, 4) ve (B, 4) xyxy kutuları için (A, B) IoU matrisi."""
    if len(kutular_a) == 0 or len(kutular_b) == 0:
        return np.zeros((len(kutular_a), len(kutular_b)))
    ust_sol = np.maximum(kutular_a[:, None, :2], kutular_b[None, :, :2])
    alt_sag = np.minimum(kutular_a[:, None, 2:], kutular_b[None, :, 2:])
    kesisim = np.clip(alt_sag - ust_sol, 0.0, None).prod(axis=-1)
    alan_a = (kutular_a[:, 2] - kutular_a[:, 0]) * (kutular_a[:, 3] - kutular_a[:, 1])
    alan_b = (kutular_b[:, 2] - kutular_b[:, 0]) * (kutular_b[:, 3] - kutular_b[:, 1])
    birlesim = alan_a[:, None] + alan_b[None, :] - kesisim
    return kesisim / np.maximum(birlesim, 1e-12)


def yolo_etiketi_oku(yol: Path) -> np.ndarray:
    """YOLO etiket dosyasını (G, 5) [sinif, x1, y1, x2, y2] dizisine çevirir. Boş dosya = nesne yok."""
    yol = Path(yol)
    satirlar = [satir.split() for satir in yol.read_text(encoding="utf-8").splitlines() if satir.strip()]
    if not satirlar:
        return np.zeros((0, 5))
    for numara, parcalar in enumerate(satirlar, 1):
        if len(parcalar) != 5:
            raise ValueError(f"{yol}: {numara}. satır 5 alan içermeli (sinif x_merkez y_merkez genislik yukseklik)")
    degerler = np.array(satirlar, dtype=np.float64)
    yari = degerler[:, 3:5] / 2.0
    return np.concatenate([degerler[:, :1], degerler[:, 1:3] - yari, degerler[:, 1:3] + yari], axis=1)


def _goruntu_eslestir(gt_kutular: np.ndarray, tahminler: np.ndarray, iou_esigi: float) -> np.ndarray:
    """Tek görüntü ve tek sınıf için tespitlerin doğru (True) / yanlış (False) olduğunu döndürür.
    tahminler güvene göre azalan sırada olmalı. Her gerçek kutu en fazla bir tespitle eşleşir."""
    dogru = np.zeros(len(tahminler), dtype=bool)
    if len(gt_kutular) == 0 or len(tahminler) == 0:
        return dogru
    iou = iou_matrisi(tahminler[:, 1:5], gt_kutular)
    kullanildi = np.zeros(len(gt_kutular), dtype=bool)
    for tahmin_no in range(len(tahminler)):
        en_iyi_gt = -1
        en_iyi_iou = min(iou_esigi, 1.0 - 1e-10)
        for gt_no in range(len(gt_kutular)):
            if kullanildi[gt_no] or iou[tahmin_no, gt_no] < en_iyi_iou:
                continue
            en_iyi_iou = iou[tahmin_no, gt_no]
            en_iyi_gt = gt_no
        if en_iyi_gt >= 0:
            kullanildi[en_iyi_gt] = True
            dogru[tahmin_no] = True
    return dogru


def _sirala_kirp(tahminler: np.ndarray, en_cok: int) -> np.ndarray:
    sira = np.argsort(-tahminler[:, 0], kind="mergesort")[:en_cok]
    return tahminler[sira]


def _sinif_ap(gt_listesi: list, tahmin_listesi: list, iou_esigi: float, en_cok: int) -> float | None:
    """Tek sınıf, tek IoU eşiği için AP. Bu sınıfta hiç gerçek kutu yoksa None.
    gt_listesi[i]: (G, 4) | tahmin_listesi[i]: (M, 5) [guven, x1, y1, x2, y2]"""
    gt_sayisi = sum(len(kutular) for kutular in gt_listesi)
    if gt_sayisi == 0:
        return None
    guvenler, dogrular = [], []
    for gt_kutular, tahminler in zip(gt_listesi, tahmin_listesi):
        if len(tahminler) == 0:
            continue
        tahminler = _sirala_kirp(tahminler, en_cok)
        guvenler.append(tahminler[:, 0])
        dogrular.append(_goruntu_eslestir(gt_kutular, tahminler, iou_esigi))
    if not guvenler:
        return 0.0
    guvenler = np.concatenate(guvenler)
    dogrular = np.concatenate(dogrular)[np.argsort(-guvenler, kind="mergesort")]
    dogru_say = np.cumsum(dogrular)
    yanlis_say = np.cumsum(~dogrular)
    anma = dogru_say / gt_sayisi
    kesinlik = dogru_say / (dogru_say + yanlis_say + np.spacing(1))
    kesinlik = np.maximum.accumulate(kesinlik[::-1])[::-1]  # kesinlik zarfı
    sirali = np.searchsorted(anma, ANMA_NOKTALARI, side="left")
    ornekler = np.where(sirali < len(kesinlik), kesinlik[np.minimum(sirali, len(kesinlik) - 1)], 0.0)
    return float(ornekler.mean())


def tespit_metrikleri(gt_listesi: list, tahmin_listesi: list, sinif_sayisi: int,
                      en_cok_tespit: int = EN_COK_TESPIT) -> dict:
    """mAP@0.5 ve mAP@0.5:0.95. Yalnızca test setinde gerçek kutusu olan sınıflar ortalamaya girer."""
    if len(gt_listesi) != len(tahmin_listesi):
        raise ValueError("gt_listesi ve tahmin_listesi aynı uzunlukta olmalı")
    sinif_ap = np.full((len(IOU_ESIKLERI), sinif_sayisi), np.nan)
    for sinif in range(sinif_sayisi):
        gt_sinif = [gt[gt[:, 0] == sinif, 1:5] for gt in gt_listesi]
        tahmin_sinif = [tahmin[tahmin[:, 0] == sinif, 1:6] for tahmin in tahmin_listesi]
        for sira, esik in enumerate(IOU_ESIKLERI):
            ap = _sinif_ap(gt_sinif, tahmin_sinif, float(esik), en_cok_tespit)
            if ap is not None:
                sinif_ap[sira, sinif] = ap
    if np.all(np.isnan(sinif_ap)):
        raise ValueError("test setinde hiç gerçek kutu yok; mAP hesaplanamaz")
    esik_basina = np.nanmean(sinif_ap, axis=1)
    return {"mAP@0.5": float(esik_basina[0]), "mAP@0.5:0.95": float(esik_basina.mean()),
            "sinif_ap50": [None if np.isnan(deger) else float(deger) for deger in sinif_ap[0]]}


def kesinlik_anma(gt_listesi: list, tahmin_listesi: list, sinif_sayisi: int,
                  guven_esigi: float = 0.25, iou_esigi: float = 0.5) -> dict:
    """Belirli güven eşiğinde (tüm sınıflar birlikte) kesinlik, anma ve sayılar."""
    dogru_pozitif = yanlis_pozitif = gt_toplam = 0
    for gt, tahmin in zip(gt_listesi, tahmin_listesi):
        gt_toplam += len(gt)
        for sinif in range(sinif_sayisi):
            gt_kutular = gt[gt[:, 0] == sinif, 1:5]
            tahminler = tahmin[(tahmin[:, 0] == sinif) & (tahmin[:, 1] >= guven_esigi)][:, 1:6]
            if len(tahminler) == 0:
                continue
            tahminler = _sirala_kirp(tahminler, EN_COK_TESPIT)
            dogru = _goruntu_eslestir(gt_kutular, tahminler, iou_esigi)
            dogru_pozitif += int(dogru.sum())
            yanlis_pozitif += int((~dogru).sum())
    tespit_toplam = dogru_pozitif + yanlis_pozitif
    return {"precision": dogru_pozitif / tespit_toplam if tespit_toplam else 0.0,
            "recall": dogru_pozitif / gt_toplam if gt_toplam else 0.0,
            "dogru_pozitif": dogru_pozitif, "yanlis_pozitif": yanlis_pozitif,
            "kacirilan": gt_toplam - dogru_pozitif}
