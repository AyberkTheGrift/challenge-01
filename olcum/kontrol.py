#!/usr/bin/env python3
"""Takım klasörlerinin şablona (sablon/) ve şartnameye uygunluğunu denetler.

Her commit'te GitHub Actions'ta çalışır (.github/workflows/takim-kontrolu.yml); takımlar kendi
bilgisayarlarında da çalıştırabilir:

    python3 olcum/kontrol.py                       # tüm takımlar
    python3 olcum/kontrol.py --takim ornek-takim   # yalnızca bir takım

Hatalar çıkış kodunu 1 yapar; uyarılar yalnızca bildirilir. Modeli çalıştırmaz; bunu
olcum/calistir.py yapar. Yalnızca Python standart kütüphanesini kullanır (Python 3.10+).
"""

from __future__ import annotations

import argparse
import functools
import os
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from calistir import IZINLI_MODEL_SUNUCULARI, REPO_KOKU, ZORUNLU_DOSYALAR, satirlari_oku

SABLON = REPO_KOKU / "sablon"
TAKIM_ADI = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEST_DOSYA_ADI = re.compile(r"^[a-z0-9_-]+$")
PIP_SATIRI = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9._,-]+\])?==[^\s;=]+(?:\s*;.+)?$")
APT_SATIRI = re.compile(r"^[a-z0-9][a-z0-9.+-]+=\S+$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
MARKDOWN_BAGLANTISI = re.compile(r"!?\[[^\[\]]*\]\(([^)\s]*)[^)]*\)")
GIZLI_BILGILER = {
    "GitHub erişim belirteci": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})"),
    "HuggingFace erişim belirteci": re.compile(r"\bhf_[A-Za-z0-9]{30,}"),
    "AWS erişim anahtarı": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "API anahtarı": re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"),
    "Kaggle API anahtarı": re.compile(r'"key"\s*:\s*"[0-9a-f]{32}"'),
    "özel anahtar": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
}
SABLON_ACIKLAMASI = "README şablonu."
DOLDURULMAMIS_DEGERLENDIRME = "degerlendir.sh henüz doldurulmadı"
BUYUK_DOSYA = 50 * 1024 * 1024
TARANACAK_EN_BUYUK_DOSYA = 2 * 1024 * 1024
TEST_SETI_SINIRI = 500


@dataclass
class Bulgu:
    seviye: str  # "hata" ya da "uyari"
    dosya: str
    mesaj: str


class Denetim:
    """Bir takım klasörü için bulguları toplar."""

    def __init__(self, dizin: Path):
        self.dizin = dizin
        self.bulgular: list[Bulgu] = []

    def _ekle(self, seviye: str, yol: Path, mesaj: str) -> None:
        try:
            goreli = yol.resolve().relative_to(REPO_KOKU)
        except ValueError:
            goreli = yol
        self.bulgular.append(Bulgu(seviye, str(goreli), mesaj))

    def hata(self, yol: Path, mesaj: str) -> None:
        self._ekle("hata", yol, mesaj)

    def uyari(self, yol: Path, mesaj: str) -> None:
        self._ekle("uyari", yol, mesaj)

    @property
    def hata_sayisi(self) -> int:
        return sum(bulgu.seviye == "hata" for bulgu in self.bulgular)

    @property
    def uyari_sayisi(self) -> int:
        return sum(bulgu.seviye == "uyari" for bulgu in self.bulgular)


def kisalt(metin: str, uzunluk: int = 70) -> str:
    return metin if len(metin) <= uzunluk else metin[: uzunluk - 1] + "…"


def metin_dosyasi_mi(yol: Path) -> bool:
    try:
        with open(yol, "rb") as dosya:
            return b"\0" not in dosya.read(8192)
    except OSError:
        return False


def dosyalar(dizin: Path) -> list[Path]:
    return sorted(yol for yol in dizin.rglob("*") if yol.is_file() and not yol.is_symlink())


# --------------------------------------------------------------------------- şablondan okunanlar


def sablon_basliklari() -> list[str]:
    return re.findall(r"^## (.+?)\s*$", (SABLON / "README.md").read_text(encoding="utf-8"), re.M)


