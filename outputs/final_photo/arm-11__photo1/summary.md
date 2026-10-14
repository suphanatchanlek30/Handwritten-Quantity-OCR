# OCR summary — arm-11__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1766 x 1862
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 13 | 0.965 | ok | tight_crop |  |
| 2 | 14 | 0.975 | ok | tight_crop |  |
| 3 | 36 | 0.901 | needs_review | tight_crop | possible_merged_digits(3->36, penalty=-0.002); tight_vs_segments_disagree(36 vs 31) |
| 4 | 42 | 0.989 | ok | tight_crop |  |
| 5 | 53 | 0.997 | ok | tight_crop |  |
| 6 | 84 | 1.000 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 5.2
- alignment: 288.0
- qty_column: 15.7
- table_extraction: 0.1
- blank_detection: 3.4
- preprocessing: 2.0
- ocr_inference: 350.2
- total: 673.6
