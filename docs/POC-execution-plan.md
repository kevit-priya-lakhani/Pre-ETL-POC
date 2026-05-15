## POC Execution plan- 2 days
### Objective:
To create a proof of concept (POC) for an ETL orchestration system using Airflow, demonstrating the ability to define and execute data pipelines based on configuration files. The POC will include the following components:
1. A directory structure for pipeline configurations, including ingestion, transformation, aggregation, loading, and orchestration.
2. A workflow for generating Airflow DAGs from the provided configuration files.
3. A sample pipeline execution workflow that validates connections, performs data ingestion, transformation, aggregation, and loading tasks, and executes post-loading SQL operations.

### Tasks:
1. **Define Directory Structure**: Create a directory structure for pipeline configurations as outlined in the workflow documentation.
2. **DAG Generation Workflow**: 
 - implement script to validate the configuration files against a predefined schema.
 - implement script to extract values from the configuration files and generate Airflow DAGs accordingly.
3. **Pipeline Execution Workflow**:
 - Implement connection validation for source and destination databases, and blob storage.
 - Implement ingestion, transformation, aggregation, and loading tasks based on the provided configurations.
4. **Pipeline Execution via API**: Implement functionality to trigger pipeline execution via Airflow's DAG run API, passing necessary parameters.
5. **Connection Management**: Implement secure storage and retrieval of connection details for databases and blob storage.


Execution plan and scope of POC:
Day 1:
- Setup PostgreSQL db, SFTP server, MinIO blob storage, and Airflow environment.
- Define the directory structure for pipeline configurations.
- Implement Ingestion tasks and functionality to perform ingestion:
  scope: - csv files from SFTP
         - single comment handling
         - single file per ingestion config
         - Filters: greaterhtan,less than, equals to
         - column validations: not null, data type checks, min/max value checks
         - bad record handling: only corrupt records considered, failed validation logged -- need to decide on the approach for handling invalid non-corrupt records
- Implement Transformation tasks:
    scope: 
        - simple transformations such as column renaming, data type conversions, and basic calculations based on the config provided.
        - transformations: concat, trim, upper/lower case, regex based transformations, arithmetic operations, round, series& uuid column generation
        - function chaining
- Implement aggregation tasks:
    scope:
        - simple aggregations such as sum, average, count, min, and max based on the config provided.
        - group by functionality based on the config provided.
        - Simple Union and Join operations based on the config provided.
Day 2:
- Implement Loading tasks:
    scope:
        - loading data into PostgreSQL from blob storage based on the config provided.
        - support for upsert and insert operations based on the config provided.
- Job orchestation:
    scope:
        - Implement connection validation for source and destination databases, and blob storage.
        - Scripts for validation and DAG- yaml  generation
        - Integration of scripts in the CI/CD pipeline