@functools.lru_cache(maxsize=None)
def sablon_yer_tutuculari() -> frozenset[str]:
    """Şablon README'de köşeli parantezli yer tutucu içeren satırlar (bağlantılar hariç)."""
    yer_tutucular = set()
    for satir in (SABLON / "README.md").read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if "[" in MARKDOWN_BAGLANTISI.sub("", satir):
            yer_tutucular.add(satir)
    return frozenset(yer_tutucular)


def lisans_govdesi(metin: str) -> list[str]:
    return [satir.strip() for satir in metin.splitlines() if satir.strip() and not satir.startswith("Copyright")]


# --------------------------------------------------------------------------- denetimler


def klasor_adini_denetle(d: Denetim) -> None:
    if not TAKIM_ADI.match(d.dizin.name):
        d.hata(d.dizin, "takım klasörünün adında yalnızca küçük harf, rakam ve tire kullanılmalı "
                        "(ör. ornek-takim)")


def zorunlu_dosyalari_denetle(d: Denetim) -> None:
    for ad in ("README.md", "LICENSE", *ZORUNLU_DOSYALAR, "model"):
        if not (d.dizin / ad).exists():
            d.hata(d.dizin / ad, f"{ad} bulunamadı (sablon/ yapısına bakın)")
    src = d.dizin / "src"
    if not src.is_dir() or not dosyalar(src):
        d.uyari(src, "src/ boş ya da yok; kart üzerinde çalışan uygulama ve çıkarım kodu burada olmalı")


def readme_denetle(d: Denetim) -> None:
    yol = d.dizin / "README.md"
    if not yol.is_file():
        return
    metin = yol.read_text(encoding="utf-8", errors="replace")
    basliklar = set(re.findall(r"^## (.+?)\s*$", metin, re.M))
    for baslik in sablon_basliklari():
        if baslik not in basliklar:
            d.hata(yol, f'"## {baslik}" başlığı yok; şablondaki başlıkları silmeyin')
    if SABLON_ACIKLAMASI in metin:
        d.uyari(yol, "şablonun başındaki açıklama (<!-- README şablonu. ... -->) silinmemiş")
    yer_tutucular = sablon_yer_tutuculari()
    for no, satir in enumerate(metin.splitlines(), 1):
        if satir.strip() in yer_tutucular:
            d.uyari(yol, f"{no}. satırdaki yer tutucu doldurulmamış: {kisalt(satir.strip())}")
    for hedef in MARKDOWN_BAGLANTISI.findall(metin):
        if hedef and not re.match(r"^(?:[a-z]+:|#)", hedef):
            if not (d.dizin / hedef.split("#")[0]).exists():
                d.uyari(yol, f"bağlantı verilen dosya yok: {hedef}")


def lisansi_denetle(d: Denetim) -> None:
    yol = d.dizin / "LICENSE"
    if not yol.is_file():
        return
    metin = yol.read_text(encoding="utf-8", errors="replace")
    if lisans_govdesi(metin) != lisans_govdesi((SABLON / "LICENSE").read_text(encoding="utf-8")):
        d.hata(yol, "lisans metni şablondakinden farklı; çalışmalar referans repodaki lisansa tabidir, "
                    "yalnızca Copyright satırı değiştirilebilir")
    elif "[takım adı]" in metin:
        d.uyari(yol, "Copyright satırındaki [takım adı] doldurulmamış")


def betikleri_denetle(d: Denetim) -> None:
    yol = d.dizin / "degerlendir.sh"
    if yol.is_file() and DOLDURULMAMIS_DEGERLENDIRME in yol.read_text(encoding="utf-8", errors="replace"):
        d.hata(yol, "degerlendir.sh şablondaki haliyle bırakılmış; modeli test-seti/ ile çalıştırıp "
                    "$CIKTI_DIZINI/sonuc.json yazmalı (olcum/README.md)")
    for ad in ("degerlendir.sh", "kurulum.sh"):
        yol = d.dizin / ad
        if not yol.is_file():
            continue
        sonuc = subprocess.run(["bash", "-n", str(yol)], capture_output=True, text=True)
        if sonuc.returncode != 0:
            d.hata(yol, f"bash sözdizimi hatası: {kisalt(sonuc.stderr.strip(), 200)}")


