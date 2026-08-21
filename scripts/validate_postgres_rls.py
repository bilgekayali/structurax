"""Validate the PostgreSQL RLS reference against an ephemeral PostgreSQL instance."""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.errors import InsufficientPrivilege


ROOT = Path(__file__).resolve().parents[1]
ROLE = "structurax_app"


def _app_dsn(admin_dsn: str, password: str) -> str:
    info = psycopg.conninfo.conninfo_to_dict(admin_dsn)
    info.update(user=ROLE, password=password)
    return psycopg.conninfo.make_conninfo(**info)


def validate() -> dict[str, object]:
    admin_dsn = os.environ["DATABASE_URL"]
    app_password = os.environ["STRUCTURAX_APP_PASSWORD"]

    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute((ROOT / "sql/001_tenant_rls_reference.sql").read_text(encoding="utf-8"))
        role_exists = admin.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,)
        ).fetchone()
        if role_exists:
            admin.execute(
                sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(ROLE), sql.Literal(app_password)
                )
            )
        else:
            admin.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(ROLE), sql.Literal(app_password)
                )
            )
        admin.execute(sql.SQL("ALTER ROLE {} NOBYPASSRLS").format(sql.Identifier(ROLE)))
        admin.execute(sql.SQL("GRANT USAGE ON SCHEMA structurax TO {}").format(sql.Identifier(ROLE)))
        admin.execute(
            sql.SQL(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON structurax.evidence_records TO {}"
            ).format(sql.Identifier(ROLE))
        )
        admin.execute("TRUNCATE structurax.evidence_records")
        admin.execute(
            """
            INSERT INTO structurax.evidence_records
                (tenant_id, artifact_id, ciphertext_sha256, key_reference)
            VALUES
                ('tenant-a', 'A-001', %s, 'kms://reference/tenant-a/evidence'),
                ('tenant-b', 'B-001', %s, 'kms://reference/tenant-b/evidence')
            """,
            ("a" * 64, "b" * 64),
        )
        rls_enabled, rls_forced = admin.execute(
            """
            SELECT relrowsecurity, relforcerowsecurity
            FROM pg_class
            WHERE oid = 'structurax.evidence_records'::regclass
            """
        ).fetchone()
        bypass_rls = admin.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = %s", (ROLE,)
        ).fetchone()[0]
        server_version = admin.execute("SHOW server_version").fetchone()[0]

    app_dsn = _app_dsn(admin_dsn, app_password)
    with psycopg.connect(app_dsn, autocommit=True) as app:
        no_context_rows = app.execute(
            "SELECT count(*) FROM structurax.evidence_records"
        ).fetchone()[0]

        app.execute("SELECT set_config('app.tenant_id', %s, false)", ("tenant-a",))
        tenant_a_rows = app.execute(
            "SELECT tenant_id, artifact_id FROM structurax.evidence_records ORDER BY artifact_id"
        ).fetchall()

        cross_tenant_insert_blocked = False
        try:
            app.execute(
                """
                INSERT INTO structurax.evidence_records
                    (tenant_id, artifact_id, ciphertext_sha256, key_reference)
                VALUES
                    ('tenant-b', 'B-BLOCKED', %s, 'kms://reference/tenant-b/evidence')
                """,
                ("c" * 64,),
            )
        except InsufficientPrivilege:
            cross_tenant_insert_blocked = True

        cross_tenant_update_rows = app.execute(
            """
            UPDATE structurax.evidence_records
            SET key_reference = 'kms://reference/tenant-b/changed'
            WHERE tenant_id = 'tenant-b'
            """
        ).rowcount

        app.execute(
            """
            INSERT INTO structurax.evidence_records
                (tenant_id, artifact_id, ciphertext_sha256, key_reference)
            VALUES
                ('tenant-a', 'A-002', %s, 'kms://reference/tenant-a/evidence')
            """,
            ("d" * 64,),
        )
        tenant_a_after_insert = app.execute(
            "SELECT artifact_id FROM structurax.evidence_records ORDER BY artifact_id"
        ).fetchall()

        app.execute("SELECT set_config('app.tenant_id', %s, false)", ("tenant-b",))
        tenant_b_rows = app.execute(
            "SELECT tenant_id, artifact_id FROM structurax.evidence_records ORDER BY artifact_id"
        ).fetchall()

    blockers: list[str] = []
    if not rls_enabled:
        blockers.append("rls_not_enabled")
    if not rls_forced:
        blockers.append("rls_not_forced")
    if bypass_rls:
        blockers.append("application_role_can_bypass_rls")
    if no_context_rows != 0:
        blockers.append("rows_visible_without_tenant_context")
    if tenant_a_rows != [("tenant-a", "A-001")]:
        blockers.append("tenant_a_visibility_mismatch")
    if not cross_tenant_insert_blocked:
        blockers.append("cross_tenant_insert_not_blocked")
    if cross_tenant_update_rows != 0:
        blockers.append("cross_tenant_update_visible")
    if tenant_a_after_insert != [("A-001",), ("A-002",)]:
        blockers.append("same_tenant_insert_or_visibility_failed")
    if tenant_b_rows != [("tenant-b", "B-001")]:
        blockers.append("tenant_b_visibility_mismatch")

    if blockers:
        raise SystemExit("PostgreSQL RLS reference validation failed: " + ", ".join(blockers))

    return {
        "validation": "passed",
        "postgresql_version": server_version,
        "rls_enabled": True,
        "rls_forced": True,
        "application_role_bypassrls": False,
        "no_context_rows_visible": 0,
        "cross_tenant_insert_blocked": True,
        "cross_tenant_update_rows": 0,
        "tenant_a_visible_artifacts": ["A-001", "A-002"],
        "tenant_b_visible_artifacts": ["B-001"],
        "ephemeral_reference_environment": True,
        "production_database_validated": False,
        "production_identity_or_kms_validated": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
