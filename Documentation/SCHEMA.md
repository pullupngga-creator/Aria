# SCHEMA.md — Aria Database Schema

## Overview
SQLite embedded database managed via `rusqlite` in Rust. Stores peer identities, chat history, file transfer metadata, voice message records, trust relationships, and user settings. All data stays local.

## Tables

### `settings`
Application-wide user settings. Single-row pattern.

```sql
CREATE TABLE settings (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    display_name        TEXT NOT NULL DEFAULT 'Aria User',
    avatar_path         TEXT,
    theme               TEXT NOT NULL DEFAULT 'system',     -- 'light' | 'dark' | 'system'
    default_download_dir TEXT NOT NULL DEFAULT '',          -- empty = OS Downloads/Aria
    audio_input_device  TEXT,
    require_trust       BOOLEAN NOT NULL DEFAULT 1,        -- auto-accept only from trusted peers
    notifications       BOOLEAN NOT NULL DEFAULT 1,
    listen_port         INTEGER NOT NULL DEFAULT 9473,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `peers`
Discovered and known peers. Fingerprint is the Ed25519 public key hash (short, human-readable).

```sql
CREATE TABLE peers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    public_key          TEXT NOT NULL,                      -- full Ed25519 public key (hex)
    fingerprint         TEXT NOT NULL UNIQUE,               -- short hash for display (e.g., "a3f9b2")
    display_name        TEXT,
    hostname            TEXT,
    ip_address          TEXT,                               -- last known IP
    port                INTEGER DEFAULT 9473,
    trust_level         TEXT NOT NULL DEFAULT 'untrusted', -- 'untrusted' | 'trusted' | 'blocked'
    avatar_path         TEXT,                               -- cached avatar file path
    first_seen          DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen           DATETIME,
    is_online           BOOLEAN NOT NULL DEFAULT 0,
    UNIQUE(public_key)
);
```

### `conversations`
One-to-one conversation threads. Maps to a single peer.

```sql
CREATE TABLE conversations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id             INTEGER NOT NULL REFERENCES peers(id) ON DELETE CASCADE,
    unread_count        INTEGER NOT NULL DEFAULT 0,
    last_message_id     INTEGER,
    last_activity       DATETIME,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(peer_id)
);
```

### `messages`
Individual chat messages: text, file offers, voice metadata.

```sql
CREATE TABLE messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id     INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_peer_id      INTEGER REFERENCES peers(id),       -- NULL = self
    type                TEXT NOT NULL,                      -- 'text' | 'file' | 'voice'
    content             TEXT,                               -- text body OR JSON metadata for file/voice
    file_path           TEXT,                               -- local path to received file or voice recording
    file_size           INTEGER,                            -- bytes
    file_name           TEXT,
    mime_type           TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',    -- 'pending' | 'sent' | 'delivered' | 'failed'
    signature           TEXT,                               -- Ed25519 signature of content (hex)
    timestamp           DATETIME DEFAULT CURRENT_TIMESTAMP,
    edited_at           DATETIME,
    is_deleted          BOOLEAN NOT NULL DEFAULT 0
);
```

### `file_transfers`
Active and completed file transfer sessions.

```sql
CREATE TABLE file_transfers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id          INTEGER REFERENCES messages(id) ON DELETE SET NULL,
    peer_id             INTEGER NOT NULL REFERENCES peers(id),
    direction           TEXT NOT NULL,                      -- 'outgoing' | 'incoming'
    file_path           TEXT NOT NULL,                      -- local source or destination path
    file_name           TEXT NOT NULL,
    file_size           INTEGER NOT NULL,
    bytes_transferred   INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'pending',    -- 'pending' | 'offered' | 'transferring' | 'completed' | 'failed' | 'cancelled'
    error_message       TEXT,
    checksum            TEXT,                               -- SHA-256 of file (hex)
    started_at          DATETIME,
    completed_at        DATETIME,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `voice_messages`
Voice message metadata and playback state.

```sql
CREATE TABLE voice_messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id          INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    duration_ms         INTEGER NOT NULL,                   -- length in milliseconds
    waveform_data       TEXT,                               -- JSON array of amplitude samples for visualization
    playback_position   INTEGER DEFAULT 0,                  -- last playback position (ms)
    is_played           BOOLEAN NOT NULL DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `typing_indicators`
Ephemeral typing state (cleaned up periodically).

```sql
CREATE TABLE typing_indicators (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id             INTEGER NOT NULL REFERENCES peers(id) ON DELETE CASCADE,
    conversation_id     INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    is_typing           BOOLEAN NOT NULL DEFAULT 1,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(peer_id, conversation_id)
);
```

## Indexes

```sql
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_peers_trust ON peers(trust_level);
CREATE INDEX idx_peers_online ON peers(is_online);
CREATE INDEX idx_file_transfers_status ON file_transfers(status);
CREATE INDEX idx_conversations_activity ON conversations(last_activity DESC);
```

## Data Flow
1. **Discovery**: Rust mDNS finds peer → upserts `peers` row → updates `is_online` → frontend receives event
2. **Chat Open**: User clicks peer → `conversations` upsert (if not exists) → load `messages` ordered by timestamp
3. **Message Send**: User sends text → `messages` insert with `status = 'pending'` → Rust delivers → updates `status` to `sent` → peer ACK → updates to `delivered`
4. **File Transfer**: User sends file → `messages` insert (type='file') + `file_transfers` insert → Rust sends offer → peer accepts → chunk transfer → progress updates `bytes_transferred` → complete → update `status`
5. **Voice**: User records → Web Audio API → JS sends to Rust → Rust stores WAV → `messages` + `voice_messages` inserts → transmit → peer receives → stores → plays

## Prisma Equivalent (for reference / future migration)

```prisma
model Setting {
  id                  Int      @id @default(autoincrement())
  displayName         String   @default("Aria User") @map("display_name")
  avatarPath          String?  @map("avatar_path")
  theme               String   @default("system")
  defaultDownloadDir  String   @default("") @map("default_download_dir")
  audioInputDevice    String?  @map("audio_input_device")
  requireTrust        Boolean  @default(true) @map("require_trust")
  notifications       Boolean  @default(true)
  listenPort          Int      @default(9473) @map("listen_port")
  createdAt           DateTime @default(now()) @map("created_at")
  updatedAt           DateTime @updatedAt @map("updated_at")

  @@map("settings")
}

