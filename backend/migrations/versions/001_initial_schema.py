"""Initial schema with pgvector, RLS, and indexes.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Enum types are created automatically by sa.Enum(..., create_type=True)
    # in the create_table calls below — no explicit CREATE TYPE needed.

    # --- tenants ---
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("settings", JSONB, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- user_profiles ---
    op.create_table(
        "user_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(
                "admin", "doctor", "nurse", "staff", name="app_role", create_type=True
            ),
            nullable=False,
            server_default="staff",
        ),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_user_profiles_tenant_id", "user_profiles", ["tenant_id"])

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by",
            UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "ready",
                "failed",
                name="document_status",
                create_type=True,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("ocr_confidence", sa.Float, nullable=True),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])

    # --- document_chunks ---
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("section_title", sa.String(255), nullable=True),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id", "document_chunks", ["document_id"]
    )
    op.create_index("ix_document_chunks_tenant_id", "document_chunks", ["tenant_id"])

    # Add vector and tsvector columns (raw SQL for pgvector types)
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(768)")
    op.execute("ALTER TABLE document_chunks ADD COLUMN search_vector tsvector")

    # HNSW index for vector similarity search
    op.execute("""
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # GIN index for full-text search
    op.execute("""
        CREATE INDEX ix_document_chunks_search_vector_gin
        ON document_chunks
        USING gin (search_vector)
    """)

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    # --- query_messages ---
    op.create_table(
        "query_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations", JSONB, nullable=True),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("prompt_tokens", sa.Integer, nullable=True),
        sa.Column("completion_tokens", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_query_messages_conversation_id", "query_messages", ["conversation_id"]
    )
    op.create_index("ix_query_messages_tenant_id", "query_messages", ["tenant_id"])

    # --- query_cache ---
    op.create_table(
        "query_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("response_content", sa.Text, nullable=False),
        sa.Column("citations", JSONB, nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_query_cache_tenant_id", "query_cache", ["tenant_id"])
    op.create_index("ix_query_cache_query_hash", "query_cache", ["query_hash"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # --- invitations ---
    op.create_table(
        "invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invited_by",
            UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "admin", "doctor", "nurse", "staff", name="app_role", create_type=True
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "accepted",
                "expired",
                "revoked",
                name="invitation_status",
                create_type=True,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("token", sa.String(255), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_invitations_tenant_id", "invitations", ["tenant_id"])
    op.create_index("ix_invitations_token", "invitations", ["token"])

    # =============================================
    # Row Level Security Policies
    # =============================================
    rls_tables = [
        "documents",
        "document_chunks",
        "conversations",
        "query_messages",
        "query_cache",
        "audit_logs",
        "invitations",
        "user_profiles",
    ]

    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            FOR ALL
            USING (tenant_id::text = current_setting('app.current_tenant', true))
            WITH CHECK (tenant_id::text = current_setting('app.current_tenant', true))
        """)

    # Audit logs: append-only (no UPDATE or DELETE for non-superusers)
    op.execute("""
        CREATE POLICY audit_logs_insert_only ON audit_logs
        FOR INSERT
        WITH CHECK (true)
    """)

    # =============================================
    # Seed role permissions data
    # =============================================
    op.execute("""
        CREATE TABLE role_permissions (
            role app_role NOT NULL,
            permission TEXT NOT NULL,
            PRIMARY KEY (role, permission)
        )
    """)

    permissions = [
        # Admin
        ("admin", "documents.upload"),
        ("admin", "documents.delete"),
        ("admin", "documents.view"),
        ("admin", "queries.execute"),
        ("admin", "audit.view"),
        ("admin", "users.manage"),
        ("admin", "org.settings"),
        ("admin", "llm.configure"),
        # Doctor
        ("doctor", "documents.upload"),
        ("doctor", "documents.delete"),
        ("doctor", "documents.view"),
        ("doctor", "queries.execute"),
        # Nurse
        ("nurse", "documents.upload"),
        ("nurse", "documents.delete"),
        ("nurse", "documents.view"),
        ("nurse", "queries.execute"),
        # Staff
        ("staff", "documents.view"),
        ("staff", "queries.execute"),
    ]

    values = ", ".join(f"('{role}'::app_role, '{perm}')" for role, perm in permissions)
    op.execute(f"INSERT INTO role_permissions (role, permission) VALUES {values}")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS role_permissions")

    tables = [
        "invitations",
        "audit_logs",
        "query_cache",
        "query_messages",
        "conversations",
        "document_chunks",
        "documents",
        "user_profiles",
        "tenants",
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    op.execute("DROP TYPE IF EXISTS invitation_status")
    op.execute("DROP TYPE IF EXISTS document_status")
    op.execute("DROP TYPE IF EXISTS app_role")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