def bagimliliklari_denetle(d: Denetim) -> None:
    yol = d.dizin / "requirements.txt"
    for satir in satirlari_oku(yol):
        if not PIP_SATIRI.match(satir):
            d.hata(yol, f"sürüm == ile sabitlenmemiş ya da desteklenmeyen satır: {kisalt(satir)} "
                        "(ör. numpy==1.26.4)")
    yol = d.dizin / "apt.txt"
    for satir in satirlari_oku(yol):
        if not APT_SATIRI.match(satir):
            d.hata(yol, f"sürüm belirtilmemiş: {kisalt(satir)} (ör. zbar-tools=0.23.92-4build2)")


def modeli_denetle(d: Denetim) -> None:
    model = d.dizin / "model"
    if not model.is_dir():
        return
    indir = model / "indir.txt"
    model_dosyalari = [yol for yol in dosyalar(model) if yol.name not in ("README.md", "indir.txt", "indir.txt.ornek")]
    if not model_dosyalari and not indir.is_file():
        d.hata(model, "model dosyası yok; dosyaları model/ altına koyun ya da HuggingFace/Kaggle "
                      "bağlantılarını model/indir.txt'ye yazın")
    adlar = set()
    for satir in satirlari_oku(indir):
        parcalar = satir.split()
        if len(parcalar) != 3:
            d.hata(indir, f"satır üç alan içermeli (dosya adı, adres, SHA256): {kisalt(satir)}")
            continue
        ad, adres, ozet = parcalar
        if Path(ad).name != ad or ad in (".", ".."):
            d.hata(indir, f"geçersiz dosya adı: {ad}")
        if ad in adlar:
            d.hata(indir, f"aynı dosya adı birden çok kez yazılmış: {ad}")
        adlar.add(ad)
        url = urllib.parse.urlparse(adres)
        sunucu = (url.hostname or "").lower()
        if url.scheme != "https" or not any(
            sunucu == izinli or sunucu.endswith("." + izinli) for izinli in IZINLI_MODEL_SUNUCULARI
        ):
            d.hata(indir, f"{ad}: model dosyaları yalnızca HuggingFace ya da Kaggle'dan https ile "
                          f"indirilebilir (şartname md. 4): {kisalt(adres)}")
        if not SHA256.match(ozet):
            d.hata(indir, f"{ad}: SHA256 özeti 64 onaltılık karakter olmalı")
        elif set(ozet) == {"0"}:
            d.hata(indir, f"{ad}: SHA256 özeti örnekteki gibi sıfır bırakılmış")


def test_setini_denetle(d: Denetim) -> None:
    test_seti = d.dizin / "test-seti"
    if not test_seti.is_dir():
        return
    tum = [yol for yol in dosyalar(test_seti) if yol.name != "README.md"]
    if not tum:
        d.hata(test_seti, "test-seti/ boş; Jüri Heyeti'nin modeli test edeceği veri burada olmalı (şartname md. 5)")
        return

    ornek_klasoru = next((test_seti / ad for ad in ("goruntuler", "girdi", "ornekler") if (test_seti / ad).is_dir()), None)
    ornekler = dosyalar(ornek_klasoru) if ornek_klasoru else tum
    if len(ornekler) > TEST_SETI_SINIRI:
        d.uyari(test_seti, f"{len(ornekler)} örnek var; test setlerinin en fazla {TEST_SETI_SINIRI} örnek "
                           "içermesi önerilir")
    uygunsuz = [yol for yol in tum
                if yol.name not in ("siniflar.txt", "etiketler.csv") and not TEST_DOSYA_ADI.match(yol.stem)]
    if uygunsuz:
        d.uyari(test_seti, f"{len(uygunsuz)} dosyanın adında küçük harf, rakam, tire ve alt çizgi dışında "
                           f"karakter var (ör. {uygunsuz[0].relative_to(test_seti)})")

    for girdi_adi, eslesen_adi in (("goruntuler", "etiketler"), ("goruntuler", "maskeler"), ("girdi", "hedef")):
        girdi, eslesen = test_seti / girdi_adi, test_seti / eslesen_adi
        if girdi.is_dir() and eslesen.is_dir():
            eslesenler = {yol.stem for yol in dosyalar(eslesen)}
            eksik = [yol for yol in dosyalar(girdi) if yol.stem not in eslesenler]
            if eksik:
                d.uyari(eslesen, f"{len(eksik)} örneğin {eslesen_adi}/ altında karşılığı yok "
                                 f"(ör. {eksik[0].name})")

    siniflar_yolu = test_seti / "siniflar.txt"
    goruntuler = test_seti / "goruntuler"
    sinif_klasorleri = {yol.name for yol in goruntuler.iterdir() if yol.is_dir()} if goruntuler.is_dir() else set()
    if sinif_klasorleri and siniflar_yolu.is_file():
        siniflar = set(satirlari_oku(siniflar_yolu))
        fazla = sorted(sinif_klasorleri - siniflar)
        if fazla:
            d.uyari(goruntuler, f"siniflar.txt'de olmayan sınıf klasörleri: {', '.join(fazla[:5])}")


