#!/usr/bin/env python3
"""
PDF faturaları okuyup içindeki şirket adı, fatura numarası ve fatura tarihini
çıkararak dosyaları 'Faturayı Basan Şirket - Fatura No - Fatura Tarihi.pdf'
formatında yeniden adlandırır.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:
    print(
        "Hata: 'pdfplumber' kütüphanesi kurulu değil.\n"
        "Kurmak için: pip3 install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


TURKISH_MONTHS = {
    "ocak": 1, "oca": 1,
    "şubat": 2, "subat": 2, "şub": 2, "sub": 2,
    "mart": 3, "mar": 3,
    "nisan": 4, "nis": 4,
    "mayıs": 5, "mayis": 5, "may": 5,
    "haziran": 6, "haz": 6,
    "temmuz": 7, "tem": 7,
    "ağustos": 8, "agustos": 8, "ağu": 8, "agu": 8,
    "eylül": 9, "eylul": 9, "eyl": 9,
    "ekim": 10, "eki": 10,
    "kasım": 11, "kasim": 11, "kas": 11,
    "aralık": 12, "aralik": 12, "ara": 12,
}

COMPANY_SUFFIX_RE = re.compile(
    r"\b("
    r"A\.?\s*Ş\.?|ANONİM\s+ŞİRKETİ|"
    r"LTD\.?\s*ŞTİ\.?|LİMİTED\s+ŞİRKETİ|"
    r"SAN\.?\s*(?:VE\s*)?TİC\.?|TİC\.?\s*LTD\.?|"
    r"KOLL\.?\s*ŞTİ\.?|KOM\.?\s*ŞTİ\.?|"
    r"ŞTİ\.?|INC\.?|LLC|LTD\.?|CORP\.?|GMBH"
    r")\b",
    re.IGNORECASE,
)

SKIP_COMPANY_LINE_RE = re.compile(
    r"^("
    r"e-?fatura|e-?arşiv(?:\s+fatura)?|fatura|irsaliye|"
    r"sayın|alıcı|müşteri|özelleştirme|senaryo|fatura\s+tipi|"
    r"vkn|tckn|vergi\s+dairesi|mersis|ticaret\s+sicil|"
    r"tel\b|telefon|fax|faks|web\b|www\.|http|e-?posta|mail|"
    r"adres|mah\.|cad\.|sok\.|no\s*:|ettn"
    r")",
    re.IGNORECASE,
)


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 2) -> str:
    """PDF'in ilk sayfalarından metin çıkarır."""
    texts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:max_pages]:
            page_text = page.extract_text(layout=True) or page.extract_text() or ""
            if page_text.strip():
                texts.append(page_text)
    return "\n".join(texts)


