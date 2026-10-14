# OCR summary — arm-18__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2387 x 2517
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=6

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 12 | 0.407 | needs_review | tight_crop | possible_merged_digits(2->12, penalty=0.024); low_confidence(0.407<0.85) |
| 2 | 18 | 0.070 | needs_review | tight_crop | possible_merged_digits(1->18, penalty=0.045); tight_vs_segments_disagree(18 vs 11); letters_mapped_to_digits('图'->1); low_confidence(0.070<0.85) |
| 3 | 32 | 0.703 | needs_review | tight_crop | tight_vs_segments_disagree(32 vs 11); low_confidence(0.703<0.85) |
| 4 | 14 | 0.992 | needs_review | tight_crop | possible_merged_digits(4->14, penalty=-0.007) |
| 5 | 19 | 0.171 | needs_review | tight_crop | possible_merged_digits(1->19, penalty=0.008); tight_vs_segments_disagree(19 vs 16); low_confidence(0.171<0.85) |
| 6 | 11 | 0.088 | needs_review | digit_segments | tight_vs_segments_disagree(1 vs 11); letters_mapped_to_digits('ı1'->11); low_confidence(0.088<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 11.6
- alignment: 313.7
- qty_column: 17.3
- table_extraction: 0.1
- blank_detection: 3.6
- preprocessing: 2.1
- ocr_inference: 370.7
- total: 726.8
