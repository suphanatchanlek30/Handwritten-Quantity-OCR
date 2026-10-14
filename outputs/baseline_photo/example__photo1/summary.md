# OCR summary — example__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1851 x 2466
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 78 | 0.767 | needs_review | tight_crop | low_confidence(0.767<0.85) |
| 2 | 54 | 0.966 | ok | tight_crop |  |
| 3 | 79 | 0.635 | needs_review | tight_crop | low_confidence(0.635<0.85) |
| 4 | 36 | 0.940 | ok | tight_crop |  |
| 5 | 289 | 0.988 | ok | tight_crop |  |
| 6 | 65 | 0.982 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 16.7
- alignment: 265.8
- table_extraction: 0.1
- blank_detection: 3.5
- preprocessing: 0.9
- ocr_inference: 420.3
- total: 718.7