def extract_invoice_number(text: str) -> Optional[str]:
    """Metinden fatura numarasını bulur."""
    labeled_patterns = [
        # Standart 16 haneli GİB e-Fatura / e-Arşiv numarası (ör: ABC2026000001234)
        r"(?:Fatura\s*(?:No|Numaras[ıi])|Belge\s*No|Invoice\s*(?:No|Number))\s*[:\-]?\s*([A-Z0-9]{3}20\d{2}\d{9})",
        # Genel etiketli fatura numarası
        r"(?:Fatura\s*(?:No|Numaras[ıi])|Fatura\s*Seri\s*/\s*S[ıi]ra\s*No|Belge\s*No|Invoice\s*(?:No|Number))\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{3,24})",
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            # UUID (ETTN) veya sadece tarih yakalamamak için kontrol
            if not re.fullmatch(r"\d{2}[./-]\d{2}[./-]\d{4}", candidate):
                return candidate

    # Etiketsiz fallback: 16 haneli GİB formatı (3 alfanümerik + 20xx + 9 rakam)
    gib_match = re.search(r"\b([A-Z0-9]{3}20\d{2}\d{9})\b", text)
    if gib_match:
        return gib_match.group(1)

    return None


def _parse_date_string(raw: str) -> Optional[date]:
    """Farklı tarih formatlarını date nesnesine çevirir."""
    raw = raw.strip()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    # Türkçe ay isimli tarih: "25 Kasım 2026"
    m = re.match(r"^(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})$", raw)
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        month = TURKISH_MONTHS.get(month_name)
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                return None
    return None


def extract_invoice_date(text: str) -> Optional[date]:
    """Metinden fatura tarihini bulur."""
    date_part = r"(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4})"
    labeled_patterns = [
        rf"(?:Fatura\s*Tarihi|D[üu]zenleme\s*Tarihi|Belge\s*Tarihi|Invoice\s*Date)\s*[:\-]?\s*{date_part}",
        rf"\bTarih\s*[:\-]\s*{date_part}",
    ]
    for pattern in labeled_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            parsed = _parse_date_string(match.group(1))
            if parsed:
                return parsed

    # Fallback: metindeki ilk geçerli tarih
    for match in re.finditer(r"\b(\d{2}[./-]\d{2}[./-]20\d{2})\b", text):
        parsed = _parse_date_string(match.group(1))
        if parsed:
            return parsed

    return None


def extract_company_name(text: str) -> Optional[str]:
    """Faturayı basan (satıcı) şirket adını metnin üst kısmından çıkarır."""
    # Satıcı bilgisi genellikle "SAYIN" / "ALICI" bölümünden önce yer alır.
    top_section = re.split(r"\b(?:SAYIN|ALICI|MÜŞTERİ\s+BİLGİLERİ)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    lines = [re.sub(r"\s{2,}", " ", line).strip() for line in top_section.splitlines()]
    lines = [line for line in lines if len(line) >= 3]

    # 1. Öncelik: Etiketli unvan (örn. "Unvanı: ABC Teknoloji A.Ş.")
    for line in lines[:25]:
        m = re.search(
            r"(?:Sat[ıi]c[ıi]\s*(?:Unvan[ıi]|Ad[ıi])?|Firma\s*(?:Unvan[ıi]|Ad[ıi])|Unvan[ıi]?)\s*[:\-]\s*(.+)",
            line,
            re.IGNORECASE,
        )
        if m:
            candidate = _clean_company_candidate(m.group(1))
            if candidate:
                return candidate

    # 2. Öncelik: Şirket türü eki içeren satır (A.Ş., LTD. ŞTİ. vb.)
    for idx, line in enumerate(lines[:20]):
        if SKIP_COMPANY_LINE_RE.search(line):
            continue
        if COMPANY_SUFFIX_RE.search(line):
            candidate = _clean_company_candidate(line)
            # Bazı faturalarda şirket adı iki satıra bölünür, üst satırı birleştir
            if idx > 0 and len(candidate) < 20 and not SKIP_COMPANY_LINE_RE.search(lines[idx - 1]):
                prev = _clean_company_candidate(lines[idx - 1])
                if prev and not re.search(r"\d{5,}", prev):
                    candidate = f"{prev} {candidate}"
            if candidate:
                return candidate

    # 3. Öncelik: Üst bölümdeki ilk anlamlı metin satırı
    for line in lines[:10]:
        if SKIP_COMPANY_LINE_RE.search(line):
            continue
        if re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]{3,}", line):
            candidate = _clean_company_candidate(line)
            if candidate:
                return candidate

    return None


def _clean_company_candidate(raw: str) -> str:
    """Şirket adının yanındaki Fatura/VKN gibi sağ sütun kalıntılarını temizler."""
    # Aynı satırda sağ sütunda kalan fatura başlıklarını kes
    cleaned = re.split(
        r"\b(?:Fatura\s*(?:No|Tarihi)|Belge\s*No|[ÖO]zelle[şs]tirme\s*No|e-?Fatura|e-?Arşiv|VKN|TCKN|Vergi\s+Dairesi|Senaryo|ETTN)\b",
        raw,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:|,.")
    return cleaned


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """Dosya adında geçersiz olan karakterleri temizler."""
    sanitized = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip(" .")
    return sanitized


def build_unique_target(directory: Path, base_name: str, suffix: str, current_path: Path) -> Path:
    """Aynı isimde dosya varsa çakışmayı önlemek için sonuna (2), (3)... ekler."""
    target = directory / f"{base_name}{suffix}"
    if target == current_path or not target.exists():
        return target

    counter = 2
    while True:
        candidate = directory / f"{base_name} ({counter}){suffix}"
        if candidate == current_path or not candidate.exists():
            return candidate
        counter += 1


def process_folder(
    folder: Path,
    dry_run: bool = False,
    recursive: bool = False,
    date_format: str = "%Y-%m-%d",
) -> None:
    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdf_files = sorted(folder.glob(pattern))

    if not pdf_files:
        print(f"'{folder}' içinde PDF dosyası bulunamadı.")
        return

    renamed_count = 0
    skipped_count = 0

    for pdf_path in pdf_files:
        try:
            text = extract_text_from_pdf(pdf_path)
        except Exception as exc:
            print(f"[HATA] {pdf_path.name}: PDF okunamadı ({exc})")
            skipped_count += 1
            continue

        if not text.strip():
            print(f"[ATLANDI] {pdf_path.name}: Metin çıkarılamadı (taranmış/görsel PDF olabilir).")
            skipped_count += 1
            continue

        company = extract_company_name(text)
        invoice_no = extract_invoice_number(text)
        invoice_date = extract_invoice_date(text)

        missing = [
            label
            for label, val in (
                ("Şirket", company),
                ("Fatura No", invoice_no),
                ("Fatura Tarihi", invoice_date),
            )
            if not val
        ]
        if missing:
            print(f"[ATLANDI] {pdf_path.name}: Eksik bilgi -> {', '.join(missing)}")
            skipped_count += 1
            continue

        formatted_date = invoice_date.strftime(date_format)  # type: ignore[union-attr]
        new_stem = (
            f"{sanitize_filename(company, max_length=60)} - "  # type: ignore[arg-type]
            f"{sanitize_filename(invoice_no, max_length=35)} - "  # type: ignore[arg-type]
            f"{sanitize_filename(formatted_date, max_length=20)}"
        )

        target_path = build_unique_target(pdf_path.parent, new_stem, pdf_path.suffix, pdf_path)

        if target_path == pdf_path:
            print(f"[AYNI] {pdf_path.name}")
            continue

        if dry_run:
            print(f"[ÖNİZLEME] {pdf_path.name} -> {target_path.name}")
        else:
            pdf_path.rename(target_path)
            print(f"[ADLANDIRILDI] {pdf_path.name} -> {target_path.name}")
        renamed_count += 1

    print(f"\nÖzet: {renamed_count} dosya {'adlandırılacak' if dry_run else 'adlandırıldı'}, {skipped_count} dosya atlandı.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF faturaları 'Faturayı Basan Şirket - Fatura No - Fatura Tarihi.pdf' olarak yeniden adlandırır."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        type=Path,
        help="PDF faturaların bulunduğu klasör (varsayılan: mevcut klasör)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Dosyaları değiştirmeden yeni isimleri önizler",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Alt klasörlerdeki PDF'leri de işler",
    )
    parser.add_argument(
        "--date-format",
        default="%Y-%m-%d",
        help="Dosya adındaki tarih formatı (varsayılan: %%Y-%%m-%%d, örn: %%d.%%m.%%Y)",
    )

    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()

    if not folder.is_dir():
        print(f"Hata: Klasör bulunamadı -> {folder}", file=sys.stderr)
        sys.exit(1)

    process_folder(
        folder=folder,
        dry_run=args.dry_run,
        recursive=args.recursive,
        date_format=args.date_format,
    )


if __name__ == "__main__":
    main()
