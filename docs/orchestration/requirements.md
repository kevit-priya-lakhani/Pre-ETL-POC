The ETL tool must support the definition and scheduling of jobs that execute data tasks in
sequence. Integration with Apache Airflow or a built-in scheduler is preferred.
- Ability for a task to wait till file appears in folder
- Ability to raise error or continue in case of missing file.
- Ability for task to execute sql code in database (eg after copying info, update a flag) --> need more clarity on the meaning
---

Job params to be considered while creating config
- run schedule: 
    - retries
    - retry delay
    - timeout

- file ingestion:
    - source path / file names 
    - wait time for file to appear (filewise/ jobwise?)
    - error handling for missing files
- post loading sql execution
    - sql commands to execute

- connections 
either connection details for source and destination or connection id (airflow) 
    - source 
    - destination 
    - blob storage (overrides default)