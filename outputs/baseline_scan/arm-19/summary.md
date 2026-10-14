# OCR summary — arm-19

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 14 | 0.963 | ok | tight_crop |  |
| 2 | 12 | 0.873 | ok | tight_crop |  |
| 3 | 11 | 0.377 | needs_review | tight_crop | possible_merged_digits(1->11, penalty=0.024); low_confidence(0.377<0.85) |
| 4 | 23 | 0.984 | ok | tight_crop |  |
| 5 | 24 | 0.960 | ok | tight_crop |  |
| 6 | 44 | 0.997 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 12.6
- alignment: 252.3
- table_extraction: 0.1
- blank_detection: 2.7
- preprocessing: 2.0
- ocr_inference: 954.7
- total: 1234.9