model Peer {
  id            Int            @id @default(autoincrement())
  publicKey     String         @unique @map("public_key")
  fingerprint   String         @unique
  displayName   String?        @map("display_name")
  hostname      String?
  ipAddress     String?        @map("ip_address")
  port          Int            @default(9473)
  trustLevel    String         @default("untrusted") @map("trust_level")
  avatarPath    String?        @map("avatar_path")
  firstSeen     DateTime       @default(now()) @map("first_seen")
  lastSeen      DateTime?      @map("last_seen")
  isOnline      Boolean        @default(false) @map("is_online")
  conversations Conversation[]
  messages      Message[]      @relation("SentMessages")
  fileTransfers FileTransfer[]

  @@map("peers")
}

model Conversation {
  id            Int       @id @default(autoincrement())
  peerId        Int       @unique @map("peer_id")
  peer          Peer      @relation(fields: [peerId], references: [id], onDelete: Cascade)
  unreadCount   Int       @default(0) @map("unread_count")
  lastMessageId Int?      @map("last_message_id")
  lastActivity  DateTime? @map("last_activity")
  createdAt     DateTime  @default(now()) @map("created_at")
  messages      Message[]

  @@map("conversations")
}

model Message {
  id              Int           @id @default(autoincrement())
  conversationId  Int           @map("conversation_id")
  conversation    Conversation  @relation(fields: [conversationId], references: [id], onDelete: Cascade)
  senderPeerId    Int?          @map("sender_peer_id")
  sender          Peer?         @relation("SentMessages", fields: [senderPeerId], references: [id])
  type            String
  content         String?
  filePath        String?       @map("file_path")
  fileSize        Int?          @map("file_size")
  fileName        String?       @map("file_name")
  mimeType        String?       @map("mime_type")
  status          String        @default("pending")
  signature       String?
  timestamp       DateTime      @default(now())
  editedAt        DateTime?     @map("edited_at")
  isDeleted       Boolean       @default(false) @map("is_deleted")
  fileTransfer    FileTransfer?
  voiceMessage    VoiceMessage?

  @@index([conversationId])
  @@index([timestamp])
  @@map("messages")
}

model FileTransfer {
  id                Int       @id @default(autoincrement())
  messageId         Int?      @unique @map("message_id")
  message           Message?  @relation(fields: [messageId], references: [id], onDelete: SetNull)
  peerId            Int       @map("peer_id")
  peer              Peer      @relation(fields: [peerId], references: [id])
  direction         String
  filePath          String    @map("file_path")
  fileName          String    @map("file_name")
  fileSize          Int       @map("file_size")
  bytesTransferred  Int       @default(0) @map("bytes_transferred")
  status            String    @default("pending")
  errorMessage      String?   @map("error_message")
  checksum          String?
  startedAt         DateTime? @map("started_at")
  completedAt       DateTime? @map("completed_at")
  createdAt         DateTime  @default(now()) @map("created_at")

  @@index([status])
  @@map("file_transfers")
}

model VoiceMessage {
  id                Int      @id @default(autoincrement())
  messageId         Int      @unique @map("message_id")
  message           Message  @relation(fields: [messageId], references: [id], onDelete: Cascade)
  durationMs        Int      @map("duration_ms")
  waveformData      String?  @map("waveform_data")
  playbackPosition  Int      @default(0) @map("playback_position")
  isPlayed          Boolean  @default(false) @map("is_played")
  createdAt         DateTime @default(now()) @map("created_at")

  @@map("voice_messages")
}

model TypingIndicator {
  id              Int          @id @default(autoincrement())
  peerId          Int          @map("peer_id")
  peer            Peer         @relation(fields: [peerId], references: [id], onDelete: Cascade)
  conversationId  Int          @map("conversation_id")
  isTyping        Boolean      @default(true) @map("is_typing")
  updatedAt       DateTime     @default(now()) @map("updated_at")

  @@unique([peerId, conversationId])
  @@map("typing_indicators")
}
```
