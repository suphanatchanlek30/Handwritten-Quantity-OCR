# OCR summary — arm-15__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1394 x 1470
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=6

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 42 | 0.908 | needs_review | tight_crop | qty_column_by_position |
| 2 | 31 | 0.918 | needs_review | tight_crop | qty_column_by_position |
| 3 | 13 | 0.892 | needs_review | tight_crop | qty_column_by_position; possible_merged_digits(3->13, penalty=-0.008) |
| 4 | 12 | 0.900 | needs_review | tight_crop | qty_column_by_position |
| 5 | 5 | 0.748 | needs_review | tight_crop | qty_column_by_position; low_confidence(0.748<0.85) |
| 6 | 8 | 0.981 | needs_review | tight_crop | qty_column_by_position |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 9.1
- alignment: 397.2
- table_extraction: 0.1
- blank_detection: 3.2
- preprocessing: 1.5
- ocr_inference: 740.7
- total: 1161.5
