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
    trust_mode          TEXT DEFAULT 'manual',              -- 'manual' | 'auto'
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
    network_interface   TEXT,                               -- subnet for network change detection
    UNIQUE(public_key)
);

CREATE TABLE IF NOT EXISTS messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id          TEXT UNIQUE NOT NULL,               -- UUID
    peer_fingerprint    TEXT NOT NULL,                      -- peer fingerprint (FK to peers.fingerprint)
    direction           TEXT NOT NULL,                      -- 'sent' | 'received'
    content             TEXT NOT NULL,                      -- text body OR JSON metadata for file/voice
    timestamp           INTEGER NOT NULL,                   -- unix timestamp (seconds)
    reply_to            TEXT,                               -- message_id being replied to
    status              TEXT DEFAULT 'pending',             -- 'pending' | 'sent' | 'delivered' | 'read' | 'failed'
    FOREIGN KEY (peer_fingerprint) REFERENCES peers(fingerprint)
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
    peer_fingerprint    TEXT NOT NULL REFERENCES peers(fingerprint) ON DELETE CASCADE,
    is_typing           BOOLEAN NOT NULL DEFAULT 1,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(peer_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_messages_peer ON messages(peer_fingerprint);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_peers_trust ON peers(trust_level);
CREATE INDEX IF NOT EXISTS idx_peers_online ON peers(is_online);
CREATE INDEX IF NOT EXISTS idx_peers_network ON peers(network_interface);
CREATE INDEX IF NOT EXISTS idx_file_transfers_status ON file_transfers(status);
"#;
