# Fatura Yeniden Adlandırma Scripti

PDF formatındaki faturaları okuyarak içlerinden **Faturayı Basan Şirket**, **Fatura No** ve **Fatura Tarihi** bilgilerini çıkarır ve dosyaları şu formatta yeniden adlandırır:

```text
Faturayı Basan Şirket - Fatura No - Fatura Tarihi.pdf
```

## Kurulum

```bash
pip3 install -r requirements.txt
```

## Kullanım

1. **Önce önizleme yapın (önerilen):**
   ```bash
   python3 rename_invoices.py /faturalar/klasoru --dry-run
   ```

2. **Dosyaları yeniden adlandırın:**
   ```bash
   python3 rename_invoices.py /faturalar/klasoru
   ```

3. **Alt klasörlerle birlikte ve `GG.AA.YYYY` tarih formatıyla çalıştırma:**
   ```bash
   python3 rename_invoices.py /faturalar/klasoru -r --date-format "%d.%m.%Y"
   ```
