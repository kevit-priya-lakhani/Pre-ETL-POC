# Pre ETL pipeline ingestion stage requirements

## SFTP sensor- orchestration
Step 1: Connect with the SFTP server and check for the presence of the file. If the file is not present, wait and check again after a specified interval.

### Configurable Parameters
-File Format type:  Fixed / Delimited 
  - Delimiter: specify if type is delimited (eg. comma, pipe, tab)
-Encoding type ( optional ): specify the encoding type of the file (eg. ANSI, UTF-8, UTF-16 with or without BOM)
-Header row (optional): specify if the file contains a header row
-Ignore line prefix (optional): specify the prefix of the lines to be ignored during ingestion (eg. # for comment lines)
-Line endings (optional): specify the line ending type (eg. /n, /r/n)
-Enclosing special characters (optional): Columns values can either be enclosed in special characters or not. Most common enclosing character is “” (e.g. “Text value”)


-Skip-Count: number of lines to skip the file (optional)
-Skip-Condition: specify the condition to skip lines (eg. skip lines where column A is empty) (optional)

-Filter-Condition: specify the condition to filter lines (eg. only ingest lines where column B is greater than 100) (optional)

-Bad record threshold (optional): specify the threshold for bad records (eg. if more than 10% of records are bad, fail the ingestion)
- threshold type: percentage or absolute count (optional)

-Bad-Records Handling: specify how to handle bad records (eg. skip, log, or move to a separate file) (optional)

- Empty file handling: specify how to handle empty files (eg. skip, log, or fail the ingestion) (optional)

-File Name/ File regex: specify the name of the file to be ingested or the pattern to match the file name (eg. data_*.csv)

- Header names: specify the names of the columns in the file (optional, required if header row is not present)
- Data types: specify the data types of the columns (optional, required if header row is not present)
- Column validation rules: specify the validation rules for the columns (eg. column A must be a positive integer) (optional)
- Date format: specify the date format for date columns (optional, required if header row is not present and date columns are present)

