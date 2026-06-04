# 📋 DEPLOYMENT GUIDE: Font Fix untuk Document Generator

**Date:** 2026-06-03  
**Commit:** 590c255  
**Issue Fixed:** Font tidak muncul di generated PDF documents

---

## ✅ File yang WAJIB diupdate di Production

### 1. backend/document_template_library.py
**Status:** MODIFIED - Font fix untuk PDF generation  
**Changes:** 
- Line 2-4: Removed Google Fonts @import
- Changed font-family dari 'Noto Sans' ke 'Droid Sans Fallback'

---

## 🔄 Cara Deploy ke Production

### Option 1: Git Pull (Recommended)
```bash
ssh user@production-server
cd /home/qqwtlphb/backend  # sesuaikan dengan path backend production
git pull origin main
# Restart backend service (pilih sesuai setup kamu)
```

### Option 2: Manual Upload
```bash
# Upload file via SCP
scp backend/document_template_library.py user@server:/home/qqwtlphb/backend/
```

---

## ⚠️ PENTING: Restart Backend Setelah Update

Backend HARUS direstart agar perubahan apply. Pilih method sesuai setup:

- **LiteSpeed/Passenger:** `touch tmp/restart.txt`
- **Systemd service:** `sudo systemctl restart backend`
- **PM2:** `pm2 restart backend`
- **Manual:** Kill process lama, start ulang

---

## 🧪 Testing Checklist Setelah Deploy

**Pre-deployment:**
- [ ] Backup file lama: `cp document_template_library.py document_template_library.py.backup`
- [ ] Git pull atau upload file baru
- [ ] Restart backend service

**Post-deployment testing:**
- [ ] Backend bisa start tanpa error (check logs)
- [ ] Login ke web UI sebagai admin
- [ ] Buka halaman Document Generator
- [ ] Create/edit template dokumen
- [ ] Generate PDF (test Invoice, Receipt, atau type lain)
- [ ] Download PDF yang di-generate
- [ ] Buka PDF di viewer, verify text muncul dengan jelas
- [ ] Test dengan nama Indonesia dan simbol Rp (contoh: "Rp 5.000.000", "PT Sejahtera Indonesia")
- [ ] Verify font rendering konsisten di semua section PDF

---

## 📊 Technical Details

### Root Cause
Template `BASE_STYLE` menggunakan Google Fonts via `@import`, tapi WeasyPrint memblock external network requests untuk security. Ini menyebabkan:
1. Font 'Noto Sans' tidak bisa di-load
2. Conflict dengan `_PDF_FONT_CSS` di main.py yang force 'Droid Sans Fallback'
3. Result: font tidak muncul di PDF

### Solution
- Hapus Google Fonts `@import` dari BASE_STYLE
- Gunakan 'Droid Sans Fallback' yang tersedia di system
- WeasyPrint akan otomatis fallback ke Noto Sans atau Arial
- Font ter-embed dengan benar di PDF

### Before (Broken):
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&display=swap');
@page{size:A4;margin:0}
*{font-family:'Noto Sans',Arial,sans-serif;box-sizing:border-box}
```

### After (Fixed):
```css
@page{size:A4;margin:0}
*{font-family:'Droid Sans Fallback',Arial,sans-serif;box-sizing:border-box}
```

---

## 🎯 Expected Result

Setelah deploy, semua generated PDF akan:
- ✅ Menampilkan text dengan font yang benar
- ✅ Support karakter Indonesia (Rp, tanggal, nama dengan huruf khusus)
- ✅ Rendering konsisten di semua browser/PDF viewer
- ✅ File size tetap optimal

---

## 📄 Test Results (Local Dev)

**Test PDF Generated:** `/home/kevin/kantorteman/test_invoice_font_fixed.pdf`

```
Producer: WeasyPrint 68.1
Pages: 1
File size: 6573 bytes
Fonts embedded: Noto-Sans-Bold, Noto-Sans

Extracted text:
INVOICE INV/202606/004
Klien: Simple Test
Tanggal: 03 Juni 2026
Total: Rp 1.000.000
```

✅ All text extracted successfully = fonts working correctly!

---

## 🆘 Troubleshooting

**Problem:** Backend tidak start setelah update  
**Solution:** Check logs, pastikan tidak ada syntax error. File hanya ubah CSS string.

**Problem:** Font masih tidak muncul setelah deploy  
**Solution:** 
1. Pastikan backend sudah direstart
2. Hard refresh browser (Ctrl+F5)
3. Generate dokumen baru (jangan gunakan cache lama)
4. Verify server punya font Noto Sans atau Droid Sans installed

**Problem:** PDF kosong atau corrupt  
**Solution:**
1. Check WeasyPrint installed: `pip list | grep -i weasy`
2. Check system fonts: `fc-list | grep -i "noto\|droid"`
3. Review backend logs untuk error messages

---

## 📞 Support

Jika ada issue setelah deploy, check:
1. Backend error logs
2. WeasyPrint version (should be 68.1 or compatible)
3. System fonts availability

File changed: **1 file only**  
Risk level: **Low** (CSS change only, no logic changes)  
Rollback: **Easy** (revert commit atau restore backup file)