def dosyalari_tara(d: Denetim) -> None:
    for yol in dosyalar(d.dizin):
        boyut = yol.stat().st_size
        if boyut > BUYUK_DOSYA:
            d.uyari(yol, f"dosya {boyut // (1024 * 1024)} MB; GitHub 100 MB'tan büyük dosyaları kabul etmez, "
                         "büyük model dosyalarını HuggingFace/Kaggle'da barındırın")
        if boyut > TARANACAK_EN_BUYUK_DOSYA or not metin_dosyasi_mi(yol):
            continue
        metin = yol.read_text(encoding="utf-8", errors="replace")
        for tur, desen in GIZLI_BILGILER.items():
            if desen.search(metin):
                d.hata(yol, f"{tur} olabilecek bir değer var; repoda gizli bilgi paylaşılmamalı (şartname md. 8)")


DENETIMLER = (
    klasor_adini_denetle,
    zorunlu_dosyalari_denetle,
    readme_denetle,
    lisansi_denetle,
    betikleri_denetle,
    bagimliliklari_denetle,
    modeli_denetle,
    test_setini_denetle,
    dosyalari_tara,
)


def takimi_denetle(dizin: Path) -> Denetim:
    d = Denetim(dizin)
    for denetim in DENETIMLER:
        denetim(d)
    return d


# --------------------------------------------------------------------------- çıktı


def actions_ozelligi(metin: str) -> str:
    return metin.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A").replace(":", "%3A").replace(",", "%2C")


def actions_mesaji(metin: str) -> str:
    return metin.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def raporla(denetimler: list[Denetim], genel_uyarilar: list[str]) -> None:
    actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for uyari in genel_uyarilar:
        print(f"UYARI {uyari}")
        if actions:
            print(f"::warning title=Takım klasörü kontrolü::{actions_mesaji(uyari)}")
    for d in denetimler:
        durum = "uygun" if not d.bulgular else f"{d.hata_sayisi} hata, {d.uyari_sayisi} uyarı"
        print(f"\n{d.dizin.name}: {durum}")
        for bulgu in d.bulgular:
            print(f"  {'HATA ' if bulgu.seviye == 'hata' else 'UYARI'} {bulgu.dosya}: {bulgu.mesaj}")
            if actions:
                komut = "error" if bulgu.seviye == "hata" else "warning"
                print(f"::{komut} file={actions_ozelligi(bulgu.dosya)},"
                      f"title={actions_ozelligi(d.dizin.name)}::{actions_mesaji(bulgu.mesaj)}")

    ozet_dosyasi = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozet_dosyasi:
        satirlar = ["## Takım klasörü kontrolü", ""]
        satirlar += [f"> {uyari}" for uyari in genel_uyarilar]
        satirlar += ["", "| Takım | Durum | Hata | Uyarı |", "|---|---|---|---|"]
        for d in denetimler:
            durum = "❌" if d.hata_sayisi else ("⚠️" if d.uyari_sayisi else "✅")
            satirlar.append(f"| `{d.dizin.name}` | {durum} | {d.hata_sayisi} | {d.uyari_sayisi} |")
        for d in denetimler:
            if d.bulgular:
                satirlar += ["", f"### `{d.dizin.name}`", ""]
                satirlar += [f"- **{'Hata' if b.seviye == 'hata' else 'Uyarı'}** `{b.dosya}`: {b.mesaj}"
                             for b in d.bulgular]
        with open(ozet_dosyasi, "a", encoding="utf-8") as dosya:
            dosya.write("\n".join(satirlar) + "\n")


