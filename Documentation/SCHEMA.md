# Aria — Database Schema

## Overview
SQLite is used for lightweight, zero-config local persistence. The schema is minimal by design — documents are stored as flat files on disk, while metadata and conversation history live in the database.

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│    documents    │       │  conversations   │       │    messages     │
├─────────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)          │◄──────│ conversation_id │
│ filename        │       │ title            │       │ id (PK)         │
│ original_path   │       │ model_provider   │       │ role            │
│ storage_path    │       │ model_name       │       │ content         │
│ file_type       │       │ created_at       │       │ sources_used    │
│ file_size_bytes │       │ updated_at       │       │ token_count     │
│ word_count      │       │ is_archived      │       │ created_at      │
│ token_count     │       └──────────────────┘       └─────────────────┘
│ extracted_text  │
│ is_active       │
│ created_at      │
└─────────────────┘
```

---

## Table: `documents`

Stores metadata for all files in the Sources Vault. Raw text is stored on disk at `storage_path`.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `TEXT` | PRIMARY KEY | UUID v4 |
| `filename` | `TEXT` | NOT NULL | Original filename (e.g., "research_paper.pdf") |
| `original_path` | `TEXT` | NOT NULL | Full path at time of upload |
| `storage_path` | `TEXT` | NOT NULL | Relative path in `data/vault/` (e.g., "doc_abc123.txt") |
| `file_type` | `TEXT` | NOT NULL | Extension: `pdf`, `docx`, `csv`, `xlsx`, `md`, `txt` |
| `file_size_bytes` | `INTEGER` | NOT NULL | Size of original file |
| `word_count` | `INTEGER` | DEFAULT 0 | Approximate word count of extracted text |
| `token_count` | `INTEGER` | DEFAULT 0 | Token count (tiktoken cl100k_base) |
| `extracted_text` | `TEXT` | | First 500 chars preview (for search) |
| `is_active` | `INTEGER` | DEFAULT 0 | Boolean: 1 = bound to current context |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | Upload timestamp |

**Indexes**:
```sql
CREATE INDEX idx_documents_active ON documents(is_active);
CREATE INDEX idx_documents_filename ON documents(filename);
CREATE VIRTUAL TABLE documents_fts USING fts5(filename, extracted_text, content='documents', content_rowid='rowid');
```

---

## Table: `conversations`

Represents a single chat thread.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `TEXT` | PRIMARY KEY | UUID v4 |
| `title` | `TEXT` | NOT NULL DEFAULT 'New Chat' | User-editable conversation name |
| `model_provider` | `TEXT` | NOT NULL | `gemini`, `claude`, `openai` |
| `model_name` | `TEXT` | NOT NULL | e.g., `gemini-1.5-pro`, `claude-3-5-sonnet` |
| `system_prompt` | `TEXT` | | Custom system prompt override (nullable) |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | Thread creation |
| `updated_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | Last message timestamp |
| `is_archived` | `INTEGER` | DEFAULT 0 | Boolean: archived threads hidden from main list |

**Indexes**:
```sql
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);
CREATE INDEX idx_conversations_archived ON conversations(is_archived);
```

---

## Table: `messages`

Individual messages within a conversation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `TEXT` | PRIMARY KEY | UUID v4 |
| `conversation_id` | `TEXT` | NOT NULL, FK → conversations(id), ON DELETE CASCADE | Parent thread |
| `role` | `TEXT` | NOT NULL, CHECK(role IN ('user', 'assistant', 'system')) | Message sender |
| `content` | `TEXT` | NOT NULL | Raw message text (Markdown) |
| `sources_used` | `TEXT` | | JSON array of document IDs referenced via @-mention or active binding |
| `token_count` | `INTEGER` | DEFAULT 0 | Approximate token count of content |
| `model_provider` | `TEXT` | | Provider used for this response (assistant only) |
| `model_name` | `TEXT` | | Model used for this response (assistant only) |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | Message timestamp |

**Indexes**:
```sql
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
```

---

## Table: `app_settings`

Key-value store for application configuration.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `key` | `TEXT` | PRIMARY KEY | Setting identifier |
| `value` | `TEXT` | NOT NULL | JSON-encoded value |
| `updated_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | Last modified |

**Default Keys**:
| Key | Value Type | Default |
|-----|-----------|---------|
| `theme` | `string` | `"dark"` |
| `default_provider` | `string` | `"gemini"` |
| `default_model` | `string` | `"gemini-1.5-pro"` |
| `gemini_api_key` | `string` | `""` |
| `claude_api_key` | `string` | `""` |
| `max_context_sources` | `integer` | `5` |
| `auto_save_interval` | `integer` | `30` (seconds) |
| `vault_panel_width` | `integer` | `320` (pixels) |

---

## Prisma Schema (Alternative Reference)

If migrating to Prisma in the future:

```prisma
generator client {
  provider = "prisma-client-py"
}

datasource db {
  provider = "sqlite"
  url      = "file:./aria.db"
}

model Document {
  id              String   @id @default(uuid())
  filename        String
  originalPath    String
  storagePath     String
  fileType        String
  fileSizeBytes   Int
  wordCount       Int      @default(0)
  tokenCount      Int      @default(0)
  extractedText   String?
  isActive        Boolean  @default(false)
  createdAt       DateTime @default(now())
  messages        Message[] @relation("MessageSources")

  @@index([isActive])
  @@index([filename])
  @@map("documents")
}

model Conversation {
  id            String    @id @default(uuid())
  title         String    @default("New Chat")
  modelProvider String
  modelName     String
  systemPrompt  String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  isArchived    Boolean   @default(false)
  messages      Message[]

  @@index([updatedAt])
  @@index([isArchived])
  @@map("conversations")
}

model Message {
  id              String       @id @default(uuid())
  conversationId  String
  conversation    Conversation @relation(fields: [conversationId], references: [id], onDelete: Cascade)
  role            String       // 'user' | 'assistant' | 'system'
  content         String
  sourcesUsed     String?      // JSON array of document IDs
  tokenCount      Int          @default(0)
  modelProvider   String?
  modelName       String?
  createdAt       DateTime     @default(now())
  sources         Document[]   @relation("MessageSources")

  @@index([conversationId, createdAt])
  @@map("messages")
}

model AppSetting {
  key       String   @id
  value     String
  updatedAt DateTime @updatedAt

  @@map("app_settings")
}
```

---

## Migration Strategy

1. **V0.1.0** (MVP): Create all tables as defined above
2. **Future**: Add `folders` table for vault organization, `tags` table for document categorization
3. **Future**: Add `embeddings` table if implementing vector RAG (migrate from raw text injection)
