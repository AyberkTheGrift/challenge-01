# takimlar/

Her takım projesini bu klasörün altında kendi adını taşıyan bir klasöre koyar: `takimlar/<takim-adi>/`. Klasör adında küçük harf, rakam ve tire kullanın (ör. `takimlar/ornek-takim/`).

Takım klasörü [`sablon/`](../sablon/) yapısını izler. [`olcum/calistir.py`](../olcum/) bu klasördeki her takımı sırayla kurar, takımın `degerlendir.sh` betiğini çalıştırır ve sonuçları kaydeder.

Takımlar yalnızca kendi klasörlerinde değişiklik yapar. Klasörlerin şablona uygunluğu her commit'te GitHub Actions'ta denetlenir; aynı denetimi `python3 olcum/kontrol.py --takim <takim-adi>` ile kendiniz de çalıştırabilirsiniz.
