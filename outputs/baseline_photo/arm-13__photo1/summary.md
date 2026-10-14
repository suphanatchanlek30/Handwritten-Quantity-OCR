# OCR summary — arm-13__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1747 x 1842
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 12 | 0.924 | ok | tight_crop |  |
| 2 | 14 | 0.776 | needs_review | tight_crop | possible_merged_digits(4->14, penalty=0.031); low_confidence(0.776<0.85) |
| 3 | 32 | 0.876 | ok | tight_crop |  |
| 4 | 63 | 0.949 | ok | tight_crop |  |
| 5 | 72 | 0.989 | ok | tight_crop |  |
| 6 | 81 | 0.985 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 11.8
- alignment: 236.6
- table_extraction: 0.1
- blank_detection: 3.5
- preprocessing: 2.2
- ocr_inference: 952.4
- total: 1217.4
