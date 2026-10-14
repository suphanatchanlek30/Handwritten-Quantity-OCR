# OCR summary — arm-20__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1766 x 1862
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=4, ok=2

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 13 | 0.692 | needs_review | tight_crop | possible_merged_digits(3->13, penalty=0.001); low_confidence(0.692<0.85) |
| 2 | 14 | 0.992 | needs_review | tight_crop | possible_merged_digits(4->14, penalty=0.020) |
| 3 | 12 | 0.546 | needs_review | tight_crop | low_confidence(0.546<0.85) |
| 4 | 8 | 0.864 | ok | tight_crop |  |
| 5 | 1 | 0.152 | needs_review | tight_crop | low_confidence(0.152<0.85) |
| 6 | 9 | 0.946 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 12.8
- alignment: 252.3
- table_extraction: 0.1
- blank_detection: 3.0
- preprocessing: 1.3
- ocr_inference: 632.1
- total: 910.1
