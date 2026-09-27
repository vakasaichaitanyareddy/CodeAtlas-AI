"""Initial database schema for CodeAtlas

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-22 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('github_user_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_github_user_id'), 'users', ['github_user_id'], unique=False)

    # 2. refresh_tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)

    # 3. repositories
    op.create_table(
        'repositories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('github_url', sa.String(length=512), nullable=False),
        sa.Column('default_branch', sa.String(length=100), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False),
        sa.Column('is_indexed', sa.Boolean(), nullable=False),
        sa.Column('current_commit_sha', sa.String(length=64), nullable=True),
        sa.Column('index_version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_repositories_owner_id'), 'repositories', ['owner_id'], unique=False)
    op.create_index(op.f('ix_repositories_full_name'), 'repositories', ['full_name'], unique=False)

    # 4. repository_branches
    op.create_table(
        'repository_branches',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_repo_branch_unique', 'repository_branches', ['repository_id', 'name'], unique=True)

    # 5. repository_commits
    op.create_table(
        'repository_commits',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('sha', sa.String(length=64), nullable=False),
        sa.Column('message', sa.String(length=2048), nullable=False),
        sa.Column('author_name', sa.String(length=255), nullable=True),
        sa.Column('author_email', sa.String(length=255), nullable=True),
        sa.Column('committed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_repo_commit_unique', 'repository_commits', ['repository_id', 'sha'], unique=True)

    # 6. repository_files
    op.create_table(
        'repository_files',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('path', sa.String(length=1024), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('loc', sa.Integer(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_repo_file_commit_path', 'repository_files', ['repository_id', 'commit_sha', 'path'], unique=True)
    op.create_index(op.f('ix_repository_files_path'), 'repository_files', ['path'], unique=False)
    op.create_index(op.f('ix_repository_files_language'), 'repository_files', ['language'], unique=False)

    # 7. code_symbols
    op.create_table(
        'code_symbols',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('file_id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('qualified_name', sa.String(length=512), nullable=False),
        sa.Column('symbol_type', sa.String(length=50), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('parent_symbol_id', sa.String(length=36), nullable=True),
        sa.Column('docstring', sa.Text(), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['repository_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_symbol_id'], ['code_symbols.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_code_symbols_name'), 'code_symbols', ['name'], unique=False)
    op.create_index(op.f('ix_code_symbols_qualified_name'), 'code_symbols', ['qualified_name'], unique=False)
    op.create_index(op.f('ix_code_symbols_symbol_type'), 'code_symbols', ['symbol_type'], unique=False)

    # 8. code_chunks
    op.create_table(
        'code_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('file_id', sa.String(length=36), nullable=False),
        sa.Column('symbol_id', sa.String(length=36), nullable=True),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('qdrant_point_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['repository_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['symbol_id'], ['code_symbols.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chunk_repo_commit', 'code_chunks', ['repository_id', 'commit_sha'], unique=False)
    op.create_index(op.f('ix_code_chunks_content_hash'), 'code_chunks', ['content_hash'], unique=False)
    op.create_index(op.f('ix_code_chunks_qdrant_point_id'), 'code_chunks', ['qdrant_point_id'], unique=False)

    # 9. graph_nodes
    op.create_table(
        'graph_nodes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('node_key', sa.String(length=512), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=True),
        sa.Column('symbol_id', sa.String(length=36), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['symbol_id'], ['code_symbols.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_graph_node_repo_commit_key', 'graph_nodes', ['repository_id', 'commit_sha', 'node_key'], unique=True)
    op.create_index(op.f('ix_graph_nodes_node_type'), 'graph_nodes', ['node_type'], unique=False)

    # 10. graph_edges
    op.create_table(
        'graph_edges',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('source_node_id', sa.String(length=36), nullable=False),
        sa.Column('target_node_id', sa.String(length=36), nullable=False),
        sa.Column('edge_type', sa.String(length=50), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_node_id'], ['graph_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['graph_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_graph_edge_source_target_type', 'graph_edges', ['source_node_id', 'target_node_id', 'edge_type'], unique=False)

    # 11. index_jobs
    op.create_table(
        'index_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('current_step', sa.String(length=100), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('stats_json', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_index_jobs_status'), 'index_jobs', ['status'], unique=False)

    # 12. conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)
    op.create_index(op.f('ix_conversations_repository_id'), 'conversations', ['repository_id'], unique=False)

    # 13. messages
    op.create_table(
        'messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations_json', sa.JSON(), nullable=True),
        sa.Column('retrieval_metadata_json', sa.JSON(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)

    # 14. pull_requests
    op.create_table(
        'pull_requests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('github_pr_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('source_branch', sa.String(length=255), nullable=False),
        sa.Column('target_branch', sa.String(length=255), nullable=False),
        sa.Column('base_sha', sa.String(length=64), nullable=False),
        sa.Column('head_sha', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pr_repo_number_unique', 'pull_requests', ['repository_id', 'github_pr_number'], unique=True)

    # 15. pull_request_analyses
    op.create_table(
        'pull_request_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('pull_request_id', sa.String(length=36), nullable=False),
        sa.Column('head_sha', sa.String(length=64), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('changed_files_count', sa.Integer(), nullable=False),
        sa.Column('affected_components_json', sa.JSON(), nullable=True),
        sa.Column('security_findings_json', sa.JSON(), nullable=True),
        sa.Column('test_gap_analysis_json', sa.JSON(), nullable=True),
        sa.Column('ai_review_markdown', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['pull_request_id'], ['pull_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pull_request_analyses_pull_request_id'), 'pull_request_analyses', ['pull_request_id'], unique=False)

    # 16. security_findings
    op.create_table(
        'security_findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('masked_evidence', sa.Text(), nullable=False),
        sa.Column('remediation_advice', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sec_repo_severity', 'security_findings', ['repository_id', 'severity'], unique=False)
    op.create_index(op.f('ix_security_findings_category'), 'security_findings', ['category'], unique=False)

    # 17. documentation_artifacts
    op.create_table(
        'documentation_artifacts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('repository_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('doc_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_doc_repo_type', 'documentation_artifacts', ['repository_id', 'doc_type'], unique=False)

    # 18. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('repository_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('payload_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_repository_id'), 'audit_logs', ['repository_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('documentation_artifacts')
    op.drop_table('security_findings')
    op.drop_table('pull_request_analyses')
    op.drop_table('pull_requests')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('index_jobs')
    op.drop_table('graph_edges')
    op.drop_table('graph_nodes')
    op.drop_table('code_chunks')
    op.drop_table('code_symbols')
    op.drop_table('repository_files')
    op.drop_table('repository_commits')
    op.drop_table('repository_branches')
    op.drop_table('repositories')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
