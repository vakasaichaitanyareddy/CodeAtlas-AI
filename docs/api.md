# CodeAtlas REST API Specification

## Overview
CodeAtlas provides an OpenAPI 3.1-compliant REST API structured under `/api/v1`. All endpoints adhere to RFC 7807 problem details for structured error responses.

---

## 1. Authentication & Users
- `POST /api/v1/auth/register`: Register a new account with email, password, and full name.
- `POST /api/v1/auth/login`: Authenticate and receive `access_token` and `refresh_token`.
- `POST /api/v1/auth/refresh`: Refresh an expired access token using a valid refresh token.
- `GET /api/v1/auth/me`: Retrieve profile of currently authenticated user.
- `POST /api/v1/auth/logout`: Revoke active refresh token.

---

## 2. Repositories
- `GET /api/v1/repositories`: List repositories owned by or shared with current user.
- `POST /api/v1/repositories`: Register a new repository (GitHub URL, branch).
- `GET /api/v1/repositories/{id}`: Get repository metadata and indexing status.
- `DELETE /api/v1/repositories/{id}`: Delete repository and cascade clean all vectors, graph, and chunks.
- `POST /api/v1/repositories/{id}/index`: Enqueue background ingestion and indexing job.
- `GET /api/v1/repositories/{id}/index/status`: Get live progress of current indexing job.

---

## 3. Query & RAG
- `POST /api/v1/repositories/{id}/query`: Execute hybrid RAG query with grounded answer and citations.
- `GET /api/v1/repositories/{id}/conversations`: List past conversation threads.
- `POST /api/v1/repositories/{id}/conversations`: Create new conversation thread.
- `GET /api/v1/repositories/{id}/conversations/{c_id}`: Get conversation message history.

---

## 4. Code Graph & Impact
- `GET /api/v1/repositories/{id}/graph`: Query graph nodes and edges with filtering.
- `POST /api/v1/repositories/{id}/impact-analysis`: Compute upstream and downstream impact for a selected symbol or file.
- `GET /api/v1/repositories/{id}/symbols`: Search symbol index by name, type, or file.

---

## 5. Pull Requests & Security
- `GET /api/v1/repositories/{id}/pull-requests`: List pull requests.
- `POST /api/v1/repositories/{id}/pull-requests/{pr_id}/analyze`: Run deep AI + graph PR analysis.
- `GET /api/v1/repositories/{id}/security`: Retrieve detected security vulnerabilities and secrets.
