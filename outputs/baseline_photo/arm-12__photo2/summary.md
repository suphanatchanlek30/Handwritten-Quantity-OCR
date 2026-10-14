# OCR summary — arm-12__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2865 x 3021
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=3, ok=3

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 88 | 0.993 | ok | tight_crop |  |
| 2 | 99 | 0.817 | needs_review | tight_crop | low_confidence(0.817<0.85) |
| 3 | 91 | 0.595 | needs_review | tight_crop | possible_merged_digits(9->91, penalty=0.016); low_confidence(0.595<0.85) |
| 4 | 95 | 0.989 | ok | tight_crop |  |
| 5 | 36 | 0.997 | ok | tight_crop |  |
| 6 | 66 | 0.705 | needs_review | tight_crop | letters_mapped_to_digits('b6'->66); low_confidence(0.705<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 34.4
- alignment: 323.9
- table_extraction: 0.1
- blank_detection: 3.3
- preprocessing: 1.8
- ocr_inference: 873.0
- total: 1247.2
