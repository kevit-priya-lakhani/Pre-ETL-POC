File reading RFP test pack 
-------------------------------

Main file: Account_20251219 103000_RFP_FileReadingTest.txt
--------------------------------------------------------------
Coverage in the main file:
- UTF-8 with BOM
- Pipe-delimited format
- Configurable skip rows: first 2 rows are preamble rows
- Header row after skipped rows/comment
- Comment lines starting with #
- Mixed line endings: LF, CRLF, and CR
- Quoted/enclosed values, including a value containing the pipe delimiter
- Leading/trailing spaces for trim behavior
- Non-printable character in one account number
- Empty values
- Row-filter examples using numeric amount values
- Bad-record examples: malformed row, invalid numeric value, invalid date value
- Filename contains a timestamp pattern: Account_20251219 103000_...

Additional variant files:
----------------------------
- Account_20251219 103000_comma_utf8.csv: comma-delimited UTF-8
- Account_20251219 103000_semicolon_utf16.txt: semicolon-delimited UTF-16 with BOM
- Account_20251219 103000_tab_ansi.txt: tab-delimited ANSI/Windows-1252
- Account_20251219 103000_fixed_length_utf8.txt: fixed-length sample
- Account_20251219 103000_empty.txt: empty-file behavior test

Additional file added for quote-enclosed value testing:
---------------------------------------------------------
- Account_20251219 103000_pipe_quote_enclosed_values.txt
  Purpose: pipe-delimited flat file where every header and data field is enclosed in double quotes, including empty fields as "".

Additional mixed-record-type case 
------------------------------------
File: Account_20251219 103000_mixed_record_types.txt
Purpose: Tests files containing multiple logical record types in the same physical file.
Structure:
- Lines beginning with # are comments.
- Header: record_type|record_id|payload_or_fields
- ACC rows contain original Account.txt account payload with an ACC prefix.
- PAY rows contain sample payment records.
- TRL row is a trailer/summary record that should normally be ignored.
Expected ETL behavior:
- Account ingestion should filter record_type == ACC or first column/prefix ACC.
- Payment ingestion should filter record_type == PAY.
- Bad-record thresholds should apply after filtering, so intentionally ignored record types do not count as bad records.
- The malformed PAY_BAD_001 row can be used to test validation behavior for payment ingestion.


Timestamp Segmented files
------------------------------
Files:
- Payment_20260410_090000.txt
- Payment_20260411_090000.txt
Purpose:
- Test dynamic filename / timestamp handling for payment delta files.
Payment key separation:
- First file payment keys: PK20260410_1 to PK20260410_20.
- Second file payment keys: PK20260411_1 to PK20260411_20.



Sample JSON & XML files
-------------------------------
Files:
- Account.json
- Account.xml


