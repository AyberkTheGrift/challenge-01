#!/usr/bin/env python3
"""T3 Gemstone Challenge değerlendirme betiği.

takimlar/ altındaki her takım klasörünü sırayla kurar, takımın degerlendir.sh betiğini
çalıştırır ve sonuçları bir çıktı klasörüne kaydeder. Kullanım ve sonuc.json biçimi için
olcum/README.md dosyasına bakın.

Yalnızca Python standart kütüphanesini kullanır (Python 3.10+).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_KOKU = Path(__file__).resolve().parent.parent
ZORUNLU_DOSYALAR = ("degerlendir.sh", "test-seti")
IZINLI_MODEL_SUNUCULARI = ("huggingface.co", "kaggle.com")
REFERANS_EDGEAI_SURUMU = "11.0"
REFERANS_UBUNTU_SURUMU = "22.04"
EDGEAI_ORTAM_DOSYASI = Path("/opt/t3-edgeai-env")
# Sürümleri kaydedilen paketler; ilk ikisinden biri Edge AI paketinin sürümünü verir.
EDGEAI_PAKETLERI = ("t3-gem-o1-edgeai", "t3-edgeai-dev", "arm-tidl-j722s", "t3-onnxruntime")

BASARILI = "basarili"
EKSIK_DOSYA = "eksik_dosya"
KURULUM_HATASI = "kurulum_hatasi"
CALISTIRMA_HATASI = "calistirma_hatasi"
ZAMAN_ASIMI = "zaman_asimi"
SONUC_GECERSIZ = "sonuc_gecersiz"
OLCUM_HATASI = "olcum_hatasi"

ISTEGE_BAGLI_SAYILAR = ("fps", "gecikme_ort_ms", "gecikme_p95_ms", "ornek_sayisi")
CSV_ALANLARI = (
    "takim", "durum", "metrik_adi", "metrik_degeri", *ISTEGE_BAGLI_SAYILAR, "ek_metrikler",
    "kurulum_sn", "calistirma_sn", "commit", "commit_disi_degisiklik", "hata",
)


class TakimHatasi(Exception):
    """Bir takımın değerlendirmesini durduran, nedeni bilinen hata."""

    def __init__(self, durum: str, mesaj: str):
        super().__init__(mesaj)
        self.durum = durum
        self.mesaj = mesaj


# --------------------------------------------------------------------------- yardımcılar


def simdi() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def satirlari_oku(yol: Path) -> list[str]:
    """Boş ve # ile başlayan satırları atlayarak dosyanın satırlarını döndürür."""
    if not yol.is_file():
        return []
    satirlar = []
    for satir in yol.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if satir and not satir.startswith("#"):
            satirlar.append(satir)
    return satirlar


