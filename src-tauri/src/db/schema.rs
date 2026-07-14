pub const SCHEMA_V1: &str = r#"
CREATE TABLE IF NOT EXISTS settings (
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

CREATE TABLE IF NOT EXISTS peers (
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

CREATE TABLE IF NOT EXISTS conversations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id             INTEGER NOT NULL REFERENCES peers(id) ON DELETE CASCADE,
    unread_count        INTEGER NOT NULL DEFAULT 0,
    last_message_id     INTEGER,
    last_activity       DATETIME,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(peer_id)
);

CREATE TABLE IF NOT EXISTS messages (
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

CREATE TABLE IF NOT EXISTS file_transfers (
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

CREATE TABLE IF NOT EXISTS voice_messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id          INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    duration_ms         INTEGER NOT NULL,                   -- length in milliseconds
    waveform_data       TEXT,                               -- JSON array of amplitude samples for visualization
    playback_position   INTEGER DEFAULT 0,                  -- last playback position (ms)
    is_played           BOOLEAN NOT NULL DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS typing_indicators (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id             INTEGER NOT NULL REFERENCES peers(id) ON DELETE CASCADE,
    conversation_id     INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    is_typing           BOOLEAN NOT NULL DEFAULT 1,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(peer_id, conversation_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_peers_trust ON peers(trust_level);
CREATE INDEX IF NOT EXISTS idx_peers_online ON peers(is_online);
CREATE INDEX IF NOT EXISTS idx_file_transfers_status ON file_transfers(status);
CREATE INDEX IF NOT EXISTS idx_conversations_activity ON conversations(last_activity DESC);
"#;