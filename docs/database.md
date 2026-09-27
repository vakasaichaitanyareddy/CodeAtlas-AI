# CodeAtlas Database Architecture (PostgreSQL 16)

## Overview
CodeAtlas stores all relational state, user credentials, repository metadata, AST symbol tables, code chunks, graph topology, conversations, PR analyses, security findings, and audit logs in PostgreSQL 16.

---

## Entity Relationship Summary

```
                      +-------------------+
                      |       users       |
                      +---------+---------+
                                | 1
                                |
                                | *
                      +---------v---------+
                      |   repositories    |
                      +----+---------+----+
                           |         |
          +----------------+         +----------------+
          | *                                         | *
+---------v---------+                       +---------v---------+
| repository_files  |                       |  repository_commits
+---------+---------+                       +-------------------+
          | 1
          |
          | *
+---------v---------+
|   code_symbols    |
+---------+---------+
          | 1
          |
          | *
+---------v---------+       +-------------------+       +-------------------+
|    code_chunks    |       |    graph_nodes    |       |    graph_edges    |
+-------------------+       +---------+---------+       +---------+---------+
                                      | 1                         |
                                      +-------------+-------------+
                                                    | *
                                            (source / target)
```

---

## Table Specifications

### 1. `users`
- `id`: `UUID` (Primary Key, default `gen_random_uuid()`)
- `email`: `VARCHAR(255)` (Unique, Not Null, Indexed)
- `hashed_password`: `VARCHAR(255)` (Not Null)
- `full_name`: `VARCHAR(255)` (Nullable)
- `role`: `VARCHAR(50)` (Not Null, default `'USER'`)
- `is_active`: `BOOLEAN` (Not Null, default `true`)
- `github_user_id`: `VARCHAR(100)` (Nullable, Indexed)
- `created_at`: `TIMESTAMPTZ` (Not Null, default `now()`)
- `updated_at`: `TIMESTAMPTZ` (Not Null, default `now()`)

### 2. `refresh_tokens`
- `id`: `UUID` (Primary Key)
- `user_id`: `UUID` (Not Null, Foreign Key -> `users.id` ON DELETE CASCADE, Indexed)
- `token_hash`: `VARCHAR(255)` (Unique, Not Null, Indexed)
- `expires_at`: `TIMESTAMPTZ` (Not Null)
- `revoked`: `BOOLEAN` (Not Null, default `false`)
- `created_at`: `TIMESTAMPTZ` (Not Null)

### 3. `repositories`
- `id`: `UUID` (Primary Key)
- `owner_id`: `UUID` (Not Null, Foreign Key -> `users.id` ON DELETE CASCADE, Indexed)
- `name`: `VARCHAR(255)` (Not Null)
- `full_name`: `VARCHAR(255)` (Not Null, Indexed)
- `github_url`: `VARCHAR(512)` (Not Null)
- `default_branch`: `VARCHAR(100)` (Not Null, default `'main'`)
- `is_private`: `BOOLEAN` (Not Null, default `false`)
- `is_indexed`: `BOOLEAN` (Not Null, default `false`)
- `current_commit_sha`: `VARCHAR(64)` (Nullable)
- `index_version`: `INTEGER` (Not Null, default `1`)
- `status`: `VARCHAR(50)` (Not Null, default `'PENDING'`)
- `created_at`: `TIMESTAMPTZ` (Not Null)
- `updated_at`: `TIMESTAMPTZ` (Not Null)

### 4. `repository_branches`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `name`: `VARCHAR(255)` (Not Null)
- `commit_sha`: `VARCHAR(64)` (Not Null)
- `is_default`: `BOOLEAN` (Not Null, default `false`)
- `updated_at`: `TIMESTAMPTZ` (Not Null)

### 5. `repository_commits`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `sha`: `VARCHAR(64)` (Not Null, Indexed)
- `message`: `TEXT` (Not Null)
- `author_name`: `VARCHAR(255)` (Nullable)
- `author_email`: `VARCHAR(255)` (Nullable)
- `committed_at`: `TIMESTAMPTZ` (Not Null)

### 6. `repository_files`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `commit_sha`: `VARCHAR(64)` (Not Null, Indexed)
- `path`: `VARCHAR(1024)` (Not Null, Indexed)
- `language`: `VARCHAR(50)` (Nullable, Indexed)
- `loc`: `INTEGER` (Not Null, default `0`)
- `size_bytes`: `INTEGER` (Not Null, default `0`)
- `content_hash`: `VARCHAR(64)` (Not Null, Indexed)
- `is_deleted`: `BOOLEAN` (Not Null, default `false`)

