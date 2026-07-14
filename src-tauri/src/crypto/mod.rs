use ed25519_dalek::SigningKey;
use keyring::Entry;
use rand::rngs::OsRng;
use sha2::{Digest, Sha256};
use std::sync::Arc;
use anyhow::Context;

pub struct Identity {
    pub signing_key: SigningKey,
    pub public_key_hex: String,
    pub fingerprint: String,
}

pub fn init() -> Result<Arc<Identity>, anyhow::Error> {
    let entry = Entry::new("aria_identity", "user")
        .context("Failed to initialize keyring entry")?;

    let signing_key = match entry.get_password() {
        Ok(encoded_key) => {
            let bytes = hex::decode(&encoded_key)
                .context("Failed to decode private key from hex")?;
            let array: [u8; 32] = bytes.try_into()
                .map_err(|_| anyhow::anyhow!("Invalid private key length stored in keyring"))?;
            SigningKey::from_bytes(&array)
        }
        Err(keyring::Error::NoEntry) => {
            let mut csprng = OsRng;
            let key = SigningKey::generate(&mut csprng);
            let encoded_key = hex::encode(key.to_bytes());
            entry.set_password(&encoded_key)
                .context("Failed to save generated private key to keychain")?;
            key
        }
        Err(e) => return Err(e).context("Keychain access error"),
    };

    let verifying_key = signing_key.verifying_key();
    let public_key_hex = hex::encode(verifying_key.as_bytes());

    let mut hasher = Sha256::new();
    hasher.update(verifying_key.as_bytes());
    let hash = hasher.finalize();
    // Use first 4 bytes (8 hex characters) for the short, human-readable fingerprint
    let fingerprint = hex::encode(&hash[..4]);

    Ok(Arc::new(Identity {
        signing_key,
        public_key_hex,
        fingerprint,
    }))
}

#[derive(serde::Serialize, specta::Type)]
pub struct IdentityInfo {
    pub public_key: String,
    pub fingerprint: String,
}

#[tauri::command]
#[specta::specta]
pub fn get_my_identity(state: tauri::State<'_, crate::AppState>) -> IdentityInfo {
    IdentityInfo {
        public_key: state.identity.public_key_hex.clone(),
        fingerprint: state.identity.fingerprint.clone(),
    }
}
