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
| 6 | 53 | 0.209 | needs_review | tight_crop | letters_mapped_to_digits('S3'->53); low_confidence(0.209<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 7.9
- alignment: 222.9
- qty_column: 16.7
- table_extraction: 0.2
- blank_detection: 4.1
- preprocessing: 1.9
- ocr_inference: 240.6
- total: 502.4