### 7. `code_symbols`
- `id`: `UUID` (Primary Key)
- `file_id`: `UUID` (Not Null, Foreign Key -> `repository_files.id` ON DELETE CASCADE, Indexed)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `commit_sha`: `VARCHAR(64)` (Not Null, Indexed)
- `name`: `VARCHAR(255)` (Not Null, Indexed)
- `qualified_name`: `VARCHAR(512)` (Not Null, Indexed)
- `symbol_type`: `VARCHAR(50)` (Not Null, Indexed) # CLASS, FUNCTION, METHOD, etc.
- `start_line`: `INTEGER` (Not Null)
- `end_line`: `INTEGER` (Not Null)
- `parent_symbol_id`: `UUID` (Nullable, Foreign Key -> `code_symbols.id` ON DELETE SET NULL)
- `docstring`: `TEXT` (Nullable)
- `signature`: `TEXT` (Nullable)

### 8. `code_chunks`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `file_id`: `UUID` (Not Null, Foreign Key -> `repository_files.id` ON DELETE CASCADE, Indexed)
- `symbol_id`: `UUID` (Nullable, Foreign Key -> `code_symbols.id` ON DELETE SET NULL)
- `commit_sha`: `VARCHAR(64)` (Not Null, Indexed)
- `chunk_index`: `INTEGER` (Not Null)
- `content`: `TEXT` (Not Null)
- `content_hash`: `VARCHAR(64)` (Not Null, Indexed)
- `start_line`: `INTEGER` (Not Null)
- `end_line`: `INTEGER` (Not Null)
- `token_count`: `INTEGER` (Not Null, default `0`)
- `qdrant_point_id`: `UUID` (Nullable, Indexed)

### 9. `graph_nodes`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `commit_sha`: `VARCHAR(64)` (Not Null, Indexed)
- `node_key`: `VARCHAR(512)` (Not Null) # unique per repo+commit+key
- `node_type`: `VARCHAR(50)` (Not Null, Indexed) # FILE, MODULE, CLASS, FUNCTION, ENDPOINT, MODEL
- `name`: `VARCHAR(255)` (Not Null)
- `file_path`: `VARCHAR(1024)` (Nullable)
- `symbol_id`: `UUID` (Nullable, Foreign Key -> `code_symbols.id` ON DELETE SET NULL)
- `metadata_json`: `JSONB` (Nullable)

### 10. `graph_edges`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `commit_sha`: `VARCHAR(64)` (Not Null, Indexed)
- `source_node_id`: `UUID` (Not Null, Foreign Key -> `graph_nodes.id` ON DELETE CASCADE, Indexed)
- `target_node_id`: `UUID` (Not Null, Foreign Key -> `graph_nodes.id` ON DELETE CASCADE, Indexed)
- `edge_type`: `VARCHAR(50)` (Not Null, Indexed) # IMPORTS, CALLS, INHERITS, IMPLEMENTS, DEPENDS_ON, EXPOSES, QUERIES
- `metadata_json`: `JSONB` (Nullable)

### 11. `index_jobs`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `commit_sha`: `VARCHAR(64)` (Not Null)
- `status`: `VARCHAR(50)` (Not Null, default `'QUEUED'`, Indexed) # QUEUED, RUNNING, COMPLETED, FAILED, RETRYING
- `current_step`: `VARCHAR(100)` (Nullable)
- `progress_percent`: `INTEGER` (Not Null, default `0`)
- `error_message`: `TEXT` (Nullable)
- `stats_json`: `JSONB` (Nullable)
- `started_at`: `TIMESTAMPTZ` (Nullable)
- `completed_at`: `TIMESTAMPTZ` (Nullable)
- `created_at`: `TIMESTAMPTZ` (Not Null)

### 12. `conversations`
- `id`: `UUID` (Primary Key)
- `user_id`: `UUID` (Not Null, Foreign Key -> `users.id` ON DELETE CASCADE, Indexed)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `commit_sha`: `VARCHAR(64)` (Nullable)
- `title`: `VARCHAR(255)` (Not Null, default `'New Conversation'`)
- `created_at`: `TIMESTAMPTZ` (Not Null)
- `updated_at`: `TIMESTAMPTZ` (Not Null)