def git(*argumanlar: str, dizin: Path) -> str | None:
    try:
        sonuc = subprocess.run(["git", *argumanlar], cwd=dizin, capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return sonuc.stdout.strip() if sonuc.returncode == 0 else None


def dpkg_surumu(paket: str) -> str | None:
    """Paket kuruluysa sürümünü, değilse None döndürür."""
    try:
        sonuc = subprocess.run(
            ["dpkg-query", "-W", "-f=${Status}|${Version}", paket], capture_output=True, text=True
        )
    except FileNotFoundError:
        return None
    if sonuc.returncode != 0:
        return None
    durum, _, surum = sonuc.stdout.partition("|")
    return surum if durum.split()[-1:] == ["installed"] else None


def isletim_sistemi() -> str:
    try:
        for satir in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if satir.startswith("PRETTY_NAME="):
                return satir.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.platform()


def sayi_mi(deger: object) -> bool:
    return isinstance(deger, (int, float)) and not isinstance(deger, bool) and math.isfinite(deger)


def bos_degilse(deger: object) -> object:
    return "" if deger is None else deger


# --------------------------------------------------------------------------- süreç yönetimi


def internetsiz_on_ek() -> list[str]:
    """degerlendir.sh'ı ağ bağlantısı olmayan (yalnızca loopback açık) bir ağ ad alanında çalıştırır.

    Root olarak yalnızca ağ ad alanı açılır; böylece süreç cihazlara (hızlandırıcı, kamera)
    root yetkileriyle erişmeye devam eder. Root olmayan kullanıcıda ağ ad alanı için bir
    kullanıcı ad alanı da gerekir.
    """
    ad_alani = ["--net"] if os.geteuid() == 0 else ["--user", "--map-root-user", "--net"]
    return ["unshare", *ad_alani, "sh", "-c", 'ip link set lo up && exec "$@"', "sh"]


def surec_grubunu_durdur(surec: subprocess.Popen, bekleme: float = 10.0) -> None:
    """Sürecin grubundaki tüm süreçleri (arka planda kalanlar dahil) durdurur."""
    for sinyal in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(surec.pid, sinyal)
        except ProcessLookupError:
            break
        son = time.monotonic() + bekleme
        while time.monotonic() < son:
            surec.poll()
            try:
                os.killpg(surec.pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.2)
    surec.poll()


def komut_calistir(
    komut: list, dizin: Path, ortam: dict, log, zaman_asimi: int
) -> tuple[int | None, float]:
    """Komutu kendi süreç grubunda çalıştırır; çıktısını log'a yazar.

    (çıkış kodu, süre) döndürür; zaman aşımında çıkış kodu None olur. Komut bittikten sonra
    arka planda bıraktığı süreçler de durdurulur, böylece sonraki takımın ölçümünü etkilemez.
    """
    komut = [str(parca) for parca in komut]
    log.write(f"\n$ {shlex.join(komut)}\n")
    log.flush()
    baslangic = time.monotonic()
    surec = subprocess.Popen(
        komut, cwd=dizin, env=ortam, stdin=subprocess.DEVNULL,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    try:
        kod = surec.wait(timeout=zaman_asimi)
    except subprocess.TimeoutExpired:
        kod = None
    finally:
        sure = time.monotonic() - baslangic
        surec_grubunu_durdur(surec)
    if kod is None:
        log.write(f"\n!! {zaman_asimi} sn içinde bitmedi, durduruldu\n")
    return kod, sure


# --------------------------------------------------------------------------- kurulum adımları


def apt_paketlerini_hazirla(calisma: Path, ortam: dict, log, apt_kur: bool, zaman_asimi: int) -> None:
    eksikler = []
    for satir in satirlari_oku(calisma / "apt.txt"):
        ad, _, surum = satir.partition("=")
        kurulu = dpkg_surumu(ad)
        if kurulu is None or (surum and kurulu != surum):
            eksikler.append(satir)
            log.write(f"apt: {satir} gerekli, kurulu sürüm: {kurulu or 'yok'}\n")
    if not eksikler:
        return
    if not apt_kur:
        raise TakimHatasi(
            KURULUM_HATASI,
            "apt.txt'deki paketler kurulu değil: " + ", ".join(eksikler) + " (kurmak için --apt-kur)",
        )
    komut = ["sudo", "-n", "env", "DEBIAN_FRONTEND=noninteractive",
             "apt-get", "install", "-y", "--no-install-recommends", *eksikler]
    kod, _ = komut_calistir(komut, calisma, ortam, log, zaman_asimi)
    if kod != 0:
        raise TakimHatasi(KURULUM_HATASI, "apt.txt'deki paketler kurulamadı (kurulum.log)")


def sanal_ortami_kur(calisma: Path, sanal_ortam: Path, ortam: dict, log, zaman_asimi: int) -> None:
    """Referans ortamdaki paketleri gören, takıma özel bir sanal ortam kurar.

    Takımın requirements.txt'de istediği paketler yalnızca bu ortama kurulur; referans
    ortamdaki paketlerle aynı sürümdekiler yeniden kurulmaz. Referans ortamda python3-venv
    (ensurepip) bulunmadığından ortam pip'siz açılır; paketler sistemdeki pip ile, sanal
    ortamın Python'u üzerinden kurulur.
    """
    komut = [sys.executable, "-m", "venv", "--system-site-packages", "--without-pip", sanal_ortam]
    kod, _ = komut_calistir(komut, calisma, ortam, log, zaman_asimi)
    if kod != 0:
        raise TakimHatasi(OLCUM_HATASI, "Python sanal ortamı oluşturulamadı (kurulum.log)")
    if not satirlari_oku(calisma / "requirements.txt"):
        return
    komut = [sanal_ortam / "bin" / "python", "-m", "pip", "install",
             "--disable-pip-version-check", "--no-input", "-r", "requirements.txt"]
    kod, _ = komut_calistir(komut, calisma, ortam, log, zaman_asimi)
    if kod is None:
        raise TakimHatasi(KURULUM_HATASI, "requirements.txt kurulumu zaman aşımına uğradı")
    if kod != 0:
        raise TakimHatasi(KURULUM_HATASI, "requirements.txt kurulamadı (kurulum.log)")


def modelleri_indir(calisma: Path, log) -> None:
    """model/indir.txt'deki dosyaları indirir ve SHA256 özetlerini doğrular."""
    model_dizini = calisma / "model"
    satirlar = satirlari_oku(model_dizini / "indir.txt")
    if satirlar and not model_dizini.resolve().is_relative_to(calisma.resolve()):
        raise TakimHatasi(KURULUM_HATASI, "model/ klasörü takım klasörünün dışını gösteriyor")
    for satir in satirlar:
        parcalar = satir.split()
        if len(parcalar) != 3:
            raise TakimHatasi(KURULUM_HATASI, f"indir.txt satırı üç alan içermeli: {satir}")
        ad, adres, beklenen = parcalar
        if Path(ad).name != ad or ad in (".", ".."):
            raise TakimHatasi(KURULUM_HATASI, f"indir.txt: geçersiz dosya adı: {ad}")
        url = urllib.parse.urlparse(adres)
        sunucu = (url.hostname or "").lower()
        if url.scheme != "https" or not any(
            sunucu == izinli or sunucu.endswith("." + izinli) for izinli in IZINLI_MODEL_SUNUCULARI
        ):
            raise TakimHatasi(
                KURULUM_HATASI,
                f"indir.txt: {ad} yalnızca HuggingFace ya da Kaggle'dan https ile indirilebilir "
                f"(şartname md. 4): {adres}",
            )

        hedef = model_dizini / ad
        if hedef.is_symlink() or hedef.exists():
            hedef.unlink()
        log.write(f"\nindiriliyor: {ad} <- {adres}\n")
        log.flush()
        ozet = hashlib.sha256()
        istek = urllib.request.Request(adres, headers={"User-Agent": "t3gc-olcum"})
        try:
            with urllib.request.urlopen(istek, timeout=60) as yanit, open(hedef, "wb") as dosya:
                while True:
                    parca = yanit.read(1 << 20)
                    if not parca:
                        break
                    ozet.update(parca)
                    dosya.write(parca)
        except OSError as hata:
            raise TakimHatasi(KURULUM_HATASI, f"indir.txt: {ad} indirilemedi: {hata}") from None
        if ozet.hexdigest() != beklenen.lower():
            raise TakimHatasi(
                KURULUM_HATASI,
                f"indir.txt: {ad} SHA256 özeti uyuşmuyor (beklenen {beklenen}, inen {ozet.hexdigest()})",
            )
        log.write(f"tamam: {ad} sha256={ozet.hexdigest()}\n")


def sonucu_dogrula(yol: Path) -> dict:
    if not yol.is_file():
        raise TakimHatasi(SONUC_GECERSIZ, "degerlendir.sh $CIKTI_DIZINI/sonuc.json dosyasını yazmadı")
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as hata:
        raise TakimHatasi(SONUC_GECERSIZ, f"sonuc.json okunamadı: {hata}") from None
    if not isinstance(veri, dict):
        raise TakimHatasi(SONUC_GECERSIZ, "sonuc.json bir JSON nesnesi olmalı")

    hatalar = []
    if not isinstance(veri.get("metrik_adi"), str) or not veri["metrik_adi"].strip():
        hatalar.append("metrik_adi boş olmayan bir metin olmalı")
    if not sayi_mi(veri.get("metrik_degeri")):
        hatalar.append("metrik_degeri bir sayı olmalı")
    for alan in ISTEGE_BAGLI_SAYILAR:
        if veri.get(alan) is not None and not sayi_mi(veri[alan]):
            hatalar.append(f"{alan} bir sayı olmalı")
    ek = veri.get("ek_metrikler")
    if ek is not None and not (
        isinstance(ek, dict) and all(isinstance(ad, str) and sayi_mi(deger) for ad, deger in ek.items())
    ):
        hatalar.append("ek_metrikler, metrik adından sayıya bir eşleme olmalı")
    if hatalar:
        raise TakimHatasi(SONUC_GECERSIZ, "; ".join(hatalar))

    alanlar = ("metrik_adi", "metrik_degeri", *ISTEGE_BAGLI_SAYILAR, "ek_metrikler")
    return {alan: veri[alan] for alan in alanlar if veri.get(alan) is not None}


# --------------------------------------------------------------------------- takım değerlendirmesi


def takim_ortami(sanal_ortam: Path, calisma: Path, cikti_dizini: Path) -> dict:
    ortam = os.environ.copy()
    ortam.pop("PYTHONHOME", None)
    ortam["VIRTUAL_ENV"] = str(sanal_ortam)
    ortam["PATH"] = f"{sanal_ortam / 'bin'}{os.pathsep}{ortam.get('PATH', '')}"
    ortam["TAKIM_DIZINI"] = str(calisma)
    ortam["TEST_SETI"] = str(calisma / "test-seti")
    ortam["CIKTI_DIZINI"] = str(cikti_dizini)
    return ortam


def takimi_degerlendir(takim_dizini: Path, cikti_kok: Path, ayarlar: argparse.Namespace) -> dict:
    ad = takim_dizini.name
    takim_cikti = cikti_kok / ad
    shutil.rmtree(takim_cikti, ignore_errors=True)
    cikti_dizini = takim_cikti / "cikti"
    cikti_dizini.mkdir(parents=True)

    degisiklikler = git("status", "--porcelain", "--untracked-files=all", "--", ".", dizin=takim_dizini)
    sonuc = {
        "takim": ad,
        "durum": None,
        "hata": None,
        "commit": git("log", "-1", "--format=%H", "--", ".", dizin=takim_dizini) or None,
        "commit_disi_degisiklik": None if degisiklikler is None else bool(degisiklikler),
        "baslangic": simdi(),
        "kurulum_sn": None,
        "calistirma_sn": None,
        "sonuc": None,
    }
    is_dizini = cikti_kok / ".calisma" / ad
    calisma = is_dizini / "takim"
    sanal_ortam = is_dizini / "venv"
    try:
        eksikler = [dosya for dosya in ZORUNLU_DOSYALAR if not (takim_dizini / dosya).exists()]
        if eksikler:
            raise TakimHatasi(EKSIK_DOSYA, "eksik: " + ", ".join(eksikler))

        shutil.rmtree(is_dizini, ignore_errors=True)
        shutil.copytree(takim_dizini, calisma, symlinks=True)
        ortam = takim_ortami(sanal_ortam, calisma, cikti_dizini)

        with open(takim_cikti / "kurulum.log", "a", encoding="utf-8") as log:
            baslangic = time.monotonic()
            try:
                apt_paketlerini_hazirla(calisma, ortam, log, ayarlar.apt_kur, ayarlar.kurulum_zaman_asimi)
                sanal_ortami_kur(calisma, sanal_ortam, ortam, log, ayarlar.kurulum_zaman_asimi)
                modelleri_indir(calisma, log)
                if (calisma / "kurulum.sh").is_file():
                    kod, _ = komut_calistir(["bash", "kurulum.sh"], calisma, ortam, log,
                                            ayarlar.kurulum_zaman_asimi)
                    if kod is None:
                        raise TakimHatasi(KURULUM_HATASI, "kurulum.sh zaman aşımına uğradı")
                    if kod != 0:
                        raise TakimHatasi(KURULUM_HATASI, f"kurulum.sh çıkış kodu {kod} (kurulum.log)")
            finally:
                sonuc["kurulum_sn"] = round(time.monotonic() - baslangic, 2)

        komut = ["bash", "degerlendir.sh"]
        if not ayarlar.internet_acik:
            komut = internetsiz_on_ek() + komut
        with open(takim_cikti / "calistirma.log", "a", encoding="utf-8") as log:
            kod, sure = komut_calistir(komut, calisma, ortam, log, ayarlar.zaman_asimi)
        sonuc["calistirma_sn"] = round(sure, 2)
        if kod is None:
            raise TakimHatasi(ZAMAN_ASIMI, f"degerlendir.sh {ayarlar.zaman_asimi} sn içinde bitmedi")
        if kod != 0:
            raise TakimHatasi(CALISTIRMA_HATASI, f"degerlendir.sh çıkış kodu {kod} (calistirma.log)")

        sonuc["sonuc"] = sonucu_dogrula(cikti_dizini / "sonuc.json")
        sonuc["durum"] = BASARILI
    except TakimHatasi as hata:
        sonuc["durum"], sonuc["hata"] = hata.durum, hata.mesaj
    except Exception as hata:  # Beklenmeyen bir hata diğer takımların değerlendirmesini durdurmasın.
        sonuc["durum"], sonuc["hata"] = OLCUM_HATASI, f"{type(hata).__name__}: {hata}"
    finally:
        if not ayarlar.sakla:
            shutil.rmtree(is_dizini, ignore_errors=True)
        sonuc["bitis"] = simdi()

    (takim_cikti / "durum.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return sonuc


# --------------------------------------------------------------------------- çıktılar


def edgeai_ortamini_yukle() -> bool:
    """/opt/t3-edgeai-env'deki ortam değişkenlerini bu sürecin (ve takımların) ortamına ekler.

    Böylece değerlendirme, betiği çalıştıran kabukta dosyanın source edilip edilmediğine
    bağlı kalmaz.
    """
    if not EDGEAI_ORTAM_DOSYASI.is_file():
        return False
    sonuc = subprocess.run(
        ["bash", "-c", 'source "$1" >/dev/null 2>&1 && env -0', "bash", str(EDGEAI_ORTAM_DOSYASI)],
        capture_output=True,
    )
    if sonuc.returncode != 0:
        return False
    for kayit in sonuc.stdout.split(b"\0"):
        ad, esittir, deger = kayit.partition(b"=")
        if esittir and ad not in (b"PS1", b"_", b"SHLVL", b"PWD", b"OLDPWD"):
            os.environ[os.fsdecode(ad)] = os.fsdecode(deger)
    return True


def ortam_bilgisi(ayarlar: argparse.Namespace, edgeai_ortami: bool) -> dict:
    return {
        "baslangic": simdi(),
        "bitis": None,
        "makine": platform.node(),
        "mimari": platform.machine(),
        "cekirdek": platform.release(),
        "isletim_sistemi": isletim_sistemi(),
        "python": platform.python_version(),
        "root": os.geteuid() == 0,
        "edgeai_paketleri": {paket: dpkg_surumu(paket) for paket in EDGEAI_PAKETLERI},
        "edgeai_ortami": str(EDGEAI_ORTAM_DOSYASI) if edgeai_ortami else None,
        "olcum_commit": git("rev-parse", "HEAD", dizin=REPO_KOKU),
        "internetsiz": not ayarlar.internet_acik,
        "zaman_asimi_sn": ayarlar.zaman_asimi,
        "kurulum_zaman_asimi_sn": ayarlar.kurulum_zaman_asimi,
    }


def csv_satiri(takim: dict) -> dict:
    sonuc = takim.get("sonuc") or {}
    satir = {
        "takim": takim["takim"],
        "durum": takim["durum"],
        "metrik_adi": sonuc.get("metrik_adi", ""),
        "metrik_degeri": sonuc.get("metrik_degeri", ""),
        "ek_metrikler": json.dumps(sonuc["ek_metrikler"], ensure_ascii=False) if sonuc.get("ek_metrikler") else "",
        "kurulum_sn": bos_degilse(takim["kurulum_sn"]),
        "calistirma_sn": bos_degilse(takim["calistirma_sn"]),
        "commit": bos_degilse(takim["commit"]),
        "commit_disi_degisiklik": bos_degilse(takim["commit_disi_degisiklik"]),
        "hata": bos_degilse(takim["hata"]),
    }
    satir.update({alan: sonuc.get(alan, "") for alan in ISTEGE_BAGLI_SAYILAR})
    return satir


def ozeti_yaz(cikti_kok: Path, ortam: dict, takimlar: list[dict]) -> None:
    (cikti_kok / "ozet.json").write_text(
        json.dumps({"ortam": ortam, "takimlar": takimlar}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with open(cikti_kok / "ozet.csv", "w", newline="", encoding="utf-8") as dosya:
        yazici = csv.DictWriter(dosya, fieldnames=CSV_ALANLARI)
        yazici.writeheader()
        for takim in takimlar:
            yazici.writerow(csv_satiri(takim))


def kisa_sonuc(takim: dict) -> str:
    if takim["durum"] == BASARILI:
        sonuc = takim["sonuc"]
        return f"{sonuc['metrik_adi']} = {sonuc['metrik_degeri']}"
    return takim["hata"] or ""


# --------------------------------------------------------------------------- ana akış


def on_kontrol(ayarlar: argparse.Namespace) -> list[str]:
    hatalar = []
    if not ayarlar.takimlar_dizini.is_dir():
        hatalar.append(f"takımlar klasörü bulunamadı: {ayarlar.takimlar_dizini}")
    if shutil.which("bash") is None:
        hatalar.append("bash bulunamadı")
    if importlib.util.find_spec("venv") is None:
        hatalar.append("Python venv modülü bulunamadı")
    if not ayarlar.internet_acik:
        try:
            deneme = subprocess.run([*internetsiz_on_ek(), "true"], capture_output=True, text=True, timeout=30)
            neden = deneme.stderr.strip() if deneme.returncode != 0 else None
        except (OSError, subprocess.TimeoutExpired) as hata:
            neden = str(hata)
        if neden is not None:
            hatalar.append(
                "degerlendir.sh internetsiz çalıştırılamıyor (unshare ve ip gerekli; root olmayan "
                "kullanıcıda kullanıcı ad alanlarına izin verilmeli). Root olarak çalıştırın ya da ağ "
                f"kısıtlaması olmadan çalıştırmak için --internet-acik verin. Ayrıntı: {neden}"
            )
    return hatalar


def ortam_uyarilari(ortam: dict) -> list[str]:
    uyarilar = []
    paketler = ortam["edgeai_paketleri"]
    edgeai = paketler["t3-gem-o1-edgeai"] or paketler["t3-edgeai-dev"]
    if edgeai is None or not edgeai.startswith(REFERANS_EDGEAI_SURUMU):
        uyarilar.append(f"Edge AI paketi sürümü {edgeai or 'bulunamadı'}; referans ortam {REFERANS_EDGEAI_SURUMU}")
    if REFERANS_UBUNTU_SURUMU not in ortam["isletim_sistemi"]:
        uyarilar.append(f"işletim sistemi {ortam['isletim_sistemi']}; referans ortam Ubuntu {REFERANS_UBUNTU_SURUMU}")
    if not ortam["edgeai_ortami"]:
        uyarilar.append(f"{EDGEAI_ORTAM_DOSYASI} yüklenemedi; Edge AI ortam değişkenleri tanımlı olmayabilir")
    if not ortam["root"]:
        uyarilar.append("betik root olarak çalışmıyor; TIDL hızlandırıcısı root yetkisi ister (sudo ile çalıştırın)")
    if importlib.util.find_spec("pip") is None:
        uyarilar.append("pip bulunamadı; requirements.txt içeren takımlar kurulamaz (sudo apt install python3-pip)")
    return uyarilar


def arguman_al() -> argparse.Namespace:
    ayristirici = argparse.ArgumentParser(
        description="takimlar/ altındaki her takımı kurar, degerlendir.sh'ı çalıştırır ve sonuçları kaydeder."
    )
    ayristirici.add_argument("--takim", action="append", metavar="AD",
                             help="yalnızca bu takımı çalıştır (birden çok kez verilebilir)")
    ayristirici.add_argument("--takimlar-dizini", type=Path, default=REPO_KOKU / "takimlar", metavar="DIZIN",
                             help="takım klasörlerinin bulunduğu klasör (varsayılan: takimlar/)")
    ayristirici.add_argument("--cikti", type=Path, metavar="DIZIN",
                             help="sonuçların yazılacağı klasör (varsayılan: sonuclar/<tarih-saat>/)")
    ayristirici.add_argument("--zaman-asimi", type=int, default=1800, metavar="SN",
                             help="degerlendir.sh için süre sınırı (varsayılan: 1800)")
    ayristirici.add_argument("--kurulum-zaman-asimi", type=int, default=3600, metavar="SN",
                             help="her kurulum adımı için süre sınırı (varsayılan: 3600)")
    ayristirici.add_argument("--apt-kur", action="store_true",
                             help="apt.txt'deki eksik paketleri sudo apt-get ile kur")
    ayristirici.add_argument("--internet-acik", action="store_true",
                             help="degerlendir.sh'ı internet bağlantısıyla çalıştır")
    ayristirici.add_argument("--sakla", action="store_true",
                             help="takımların çalışma kopyalarını ve sanal ortamlarını silme")
    return ayristirici.parse_args()


def main() -> int:
    ayarlar = arguman_al()
    ayarlar.takimlar_dizini = ayarlar.takimlar_dizini.resolve()
    edgeai_ortami = edgeai_ortamini_yukle()

    hatalar = on_kontrol(ayarlar)
    if hatalar:
        for hata in hatalar:
            print(f"HATA: {hata}", file=sys.stderr)
        return 2

    takimlar = sorted(
        dizin for dizin in ayarlar.takimlar_dizini.iterdir()
        if dizin.is_dir() and not dizin.name.startswith((".", "_"))
    )
    if ayarlar.takim:
        bilinmeyen = sorted(set(ayarlar.takim) - {dizin.name for dizin in takimlar})
        if bilinmeyen:
            print(f"HATA: takım bulunamadı: {', '.join(bilinmeyen)}", file=sys.stderr)
            return 2
        takimlar = [dizin for dizin in takimlar if dizin.name in ayarlar.takim]
    if not takimlar:
        print(f"HATA: {ayarlar.takimlar_dizini} altında takım klasörü yok", file=sys.stderr)
        return 2

    zaman = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    cikti_kok = (ayarlar.cikti or REPO_KOKU / "sonuclar" / zaman).resolve()
    cikti_kok.mkdir(parents=True, exist_ok=True)

    ortam = ortam_bilgisi(ayarlar, edgeai_ortami)
    for uyari in ortam_uyarilari(ortam):
        print(f"UYARI: {uyari}", file=sys.stderr)
    print(f"{len(takimlar)} takım değerlendirilecek; çıktı: {cikti_kok}", flush=True)

    sonuclar: list[dict] = []
    try:
        for sira, takim_dizini in enumerate(takimlar, 1):
            print(f"[{sira}/{len(takimlar)}] {takim_dizini.name} ...", flush=True)
            sonuc = takimi_degerlendir(takim_dizini, cikti_kok, ayarlar)
            sonuclar.append(sonuc)
            ozeti_yaz(cikti_kok, ortam, sonuclar)
            print(f"      {sonuc['durum']}: {kisa_sonuc(sonuc)}", flush=True)
    except KeyboardInterrupt:
        print("\nDurduruldu; o ana kadarki sonuçlar kaydedildi.", file=sys.stderr)
        return 130
    finally:
        ortam["bitis"] = simdi()
        ozeti_yaz(cikti_kok, ortam, sonuclar)
        if not ayarlar.sakla:
            shutil.rmtree(cikti_kok / ".calisma", ignore_errors=True)

    genislik = max(len(takim["takim"]) for takim in sonuclar)
    print("\nÖzet:")
    for takim in sonuclar:
        print(f"  {takim['takim']:<{genislik}}  {takim['durum']:<18} {kisa_sonuc(takim)}")
    print(f"\nSonuçlar: {cikti_kok / 'ozet.csv'}")
    return 0 if all(takim["durum"] == BASARILI for takim in sonuclar) else 1


if __name__ == "__main__":
    sys.exit(main())
