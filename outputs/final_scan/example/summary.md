# OCR summary — example

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2591 x 3452
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 78 | 0.767 | needs_review | tight_crop | possible_merged_digits(7->78, penalty=0.001); low_confidence(0.767<0.85) |
| 2 | 54 | 0.977 | ok | tight_crop |  |
| 3 | 79 | 0.753 | needs_review | tight_crop | possible_merged_digits(7->79, penalty=0.021); low_confidence(0.753<0.85) |
| 4 | 36 | 0.989 | ok | tight_crop |  |
| 5 | 289 | 0.982 | ok | tight_crop |  |
| 6 | 65 | 0.927 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 11.4
- alignment: 312.3
- qty_column: 17.0
- table_extraction: 0.1
- blank_detection: 5.7
- preprocessing: 1.2
- ocr_inference: 189.0
- total: 543.6
