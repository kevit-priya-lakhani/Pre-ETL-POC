
Uploads pipeline folder in the cofigs folder:
Pipeline directory structure:
- ingestion/
    accounts_ingestion_config.yml
    payments_ingestion_config.yml
- transformation/
    accounts_transformation_config.yml
    payments_transformation_config.yml
- aggregation/
    current_accounts_aggregation_config.yml
    payments_aggregation_config.yml
- loading/
    data_loading.yml
- orchestration/
    orchestration.yml

DAG generation workflow
- Upon arrival of a new pipeline folder:--> Added via a github PR
    - CI: config is validated against a predefined schema to ensure it contains all necessary information and adheres to expected formats.
    - CD: if valid, a DAG YAML is generated from the pipeline configs and committed to the dags/ folder.
    - At the next Airflow DAG processor cycle, dag_generation.py picks up the new YAML via load_yaml_dags and registers it as a live DAG.

Pipeline Creation & execution workflow
Mandatory stages: ingestion + loading. Transformation, aggregation, and post-loading SQL are optional and skipped when their config is absent from the pipeline folder.

step 1: validate and test connections to source and destination databases, and blob storage to ensure they are accessible and properly configured.
        - If any connection test fails, the entire DAG run is aborted.
        - Blob storage: if a connection_id is specified in the orchestration config, that connection is tested; otherwise the environment-level default blob storage connection is tested. Local disk is not used — blob storage is always required.

step 2: Ingestion tasks- config wise (parallel ingestion tasks created based on the configs provided) 
        - Wait for files to arrive in the source location using file sensor
        - Execute ingestion tasks to extract data from source and stage it in blob storage.
        - Pass on the path of the staged data to the next step via XComs or using run ids

step 3: Transformation tasks- parallel, one task per transformation config
        - Each transformation task reads from the upstream ingestion file_id declared in its config.
        - Tasks run in parallel; each is independent of other transformation tasks.
        - Write transformed data to blob storage and pass the output file_id to downstream tasks.

step 4: Aggregation tasks- parallel, each starts as soon as its upstream transformation dependency completes
        - Each aggregation task declares its upstream transformation config; it starts as soon as that specific transformation task completes (not waiting for all transformations).
        - Aggregation tasks that depend on the same transformation run in parallel with each other.
        - Loading (step 5) only begins once ALL aggregation tasks have completed successfully.

step 5: Loading tasks- sequential, in the order defined in the orchestration config
        - Source data is referenced by the upstream config file path declared in the loading config (can point to an ingestion, transformation, or aggregation config). The file_id is resolved from that config.
        - Execute loading tasks sequentially: each loading task completes before the next begins.

step 6: Post Loading SQL tasks
        - Run the post loading SQL scripts specified in the orchestration config against the destination database to perform any necessary cleanup, indexing, or logging operations after the data has been loaded.  


Pipeline execution via API:
- Trigger the pipeline execution via Airflow's DAG run API call to the orchestration layer, passing necessary parameters such as pipeline name, execution date, and any runtime configurations.
- dry_run mode: pass {"dry_run": true} in the DAG run conf. Steps 1–4 execute normally and stage output to blob storage for inspection. Steps 5 (loading) and 6 (post-loading SQL) are skipped entirely. 

Connection management:
- Connection details for source and destination databases, as well as blob storage, are stored securely in a centralized configuration file or a secrets manager. The orchestration layer retrieves these details at runtime to establish connections for the various tasks. This approach ensures that sensitive information is not hardcoded in the DAGs

TODO (not considered in implementation):
- Pipeline versioning strategy: when a pipeline config is updated via PR, in-flight DAG runs may be affected if the DAG structure changes (tasks added/removed). A versioning mechanism (e.g. version field in orchestration.yml, versioned job_id, or immutable pipeline snapshots) is required to safely handle concurrent runs during config updates.
- Monitoring and observability: Airflow-native logging and task state tracking is sufficient for the POC. A richer monitoring strategy (rows processed, bad record counts, load durations per table written to an audit DB table; Prometheus/Grafana for infrastructure metrics) is deferred post-POC.