### 13. `messages`
- `id`: `UUID` (Primary Key)
- `conversation_id`: `UUID` (Not Null, Foreign Key -> `conversations.id` ON DELETE CASCADE, Indexed)
- `role`: `VARCHAR(20)` (Not Null) # USER, ASSISTANT, SYSTEM
- `content`: `TEXT` (Not Null)
- `citations_json`: `JSONB` (Nullable)
- `retrieval_metadata_json`: `JSONB` (Nullable)
- `tokens_used`: `INTEGER` (Nullable)
- `latency_ms`: `INTEGER` (Nullable)
- `created_at`: `TIMESTAMPTZ` (Not Null)

### 14. `pull_requests`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `github_pr_number`: `INTEGER` (Not Null, Indexed)
- `title`: `VARCHAR(512)` (Not Null)
- `source_branch`: `VARCHAR(255)` (Not Null)
- `target_branch`: `VARCHAR(255)` (Not Null)
- `base_sha`: `VARCHAR(64)` (Not Null)
- `head_sha`: `VARCHAR(64)` (Not Null)
- `status`: `VARCHAR(50)` (Not Null, default `'OPEN'`)
- `created_at`: `TIMESTAMPTZ` (Not Null)

### 15. `pull_request_analyses`
- `id`: `UUID` (Primary Key)
- `pull_request_id`: `UUID` (Not Null, Foreign Key -> `pull_requests.id` ON DELETE CASCADE, Indexed)
- `head_sha`: `VARCHAR(64)` (Not Null)
- `summary`: `TEXT` (Nullable)
- `risk_score`: `FLOAT` (Nullable)
- `changed_files_count`: `INTEGER` (Not Null, default `0`)
- `affected_components_json`: `JSONB` (Nullable)
- `security_findings_json`: `JSONB` (Nullable)
- `test_gap_analysis_json`: `JSONB` (Nullable)
- `ai_review_markdown`: `TEXT` (Nullable)
- `created_at`: `TIMESTAMPTZ` (Not Null)

### 16. `security_findings`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `commit_sha`: `VARCHAR(64)` (Not Null, Indexed)
- `file_path`: `VARCHAR(1024)` (Not Null)
- `line_number`: `INTEGER` (Not Null)
- `severity`: `VARCHAR(20)` (Not Null, Indexed) # CRITICAL, HIGH, MEDIUM, LOW
- `category`: `VARCHAR(50)` (Not Null, Indexed) # SECRET, SQL_INJECTION, COMMAND_INJECTION, etc.
- `title`: `VARCHAR(255)` (Not Null)
- `description`: `TEXT` (Not Null)
- `masked_evidence`: `TEXT` (Not Null) # NEVER store raw secrets
- `remediation_advice`: `TEXT` (Nullable)
- `status`: `VARCHAR(20)` (Not Null, default `'ACTIVE'`)
- `created_at`: `TIMESTAMPTZ` (Not Null)

### 17. `documentation_artifacts`
- `id`: `UUID` (Primary Key)
- `repository_id`: `UUID` (Not Null, Foreign Key -> `repositories.id` ON DELETE CASCADE, Indexed)
- `commit_sha`: `VARCHAR(64)` (Not Null)
- `doc_type`: `VARCHAR(50)` (Not Null, Indexed)
- `title`: `VARCHAR(255)` (Not Null)
- `content_markdown`: `TEXT` (Not Null)
- `created_at`: `TIMESTAMPTZ` (Not Null)

### 18. `audit_logs`
- `id`: `UUID` (Primary Key)
- `user_id`: `UUID` (Nullable, Foreign Key -> `users.id` ON DELETE SET NULL, Indexed)
- `repository_id`: `UUID` (Nullable, Foreign Key -> `repositories.id` ON DELETE SET NULL, Indexed)
- `action`: `VARCHAR(100)` (Not Null, Indexed)
- `resource_type`: `VARCHAR(100)` (Not Null)
- `resource_id`: `VARCHAR(255)` (Nullable)
- `ip_address`: `VARCHAR(45)` (Nullable)
- `user_agent`: `VARCHAR(512)` (Nullable)
- `payload_json`: `JSONB` (Nullable)
- `created_at`: `TIMESTAMPTZ` (Not Null)