# --------------------------------------------------------------------------- ana akış


def degisen_takimlar(degisenler: list[str], takimlar_dizini: Path) -> tuple[set[str], list[str]]:
    """Değişen dosyalardan takım adlarını ve kapsamla ilgili uyarıları çıkarır."""
    try:
        onek = takimlar_dizini.resolve().relative_to(REPO_KOKU).as_posix() + "/"
    except ValueError:  # takımlar klasörü repo dışında (ör. denemelerde)
        onek = "takimlar/"
    takimlar, disarida = set(), []
    for yol in degisenler:
        if yol.startswith(onek) and "/" in yol[len(onek):]:
            takimlar.add(yol[len(onek):].split("/", 1)[0])
        else:
            disarida.append(yol)
    uyarilar = []
    gercek_takimlar = {ad for ad in takimlar if not ad.startswith((".", "_"))}
    if len(gercek_takimlar) > 1:
        uyarilar.append(f"Bu değişiklik birden çok takımın klasörüne dokunuyor: {', '.join(sorted(gercek_takimlar))}. "
                        "Takımlar yalnızca kendi klasörlerinde değişiklik yapar.")
    if gercek_takimlar and disarida:
        uyarilar.append(f"Bu değişiklik takım klasörü dışındaki dosyalara da dokunuyor "
                        f"(ör. {disarida[0]}). Takımlar yalnızca kendi klasörlerinde değişiklik yapar.")
    return gercek_takimlar, uyarilar


def arguman_al() -> argparse.Namespace:
    ayristirici = argparse.ArgumentParser(description="Takım klasörlerinin şablona uygunluğunu denetler.")
    ayristirici.add_argument("--takim", action="append", metavar="AD",
                             help="yalnızca bu takımı denetle (birden çok kez verilebilir)")
    ayristirici.add_argument("--degisenler", type=Path, metavar="DOSYA",
                             help="değişen dosyaların listesi (satır başına bir yol); yalnızca bunların "
                                  "dokunduğu takımlar denetlenir")
    ayristirici.add_argument("--takimlar-dizini", type=Path, default=REPO_KOKU / "takimlar", metavar="DIZIN",
                             help="takım klasörlerinin bulunduğu klasör (varsayılan: takimlar/)")
    return ayristirici.parse_args()


def main() -> int:
    ayarlar = arguman_al()
    takimlar_dizini = ayarlar.takimlar_dizini.resolve()
    if not takimlar_dizini.is_dir():
        print(f"HATA: takımlar klasörü bulunamadı: {takimlar_dizini}", file=sys.stderr)
        return 2
    takimlar = sorted(
        dizin for dizin in takimlar_dizini.iterdir()
        if dizin.is_dir() and not dizin.name.startswith((".", "_"))
    )

    genel_uyarilar: list[str] = []
    if ayarlar.takim:
        bilinmeyen = sorted(set(ayarlar.takim) - {dizin.name for dizin in takimlar})
        if bilinmeyen:
            print(f"HATA: takım bulunamadı: {', '.join(bilinmeyen)}", file=sys.stderr)
            return 2
        takimlar = [dizin for dizin in takimlar if dizin.name in ayarlar.takim]
    elif ayarlar.degisenler:
        degisenler = [satir.strip() for satir in ayarlar.degisenler.read_text(encoding="utf-8").splitlines() if satir.strip()]
        secilenler, genel_uyarilar = degisen_takimlar(degisenler, takimlar_dizini)
        takimlar = [dizin for dizin in takimlar if dizin.name in secilenler]
        if not takimlar:
            print("Bu değişiklik hiçbir takım klasörüne dokunmuyor; denetlenecek takım yok.")
            raporla([], genel_uyarilar)
            return 0

    if not takimlar:
        print(f"{takimlar_dizini} altında takım klasörü yok.")
        return 0

    denetimler = [takimi_denetle(dizin) for dizin in takimlar]
    raporla(denetimler, genel_uyarilar)
    hatali = [d.dizin.name for d in denetimler if d.hata_sayisi]
    print(f"\n{len(denetimler)} takım denetlendi; "
          + (f"hatalı: {', '.join(hatali)}" if hatali else "hepsi şablona uygun."))
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())
