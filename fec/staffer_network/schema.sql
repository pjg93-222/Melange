PRAGMA foreign_keys = ON;

CREATE TABLE source_system (
    source_system_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    authority_scope TEXT NOT NULL,
    terms_uri TEXT,
    license TEXT,
    redistribution_class TEXT NOT NULL,
    authorization_status TEXT NOT NULL,
    CHECK (authorization_status IN ('AUTHORIZED', 'QUARANTINED', 'PROHIBITED'))
);

CREATE TABLE ingest_run (
    run_id TEXT PRIMARY KEY,
    source_system_id TEXT NOT NULL REFERENCES source_system(source_system_id),
    collected_at TEXT NOT NULL,
    source_as_of TEXT,
    query_json TEXT NOT NULL,
    collector_version TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    expected_count INTEGER,
    observed_count INTEGER NOT NULL CHECK (observed_count >= 0),
    accepted_count INTEGER NOT NULL CHECK (accepted_count >= 0),
    rejected_count INTEGER NOT NULL CHECK (rejected_count >= 0),
    completeness_status TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    CHECK (accepted_count + rejected_count = observed_count)
);

CREATE TABLE raw_record (
    raw_record_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES ingest_run(run_id),
    source_record_type TEXT NOT NULL,
    source_record_key TEXT,
    source_uri TEXT,
    blob_sha256 TEXT NOT NULL,
    media_type TEXT NOT NULL,
    source_created_at TEXT,
    source_updated_at TEXT,
    locator_json TEXT NOT NULL
);

CREATE TABLE entity (
    entity_id TEXT PRIMARY KEY,
    entity_kind TEXT NOT NULL,
    created_system_at TEXT NOT NULL,
    retired_system_at TEXT,
    CHECK (entity_kind IN (
        'person', 'organization', 'legislative_term', 'office', 'committee',
        'institution', 'education_program', 'lda_filing', 'lda_activity',
        'issue', 'bill'
    )),
    CHECK (retired_system_at IS NULL OR retired_system_at > created_system_at)
);

CREATE TABLE source_entity (
    source_entity_id TEXT PRIMARY KEY,
    source_system_id TEXT NOT NULL REFERENCES source_system(source_system_id),
    entity_kind TEXT NOT NULL,
    source_key TEXT NOT NULL,
    first_raw_record_id TEXT NOT NULL REFERENCES raw_record(raw_record_id),
    UNIQUE (source_system_id, entity_kind, source_key)
);

CREATE TABLE source_entity_observation (
    source_entity_id TEXT NOT NULL REFERENCES source_entity(source_entity_id),
    raw_record_id TEXT NOT NULL REFERENCES raw_record(raw_record_id),
    observed_at TEXT NOT NULL,
    observation_role TEXT NOT NULL,
    PRIMARY KEY (source_entity_id, raw_record_id)
);

CREATE TABLE resolution_decision (
    decision_id TEXT PRIMARY KEY,
    left_source_entity_id TEXT NOT NULL REFERENCES source_entity(source_entity_id),
    right_source_entity_id TEXT NOT NULL REFERENCES source_entity(source_entity_id),
    decision TEXT NOT NULL,
    method TEXT NOT NULL,
    model_version TEXT,
    score REAL,
    adjudicator TEXT NOT NULL,
    rationale TEXT NOT NULL,
    system_from TEXT NOT NULL,
    system_to TEXT,
    CHECK (decision IN ('MATCH', 'DISTINCT', 'POSSIBLE', 'SPLIT')),
    CHECK (left_source_entity_id <> right_source_entity_id)
);

CREATE TABLE entity_membership (
    source_entity_id TEXT NOT NULL REFERENCES source_entity(source_entity_id),
    entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    decision_id TEXT REFERENCES resolution_decision(decision_id),
    assignment_method TEXT NOT NULL,
    system_from TEXT NOT NULL,
    system_to TEXT,
    PRIMARY KEY (source_entity_id, entity_id, system_from),
    CHECK (assignment_method IN ('SOURCE_NATIVE', 'RESOLUTION')),
    CHECK (
        (assignment_method = 'SOURCE_NATIVE' AND decision_id IS NULL) OR
        (assignment_method = 'RESOLUTION' AND decision_id IS NOT NULL)
    ),
    CHECK (system_to IS NULL OR system_to > system_from)
);

CREATE TABLE identifier_assertion (
    assertion_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    namespace TEXT NOT NULL,
    identifier TEXT NOT NULL,
    source_entity_id TEXT NOT NULL REFERENCES source_entity(source_entity_id),
    system_from TEXT NOT NULL,
    system_to TEXT,
    UNIQUE (namespace, identifier, system_from),
    CHECK (system_to IS NULL OR system_to > system_from)
);

CREATE UNIQUE INDEX identifier_assertion_one_current
    ON identifier_assertion(namespace, identifier)
    WHERE system_to IS NULL;

CREATE TABLE lda_activity_lobbyist_observation (
    observation_id TEXT PRIMARY KEY,
    raw_record_id TEXT NOT NULL REFERENCES raw_record(raw_record_id),
    activity_source_entity_id TEXT NOT NULL REFERENCES source_entity(source_entity_id),
    lobbyist_source_entity_id TEXT NOT NULL REFERENCES source_entity(source_entity_id),
    occurrence_ordinal INTEGER NOT NULL CHECK (occurrence_ordinal >= 0),
    covered_position_raw TEXT,
    new_flag INTEGER CHECK (new_flag IS NULL OR new_flag IN (0, 1)),
    observed_at TEXT NOT NULL,
    system_from TEXT NOT NULL,
    system_to TEXT,
    UNIQUE (raw_record_id, activity_source_entity_id, occurrence_ordinal),
    CHECK (activity_source_entity_id <> lobbyist_source_entity_id),
    CHECK (system_to IS NULL OR system_to > system_from)
);

