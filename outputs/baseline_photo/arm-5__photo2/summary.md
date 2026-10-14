# OCR summary — arm-5__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2084 x 2197
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 23 | 0.872 | ok | tight_crop |  |
| 2 | 31 | 1.000 | ok | tight_crop |  |
| 3 | 42 | 0.877 | ok | tight_crop |  |
| 4 | 68 | 0.996 | ok | tight_crop |  |
| 5 | 76 | 0.987 | ok | tight_crop |  |
| 6 | 53 | 0.208 | needs_review | tight_crop | letters_mapped_to_digits('S3'->53); low_confidence(0.208<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 19.6
- alignment: 266.3
- table_extraction: 0.1
- blank_detection: 3.3
- preprocessing: 1.4
- ocr_inference: 642.0
- total: 944.1
