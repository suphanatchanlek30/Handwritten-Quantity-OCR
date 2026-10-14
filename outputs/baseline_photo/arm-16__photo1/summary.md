# OCR summary — arm-16__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2550 x 2689
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 22 | 0.999 | ok | tight_crop |  |
| 2 | 38 | 0.842 | needs_review | tight_crop | tight_vs_segments_disagree(38 vs 32); low_confidence(0.842<0.85) |
| 3 | 64 | 0.994 | ok | tight_crop |  |
| 4 | 47 | 0.999 | ok | tight_crop |  |
| 5 | 49 | 0.995 | ok | tight_crop |  |
| 6 | 55 | 0.501 | needs_review | tight_crop | letters_mapped_to_digits('S5'->55); low_confidence(0.501<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 27.2
- alignment: 374.0
- table_extraction: 0.1
- blank_detection: 3.4
- preprocessing: 2.1
- ocr_inference: 952.1
- total: 1370.1
