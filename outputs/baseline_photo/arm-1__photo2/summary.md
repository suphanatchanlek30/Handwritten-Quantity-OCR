# OCR summary — arm-1__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2871 x 3028
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 15 | 0.992 | ok | tight_crop |  |
| 2 | 23 | 0.974 | ok | tight_crop |  |
| 3 | 29 | 0.886 | ok | tight_crop |  |
| 4 | 32 | 0.994 | ok | tight_crop |  |
| 5 | 49 | 0.571 | needs_review | tight_crop | letters_mapped_to_digits('4g'->49); low_confidence(0.571<0.85) |
| 6 | 48 | 0.997 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 37.5
- alignment: 334.5
- table_extraction: 0.1
- blank_detection: 3.8
- preprocessing: 1.2
- ocr_inference: 548.1
- total: 936.2
