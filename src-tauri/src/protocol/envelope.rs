use serde::{Deserialize, Serialize};
use ed25519_dalek::{Verifier, Signature, VerifyingKey, Signer};
use base64::Engine;
use crate::crypto::Identity;

/// Message type identifiers
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum MessageType {
    Handshake,
    Message,
    FileOffer,
    FileChunk,
    FileComplete,
    Voice,
    Heartbeat,
    Typing,
}

/// Wire protocol envelope - the outer wrapper for all P2P messages
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Envelope {
    pub version: u8,
    #[serde(rename = "type")]
    pub message_type: MessageType,
    pub sender: String, // Ed25519 public key fingerprint
    pub payload: serde_json::Value,
    pub timestamp: i64, // Unix timestamp in seconds
    pub signature: String, // Base64-encoded Ed25519 signature
}

impl Envelope {
    /// Create a new envelope and sign it with our identity
    pub fn new(
        message_type: MessageType,
        sender_fingerprint: String,
        payload: serde_json::Value,
        identity: &Identity,
    ) -> Self {
        let timestamp = chrono::Utc::now().timestamp();
        let mut envelope = Self {
            version: 1,
            message_type,
            sender: sender_fingerprint,
            payload,
            timestamp,
            signature: String::new(),
        };

        // Sign the envelope (excluding signature field)
        envelope.signature = envelope.sign(identity);
        envelope
    }

    /// Serialize envelope to JSON bytes for transmission
    pub fn to_bytes(&self) -> anyhow::Result<Vec<u8>> {
        serde_json::to_vec(self).map_err(Into::into)
    }

    /// Deserialize envelope from JSON bytes
    pub fn from_bytes(bytes: &[u8]) -> anyhow::Result<Self> {
        serde_json::from_slice(bytes).map_err(Into::into)
    }

    /// Sign the envelope payload (version + type + sender + payload + timestamp)
    fn sign(&self, identity: &Identity) -> String {
        let data = self.signing_data();
        let signature = identity.signing_key.sign(&data);
        base64::engine::general_purpose::STANDARD.encode(signature.to_bytes())
    }

    /// Verify the envelope signature using the sender's public key
    pub fn verify(&self, public_key: &VerifyingKey) -> anyhow::Result<()> {
        let data = self.signing_data();
        let sig_bytes = base64::engine::general_purpose::STANDARD.decode(&self.signature)?;
        let signature = Signature::from_slice(&sig_bytes)?;

        public_key
            .verify(&data, &signature)
            .map_err(|e| anyhow::anyhow!("Signature verification failed: {}", e))
    }

    /// Get the bytes that should be signed/verified
    fn signing_data(&self) -> Vec<u8> {
        // Create a canonical representation for signing
        let sign_obj = serde_json::json!({
            "version": self.version,
            "type": self.message_type,
            "sender": self.sender,
            "payload": self.payload,
            "timestamp": self.timestamp,
        });
        serde_json::to_vec(&sign_obj).unwrap_or_default()
    }

    /// Check if timestamp is within acceptable drift (5 minutes)
    pub fn is_timestamp_valid(&self) -> bool {
        let now = chrono::Utc::now().timestamp();
        let diff = (now - self.timestamp).abs();
        diff < 300 // 5 minutes = 300 seconds
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_envelope_serialization() {
        let envelope = Envelope {
            version: 1,
            message_type: MessageType::Heartbeat,
            sender: "test_fp".to_string(),
            payload: serde_json::json!({}),
            timestamp: 1234567890,
            signature: "dummy_sig".to_string(),
        };
        let bytes = envelope.to_bytes().unwrap();
        let decoded = Envelope::from_bytes(&bytes).unwrap();
        assert_eq!(decoded.message_type, MessageType::Heartbeat);
    }

    #[test]
    fn test_timestamp_validation() {
        let now = chrono::Utc::now().timestamp();
        let valid = Envelope {
            version: 1,
            message_type: MessageType::Heartbeat,
            sender: "test".to_string(),
            payload: serde_json::json!({}),
            timestamp: now,
            signature: "sig".to_string(),
        };
        assert!(valid.is_timestamp_valid());

        let invalid = Envelope {
            timestamp: now - 400, // > 5 minutes ago
            ..valid
        };
        assert!(!invalid.is_timestamp_valid());
    }
}
