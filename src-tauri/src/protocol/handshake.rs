use crate::protocol::{Envelope, MessageType};
use serde::{Deserialize, Serialize};

/// Handshake payload exchanged during peer connection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakePayload {
    pub version: u8,
    pub public_key: String, // Ed25519 public key hex
    pub fingerprint: String,
    pub display_name: Option<String>,
    pub timestamp: i64,
}

impl HandshakePayload {
    /// Create a new handshake payload from our identity
    pub fn from_identity(
        public_key_hex: String,
        fingerprint: String,
        display_name: Option<String>,
    ) -> Self {
        Self {
            version: 1,
            public_key: public_key_hex,
            fingerprint,
            display_name,
            timestamp: chrono::Utc::now().timestamp(),
        }
    }

    /// Wrap this payload in a signed envelope
    pub fn to_envelope(self, identity: &crate::crypto::Identity) -> Envelope {
        let payload = serde_json::to_value(self).unwrap();
        Envelope::new(
            MessageType::Handshake,
            identity.fingerprint.clone(),
            payload,
            identity,
        )
    }

    /// Extract handshake payload from an envelope
    pub fn from_envelope(envelope: &Envelope) -> anyhow::Result<Self> {
        serde_json::from_value(envelope.payload.clone()).map_err(Into::into)
    }

    /// Check if timestamp is within acceptable drift (30 seconds for handshake)
    pub fn is_timestamp_valid(&self) -> bool {
        let now = chrono::Utc::now().timestamp();
        let diff = (now - self.timestamp).abs();
        diff < 30 // 30 seconds
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_handshake_serialization() {
        let payload = HandshakePayload {
            version: 1,
            public_key: "test_key".to_string(),
            fingerprint: "test_fp".to_string(),
            display_name: Some("Test User".to_string()),
            timestamp: 1234567890,
        };
        let json = serde_json::to_value(&payload).unwrap();
        let decoded = HandshakePayload::from_envelope(&Envelope {
            version: 1,
            message_type: MessageType::Handshake,
            sender: "test_fp".to_string(),
            payload: json,
            timestamp: 1234567890,
            signature: "sig".to_string(),
        })
        .unwrap();
        assert_eq!(decoded.fingerprint, "test_fp");
    }
}
