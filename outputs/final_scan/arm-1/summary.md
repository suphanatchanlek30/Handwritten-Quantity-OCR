# OCR summary — arm-1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 15 | 0.995 | ok | tight_crop |  |
| 2 | 23 | 0.973 | ok | tight_crop |  |
| 3 | 29 | 0.649 | needs_review | tight_crop | low_confidence(0.649<0.85) |
| 4 | 32 | 0.993 | ok | tight_crop |  |
| 5 | 43 | 0.904 | needs_review | tight_crop | possible_merged_digits(4->43, penalty=-0.010) |
| 6 | 48 | 0.993 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 12.2
- alignment: 200.7
- qty_column: 20.4
- table_extraction: 0.1
- blank_detection: 3.1
- preprocessing: 1.4
- ocr_inference: 228.7
- total: 472.8
