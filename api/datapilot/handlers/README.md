# module_data 数据源 handler 清单

> 自动生成。当前支持 **78** 个数据源。

每个源一个 `<name>_handler/` 目录,含 `<name>_handler.py`(实现)、`connection_args.py`(连接参数,可转 JSON Schema 渲染表单)、`requirements.txt`(独立依赖,惰性加载)、多数含 `README.md` + `icon.svg`。新增源 = 加目录,`_discover()` 自动注册。

**能力位**:读 / 写 / 抽取(dlt)/ 结构 / 流式 / 向量 / 接口(可生成数据服务)。


## 关系型 / 数仓 / OLAP (54)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `athena` | Amazon Athena | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | aws_access_key_id, aws_secret_access_key, region_name, database, workgroup, catalog |
| `aurora` | Amazon Aurora (MySQL) | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port, db_engine |
| `bigquery` | Google BigQuery | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | project_id, dataset, service_account_keys, service_account_json |
| `clickhouse` | ClickHouse | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | protocol, user, database, host, port, password |
| `cloud_spanner` | Google Cloud Spanner | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | instance_id, database_id, project, dialect, credentials |
| `cloud_sql` | Google Cloud SQL | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port, db_engine |
| `cockroachdb` | CockroachDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `crate` | CrateDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `databend` | Databend | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port |
| `databricks` | Databricks | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | server_hostname, http_path, access_token, session_configuration, http_headers, catalog |
| `db2` | IBM Db2 | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, database, user, password, port, schema |
| `dolt` | Dolt | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `doris` | Apache Doris | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `dremio` | Dremio | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, username, password |
| `druid` | Apache Druid | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, path, scheme, user, password |
| `duckdb` | DuckDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | database, read_only |
| `edgelessdb` | EdgelessDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port, ssl |
| `firebird` | Firebird | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, database, user, password |
| `greptimedb` | GreptimeDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `hana` | SAP HANA | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | address, port, user, password, schema, database |
| `hive` | Apache Hive | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | username, password, database, host, port, auth |
| `impala` | Apache Impala | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port |
| `informix` | IBM Informix | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `ingres` | Actian Ingres | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, server, database, servertype |
| `mariadb` | MariaDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | url, user, password, database, host, port |
| `materialize` | Materialize | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `matrixone` | MatrixOne | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port, ssl |
| `monetdb` | MonetDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, database, user, password, port, schema_name |
| `mssql` | Microsoft SQL Server | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port, server |
| `mysql` | MySQL | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | url, user, password, database, host, port |
| `oceanbase` | OceanBase | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `opengauss` | OpenGauss | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port |
| `oracle` | Oracle | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | dsn, host, port, sid, service_name, user |
| `orioledb` | OrioleDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port |
| `pinot` | Apache Pinot | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, broker_port, controller_port, path, scheme, username |
| `planetscale` | PlanetScale | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port |
| `postgresql` | PostgreSQL | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port, schema |
| `questdb` | QuestDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `redshift` | Amazon Redshift | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, database, user, password, schema |
| `rockset` | Rockset | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, api_key, api_server, host, port |
| `singlestore` | SingleStore | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `snowflake` | Snowflake | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | account, user, password, private_key_path, private_key, private_key_passphrase |
| `sqlany` | SAP SQL Anywhere | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, server, database |
| `sqlite` | SQLite | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | db_file |
| `sqreamdb` | SQream | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, user, password, port, database, service |
| `starrocks` | StarRocks | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `supabase` | Supabase | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `teradata` | Teradata | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, user, password, database |
| `tidb` | TiDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port |
| `timescaledb` | TimescaleDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `trino` | Trino | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, catalog, schema |
| `vertica` | Vertica | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port, schema_name |
| `vitess` | Vitess | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |
| `yugabyte` | YugabyteDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, port, user, password, database |

## 时序库 (2)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `influxdb` | InfluxDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | host, token, database, org |
| `tdengine` | TDengine | ✓ |  | ✓ | ✓ |  |  | ✓ | user, password, database, url, token |

## 文档库 (4)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `couchbase` | Couchbase | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, bucket, connection_string, scope |
| `documentdb` | Amazon DocumentDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, database, host, port, kwargs |
| `dynamodb` | Amazon DynamoDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | aws_access_key_id, aws_secret_access_key, region_name, aws_session_token |
| `mongodb` | MongoDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | username, password, database, host, port |

## 宽列(CQL) (2)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `cassandra` | Apache Cassandra | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, protocol_version, host, port, keyspace |
| `scylla` | ScyllaDB | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | user, password, protocol_version, host, port, keyspace |

## 图库 (1)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `neo4j` | Neo4j | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | uri, username, password, database |

## 键值 (1)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `redis` | Redis | ✓ | ✓ | ✓ | ✓ |  |  |  | host, port, password, db |

## 搜索引擎 (2)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `elasticsearch` | Elasticsearch | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | hosts, cloud_id, user, password, api_key |
| `opensearch` | OpenSearch | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | hosts, user, password, verify_certs |

## 向量库 (7)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `chromadb` | ChromaDB | ✓ | ✓ |  | ✓ |  | ✓ | ✓ | host, port, persist_directory |
| `lancedb` | LanceDB | ✓ | ✓ |  | ✓ |  | ✓ | ✓ | persist_directory, api_key, region, host_override |
| `milvus` | Milvus | ✓ | ✓ |  | ✓ |  | ✓ | ✓ | uri, token, search_default_limit, search_metric_type, search_ignore_growing, search_params |
| `pgvector` | pgvector (PostgreSQL) | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | user, password, database, host, port, schema |
| `pinecone` | Pinecone | ✓ | ✓ |  | ✓ |  | ✓ | ✓ | api_key, environment, dimension, metric, pods, replicas |
| `qdrant` | Qdrant | ✓ | ✓ |  | ✓ |  | ✓ | ✓ | location, url, host, port, grpc_port, prefer_grpc |
| `weaviate` | Weaviate | ✓ | ✓ |  | ✓ |  | ✓ | ✓ | weaviate_url, weaviate_api_key, persistence_directory |

## 文件 / 对象存储 (3)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `azure_blob` | Azure Blob Storage | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | container_name, connection_string |
| `gcs` | Google Cloud Storage | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | bucket, service_account_keys, service_account_json |
| `s3` | S3 / 对象存储 | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | aws_access_key_id, aws_secret_access_key, bucket, region_name, aws_session_token, endpoint_url |

## 流式消息 (1)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `kafka` | Apache Kafka | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | bootstrap_servers, group_id, security_protocol, sasl_mechanism, sasl_plain_username, sasl_plain_password |

## 变更捕获 CDC (1)

| source_type | 名称 | 读 | 写 | 抽 | 构 | 流 | 向 | 接 | 主要连接参数 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `mysql_binlog` | MySQL Binlog (CDC) | ✓ |  | ✓ | ✓ | ✓ |  |  | host, port, user, password, database, server_id |

---

> 验证程度:MySQL 协议族 + binlog CDC 已对运行中的 MySQL 真连验证;S3/DuckDB 对 MinIO、sqlite/duckdb 本机已真测;其余为结构验证(注册/实例化/URL),驱动在各自 requirements,接真库时按需安装。向量库委托 Agno(`agno[...]` extra)。

