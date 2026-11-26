# 🧾 Auto Renamer — Akıllı Fatura Yeniden Adlandırma

Karmaşık isimlerle indirilen **PDF** ve **HTML** faturalarınızı saniyeler içinde okuyup, içindeki bilgilerle düzenli bir formata dönüştüren Python aracı. ✨

```text
Faturayı Basan Şirket (ilk 2 kelime) - Fatura No - Fatura Tarihi.<uzantı>
```

---

## 🔄 Örnek (Before → After)

| ❌ Öncesi (Before) | ✅ Sonrası (After) |
| :--- | :--- |
| `scan_00492_final_v2.pdf` | `ÖRNEK TEKNOLOJİ - OTY2026000001042 - 12.03.2026.pdf` |
| `IMG_8821_fatura_kopya.pdf` | `HIZLI BULUT - GIB2026000987654 - 25.11.2026.pdf` |
| `indirilen_e_fatura (3).html` | `YILDIZ BULUT - YLD2026000012345 - 26.11.2026.html` |

---

## 🚀 Özellikler

- 📄 **PDF & HTML Desteği:** Hem `.pdf` hem de `.html` / `.htm` formatındaki faturaları okur.
- 🏢 **Kısa & Temiz Şirket Adı:** Şirket adı 2 kelimeden uzunsa otomatik olarak ilk 2 kelimeyi alır.
- 📅 **Okunaklı Tarih Formatı:** Tarihleri `GG.AA.YYYY` formatında yazar.
- 🛡️ **Güvenli İşlem:** Eksik bilgisi olan veya okunamayan (ör. taranmış/kopyalanamayan) dosyalara **hiçbir şey yapmaz**, terminalde *"İnsan müdahalesi gerekli"* uyarısı vererek hangi alanın çekilip hangisinin başarısız olduğunu bildirir.
- 🔁 **Çakışma Koruması:** Aynı isimde dosya varsa üzerine yazmaz, sonuna `(2)`, `(3)` ekler.

---

## ⚙️ Kurulum

```bash
pip3 install -r requirements.txt
```

---

## ▶️ Kullanım

Faturaların bulunduğu klasörde terminali açıp çalıştırmanız yeterli:

```bash
python3 rename_invoices.py
```

*(Önce değişiklikleri görmek isterseniz `--dry-run` ekleyebilirsiniz.)*
