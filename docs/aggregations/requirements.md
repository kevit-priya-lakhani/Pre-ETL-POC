- Ability to merge multiple files into one
- Ability to aggregate info out of a file (group by and aggregated columns)
- Aggregation functions:
    o Min
    o Max
    o First
    o Last
    o Count
    o Sum
    o Avg
- Aggregated files should have the same column transformation properties as the native
ones (the ones applicable)


An initial simple plan for the requirements
 tasks will be executed in sequence.
 one aggregation file, one destination file / or multiple destinations?
 multiple  source files- id of the files used for ingestion

- merging multiple files
 Can be done using join operations
 specify: 
    - source file ids 
    - columns of all the files needed
    - join type: left, right, inner, cross. etc(as supported by duckdb)
    - join on column 
    - extra params as required by join type

- aggregations
    - source id (if singular block)
    - aggregation function to be applied, column name, alias
    - group by
    - order by column (asc/desc)

- column transformations
    (same as previous transformation blocks OR specify file name)

- destination file id (to be used for further reference)
all these 3 tasks can be done on the same set of source files, hence specify destination






- destination file id
 

