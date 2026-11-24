"""Kart üzerinde çıkarım katmanı (T3 Gemstone O1, TIDL hızlandırıcısı).

degerlendir.py yalnızca bu arayüzü bilir; modele özgü kısımlar (ön işleme, TIDL oturumu, son işleme)
burada toplanır. Model eklendiğinde yalnızca bu dosya doldurulur.

Arayüz
  yukle(goruntu_yolu) -> girdi          diskten okuma; süre ölçümüne GİRMEZ
  tespit_et(girdi)    -> (M, 6) dizi    [sinif, guven, x1, y1, x2, y2]; kutular 0-1 aralığında (görüntü
                                        genişlik/yüksekliğine bölünmüş). Ön ve son işleme (letterbox, kutu
                                        çözümü, NMS) süre ölçümüne GİRER: ölçülen gecikme uçtan uca değerdir.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


class Tespitci:
    def yukle(self, goruntu_yolu: Path):
        raise NotImplementedError

    def tespit_et(self, girdi) -> np.ndarray:
        raise NotImplementedError


def tespitci_olustur(model_dizini: Path, sinif_sayisi: int) -> Tespitci:
    # YAPILACAK (model eklenince):
    #  1. model_dizini altındaki derlenmiş TIDL çıktısını (artifacts) ve model.onnx'i bul
    #  2. onnxruntime oturumunu TIDLExecutionProvider + CPUExecutionProvider ile aç
    #  3. yukle / tespit_et'i uygula; hızlandırıcıda ve CPU'da çalışan katmanları README'ye yaz
    raise NotImplementedError(
        "Model henüz eklenmedi: src/cikarim.py içindeki tespitci_olustur doldurulmalı "
        "(model/ klasörüne model dosyaları ya da model/indir.txt konduktan sonra)."
    )