CREATE TABLE relation_assertion (
    assertion_id TEXT PRIMARY KEY,
    subject_source_entity_id TEXT NOT NULL REFERENCES source_entity(source_entity_id),
    predicate TEXT NOT NULL,
    object_source_entity_id TEXT REFERENCES source_entity(source_entity_id),
    literal_json TEXT,
    valid_start_earliest TEXT,
    valid_start_latest TEXT,
    valid_end_earliest TEXT,
    valid_end_latest TEXT,
    start_precision TEXT NOT NULL,
    end_precision TEXT NOT NULL,
    asserted_current INTEGER NOT NULL DEFAULT 0 CHECK (asserted_current IN (0, 1)),
    observed_at TEXT NOT NULL,
    system_from TEXT NOT NULL,
    system_to TEXT,
    raw_record_id TEXT NOT NULL REFERENCES raw_record(raw_record_id),
    extraction_method TEXT NOT NULL,
    extraction_confidence REAL,
    parser_version TEXT NOT NULL,
    CHECK ((object_source_entity_id IS NULL) <> (literal_json IS NULL)),
    CHECK (start_precision IN ('day', 'month', 'year', 'unknown')),
    CHECK (end_precision IN ('day', 'month', 'year', 'unknown')),
    CHECK ((valid_start_earliest IS NULL) = (valid_start_latest IS NULL)),
    CHECK ((valid_end_earliest IS NULL) = (valid_end_latest IS NULL)),
    CHECK (valid_start_earliest IS NULL OR valid_start_earliest <= valid_start_latest),
    CHECK (valid_end_earliest IS NULL OR valid_end_earliest <= valid_end_latest),
    CHECK (valid_start_earliest IS NULL OR valid_end_latest IS NULL OR valid_start_earliest <= valid_end_latest),
    CHECK (asserted_current = 0 OR valid_end_earliest IS NULL),
    CHECK (system_to IS NULL OR system_to > system_from)
);

CREATE TABLE consolidation_build (
    consolidation_build_id TEXT PRIMARY KEY,
    corpus_manifest_sha256 TEXT NOT NULL,
    consolidation_version TEXT NOT NULL,
    as_of TEXT NOT NULL,
    config_json TEXT NOT NULL
);

CREATE TABLE canonical_fact (
    fact_id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    predicate TEXT NOT NULL,
    object_entity_id TEXT REFERENCES entity(entity_id),
    literal_json TEXT,
    valid_start_earliest TEXT,
    valid_start_latest TEXT,
    valid_end_earliest TEXT,
    valid_end_latest TEXT,
    fact_status TEXT NOT NULL,
    consolidation_build_id TEXT NOT NULL REFERENCES consolidation_build(consolidation_build_id),
    system_from TEXT NOT NULL,
    system_to TEXT,
    supersedes_fact_id TEXT REFERENCES canonical_fact(fact_id),
    CHECK ((object_entity_id IS NULL) <> (literal_json IS NULL)),
    CHECK (fact_status IN ('ACTIVE', 'CONFLICTED', 'RETRACTED', 'SUPERSEDED')),
    CHECK ((valid_start_earliest IS NULL) = (valid_start_latest IS NULL)),
    CHECK ((valid_end_earliest IS NULL) = (valid_end_latest IS NULL)),
    CHECK (valid_start_earliest IS NULL OR valid_start_earliest <= valid_start_latest),
    CHECK (valid_end_earliest IS NULL OR valid_end_earliest <= valid_end_latest),
    CHECK (valid_start_earliest IS NULL OR valid_end_latest IS NULL OR valid_start_earliest <= valid_end_latest),
    CHECK (system_to IS NULL OR system_to > system_from)
);

CREATE TABLE fact_support (
    fact_id TEXT NOT NULL REFERENCES canonical_fact(fact_id),
    assertion_id TEXT NOT NULL REFERENCES relation_assertion(assertion_id),
    support_role TEXT NOT NULL,
    system_from TEXT NOT NULL,
    system_to TEXT,
    PRIMARY KEY (fact_id, assertion_id, system_from)
);

CREATE TABLE network_build (
    build_id TEXT PRIMARY KEY,
    as_of TEXT NOT NULL,
    corpus_manifest_sha256 TEXT NOT NULL,
    config_json TEXT NOT NULL,
    derivation_version TEXT NOT NULL
);

CREATE TABLE network_edge (
    edge_id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL REFERENCES network_build(build_id),
    layer TEXT NOT NULL,
    predicate TEXT NOT NULL,
    subject_entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    object_entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    directed INTEGER NOT NULL CHECK (directed IN (0, 1)),
    raw_weight REAL NOT NULL CHECK (raw_weight >= 0),
    scaled_weight REAL CHECK (scaled_weight >= 0),
    evidence_class TEXT NOT NULL,
    precision_bucket TEXT NOT NULL,
    support_count INTEGER NOT NULL CHECK (support_count > 0),
    support_digest TEXT NOT NULL,
    CHECK (subject_entity_id <> object_entity_id),
    CHECK (precision_bucket IN ('day', 'month', 'year', 'undated-only')),
    CHECK (length(support_digest) = 64)
);

CREATE TABLE network_edge_support (
    edge_id TEXT NOT NULL REFERENCES network_edge(edge_id),
    fact_id TEXT NOT NULL REFERENCES canonical_fact(fact_id),
    contribution REAL NOT NULL CHECK (contribution >= 0),
    PRIMARY KEY (edge_id, fact_id)
);
