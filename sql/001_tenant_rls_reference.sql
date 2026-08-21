-- StructuraX PostgreSQL tenant-isolation reference.
-- Reference-only: this file is not a production migration and does not prove IAM,
-- connection-pool, backup, key-management, or operational isolation.

CREATE SCHEMA IF NOT EXISTS structurax;

CREATE TABLE IF NOT EXISTS structurax.evidence_records (
    tenant_id text NOT NULL,
    artifact_id text NOT NULL,
    ciphertext_sha256 char(64) NOT NULL,
    key_reference text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, artifact_id)
);

ALTER TABLE structurax.evidence_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE structurax.evidence_records FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_evidence_select ON structurax.evidence_records;
CREATE POLICY tenant_evidence_select
ON structurax.evidence_records
FOR SELECT
USING (
    tenant_id = current_setting('app.tenant_id', true)
    AND current_setting('app.tenant_id', true) IS NOT NULL
);

DROP POLICY IF EXISTS tenant_evidence_insert ON structurax.evidence_records;
CREATE POLICY tenant_evidence_insert
ON structurax.evidence_records
FOR INSERT
WITH CHECK (
    tenant_id = current_setting('app.tenant_id', true)
    AND current_setting('app.tenant_id', true) IS NOT NULL
);

DROP POLICY IF EXISTS tenant_evidence_update ON structurax.evidence_records;
CREATE POLICY tenant_evidence_update
ON structurax.evidence_records
FOR UPDATE
USING (
    tenant_id = current_setting('app.tenant_id', true)
    AND current_setting('app.tenant_id', true) IS NOT NULL
)
WITH CHECK (
    tenant_id = current_setting('app.tenant_id', true)
    AND current_setting('app.tenant_id', true) IS NOT NULL
);

DROP POLICY IF EXISTS tenant_evidence_delete ON structurax.evidence_records;
CREATE POLICY tenant_evidence_delete
ON structurax.evidence_records
FOR DELETE
USING (
    tenant_id = current_setting('app.tenant_id', true)
    AND current_setting('app.tenant_id', true) IS NOT NULL
);

COMMENT ON TABLE structurax.evidence_records IS
'Reference-only StructuraX tenant-RLS design; not evidence of production deployment.';
