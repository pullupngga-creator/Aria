use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Message payload for text chat
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessagePayload {
    pub message_id: String, // UUID
    pub content: String,
    pub timestamp: i32,           // Changed to i32 for Specta compatibility
    pub reply_to: Option<String>, // message_id being replied to
}

impl MessagePayload {
    /// Create a new message payload
    pub fn new(content: String, reply_to: Option<String>) -> Self {
        Self {
            message_id: Uuid::new_v4().to_string(),
            content,
            timestamp: chrono::Utc::now().timestamp() as i32,
            reply_to,
        }
    }

    /// Extract message payload from an envelope
    pub fn from_envelope(envelope: &crate::protocol::Envelope) -> anyhow::Result<Self> {
        serde_json::from_value(envelope.payload.clone()).map_err(Into::into)
    }
}

/// Delivery receipt payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReceiptPayload {
    pub message_id: String,
    pub timestamp: i64,
    pub status: String, // "delivered", "read"
}

impl ReceiptPayload {
    pub fn new(message_id: String, status: String) -> Self {
        Self {
            message_id,
            timestamp: chrono::Utc::now().timestamp(),
            status,
        }
    }

    /// Extract receipt payload from an envelope
    pub fn from_envelope(envelope: &crate::protocol::Envelope) -> anyhow::Result<Self> {
        serde_json::from_value(envelope.payload.clone()).map_err(Into::into)
    }
}

/// Typing indicator payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypingPayload {
    pub is_typing: bool,
    pub timestamp: i32,
}

impl TypingPayload {
    pub fn new(is_typing: bool) -> Self {
        Self {
            is_typing,
            timestamp: chrono::Utc::now().timestamp() as i32,
        }
    }

    /// Extract typing payload from an envelope
    pub fn from_envelope(envelope: &crate::protocol::Envelope) -> anyhow::Result<Self> {
        serde_json::from_value(envelope.payload.clone()).map_err(Into::into)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_creation() {
        let msg = MessagePayload::new("Hello".to_string(), None);
        assert!(!msg.message_id.is_empty());
        assert_eq!(msg.content, "Hello");
    }
}
