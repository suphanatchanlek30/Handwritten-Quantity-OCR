# OCR summary — arm-10__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1913 x 2017
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=3, ok=3

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 12 | 0.946 | ok | tight_crop |  |
| 2 | 13 | 0.832 | needs_review | tight_crop | possible_merged_digits(3->13, penalty=-0.001); low_confidence(0.832<0.85) |
| 3 | 86 | 0.935 | ok | tight_crop |  |
| 4 | 97 | 0.996 | ok | tight_crop |  |
| 5 | 69 | 0.795 | needs_review | tight_crop | low_confidence(0.795<0.85) |
| 6 | 72 | 0.767 | needs_review | tight_crop | low_confidence(0.767<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 8.2
- alignment: 531.1
- qty_column: 15.8
- table_extraction: 0.1
- blank_detection: 3.5
- preprocessing: 2.1
- ocr_inference: 299.7
- total: 869.1
