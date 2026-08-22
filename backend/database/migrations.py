from sqlalchemy import inspect, text

BASE_PROVIDER_CONNECTION_COLUMNS = {
    "id",
    "provider",
    "account_id",
    "account_label",
    "status",
    "expires_at",
    "auth_method_id",
    "created_at",
    "updated_at",
}

CURRENT_PROVIDER_CONNECTION_COLUMNS = BASE_PROVIDER_CONNECTION_COLUMNS | {"endpoint_url"}

LEGACY_PROVIDER_CONNECTION_COLUMNS = {
    "id",
    "provider",
    "auth_type",
    "account_name",
    "credential_key",
    "created_at",
    "updated_at",
}


def migrate_provider_connections_schema(db) -> None:
    inspector = inspect(db.engine)
    if "provider_connections" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("provider_connections")
    }
    if CURRENT_PROVIDER_CONNECTION_COLUMNS.issubset(columns):
        return
    if BASE_PROVIDER_CONNECTION_COLUMNS.issubset(columns):
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE provider_connections ADD COLUMN endpoint_url VARCHAR(2048)")
            )
        return
    if not LEGACY_PROVIDER_CONNECTION_COLUMNS.issubset(columns):
        raise RuntimeError(
            "Unsupported provider_connections schema. Add an explicit migration before starting Cowriter."
        )

    with db.engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO auth_methods (method_name, description)
                SELECT DISTINCT
                    COALESCE(NULLIF(TRIM(auth_type), ''), 'unknown'),
                    'Migrated from a legacy provider connection'
                FROM provider_connections
                """
            )
        )
        connection.execute(text("DROP TABLE IF EXISTS provider_connections_v2"))
        connection.execute(
            text(
                """
                CREATE TABLE provider_connections_v2 (
                    id INTEGER NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    account_id VARCHAR(100) NOT NULL,
                    account_label VARCHAR(100) NOT NULL,
                    endpoint_url VARCHAR(2048),
                    status VARCHAR(20) NOT NULL DEFAULT 'disconnected',
                    expires_at DATETIME,
                    auth_method_id INTEGER NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME,
                    PRIMARY KEY (id),
                    FOREIGN KEY(auth_method_id) REFERENCES auth_methods (id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO provider_connections_v2 (
                    id,
                    provider,
                    account_id,
                    account_label,
                    endpoint_url,
                    status,
                    expires_at,
                    auth_method_id,
                    created_at,
                    updated_at
                )
                SELECT
                    legacy.id,
                    legacy.provider,
                    'legacy-' || legacy.id,
                    legacy.account_name,
                    NULL,
                    'disconnected',
                    NULL,
                    auth_method.id,
                    legacy.created_at,
                    legacy.updated_at
                FROM provider_connections AS legacy
                JOIN auth_methods AS auth_method
                    ON auth_method.method_name = COALESCE(
                        NULLIF(TRIM(legacy.auth_type), ''),
                        'unknown'
                    )
                """
            )
        )
        connection.execute(text("DROP TABLE provider_connections"))
        connection.execute(
            text("ALTER TABLE provider_connections_v2 RENAME TO provider_connections")
        )


def ensure_provider_connection_indexes(db) -> None:
    inspector = inspect(db.engine)
    unique_column_sets = {
        tuple(constraint.get("column_names") or [])
        for constraint in inspector.get_unique_constraints("provider_connections")
    }
    unique_column_sets.update(
        tuple(index.get("column_names") or [])
        for index in inspector.get_indexes("provider_connections")
        if index.get("unique")
    )
    if ("provider", "account_id") in unique_column_sets:
        return

    with db.engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM provider_connections "
                "WHERE id NOT IN ("
                "SELECT MAX(id) FROM provider_connections GROUP BY provider, account_id"
                ")"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_provider_connections_provider_account "
                "ON provider_connections (provider, account_id)"
            )
        )
