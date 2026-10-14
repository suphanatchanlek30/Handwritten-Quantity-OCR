# OCR summary — arm-2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 101 | 0.759 | needs_review | tight_crop | low_confidence(0.759<0.85) |
| 2 | 203 | 0.991 | ok | tight_crop |  |
| 3 | 409 | 0.958 | ok | tight_crop |  |
| 4 | 56 | 0.994 | ok | tight_crop |  |
| 5 | 77 | 0.999 | ok | tight_crop |  |
| 6 | 86 | 0.998 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 4.0
- alignment: 200.4
- qty_column: 17.1
- table_extraction: 0.1
- blank_detection: 3.7
- preprocessing: 3.5
- ocr_inference: 415.8
- total: 652.6
