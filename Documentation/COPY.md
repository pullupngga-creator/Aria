# Aria — Copy & Content

## Brand Voice

**Tone**: Confident, precise, quietly luxurious. Aria speaks like a brilliant research partner who never wastes words. No exclamation points. No filler. Every sentence earns its place.

**Principles**:
- Use active voice
- Prefer concrete over abstract
- Avoid buzzwords ("leverage", "synergize", "unlock")
- Technical accuracy without jargon
- Respect the user's intelligence

---

## Brand Name
**Aria** — From the Italian for "air" and the musical term for a solo vocal piece. Evokes clarity, breath, and singular focus.

---

## Taglines

### Primary
> "Your documents. Your context. One mind."

### Secondary
> "A laboratory for thought."
> "Where documents become dialogue."
> "The thinking environment."

### Empty States
> "No sources yet. Drop a file to begin."
> "Start a conversation. Your sources are listening."
> "Upload research. Ask questions. Think deeper."

---

## Page Headers & Navigation

### Sources Vault Header
- **Title**: "Sources Vault"
- **Subtitle**: "Active documents bind to your context automatically"
- **Upload Button**: "Add Source" (tooltip: "Upload PDF, DOCX, CSV, TXT, or Markdown")
- **Search Placeholder**: "Search sources..."

### Chat Canvas Header
- **Default Title**: "New Conversation"
- **Model Selector Label**: "Model"
- **New Chat Button**: "New Chat" (tooltip: "Start a fresh conversation")
- **Archive Button**: "Archive" (tooltip: "Move to archived conversations")

### Input Bar
- **Placeholder (no sources)**: "Ask anything..."
- **Placeholder (with active sources)**: "Ask about your {N} active sources..."
- **Placeholder (with @mention)**: "Ask about @{filename}..."
- **Token Counter Label**: "{used} / {limit} tokens"
- **Send Button Tooltip**: "Send message (Enter)"

---

## Onboarding

### Welcome Screen (First Launch)

**Headline**: "Welcome to Aria"
**Body**: "Aria is a cognitive workspace for researchers, writers, and strategists. Upload documents to your Sources Vault, then converse with them directly. Use @ to reference specific files inline."

**Steps**:
1. **Upload** — "Drop PDFs, Word docs, spreadsheets, or text files into your Sources Vault."
2. **Activate** — "Click any document to bind it to your active context."
3. **Converse** — "Type a question. Use @ to mention specific sources. Aria responds with full context."

**CTA**: "Upload Your First Source" / "Skip for now"

---

## Error Messages

### Document Errors
- **Parse Failed**: "Could not extract text from `{filename}`. The file may be corrupted or password-protected."
- **File Too Large**: "`{filename}` exceeds the 50MB limit. Consider splitting the document."
- **Unsupported Type**: "`{filename}` is not a supported format. Use PDF, DOCX, CSV, XLSX, MD, or TXT."
- **Duplicate File**: "`{filename}` already exists in your vault."

### API Errors
- **No API Key**: "Add your API key in Settings to start chatting."
- **Rate Limited**: "Rate limit reached. Waiting {seconds} seconds before retrying..."
- **Context Too Long**: "The active sources exceed the model's context window. Deselect some documents or use @mentions for specific files."
- **API Unavailable**: "{Provider} is temporarily unavailable. Switch models in the header or try again shortly."

### General Errors
- **Unknown Error**: "Something went wrong. If this persists, restart Aria."
- **Disk Full**: "Your storage is full. Delete old conversations or sources to free space."

---

## Success Messages

- **Upload Complete**: "`{filename}` added to vault. {word_count} words extracted."
- **Source Activated**: "`{filename}` is now active. {token_count} tokens bound to context."
- **Conversation Saved**: "Conversation archived."
- **Settings Saved**: "Settings updated."

---

## Settings Panel

### Section: API Keys
- **Header**: "API Configuration"
- **Gemini Key Label**: "Google Gemini API Key"
- **Claude Key Label**: "Anthropic Claude API Key"
- **Helper Text**: "Your keys are stored locally and never transmitted to our servers."
- **Validate Button**: "Test Connection"

### Section: Preferences
- **Header**: "Preferences"
- **Default Model Label**: "Default Model"
- **Max Sources Label**: "Maximum Active Sources"
- **Max Sources Helper**: "Limit how many documents can be active simultaneously to manage token usage."
- **Auto-Save Label**: "Auto-save Interval"
- **Auto-Save Helper**: "How often to save conversation state to disk."

### Section: Data
- **Header**: "Data Management"
- **Export Label**: "Export Conversations"
- **Export Button**: "Export as JSON"
- **Clear Vault Label**: "Clear Sources Vault"
- **Clear Vault Button**: "Delete All Sources"
- **Clear Vault Warning**: "This permanently deletes all uploaded documents and cannot be undone."

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + N` | New conversation |
| `Cmd/Ctrl + Shift + A` | Toggle all sources active/inactive |
| `Cmd/Ctrl + F` | Focus vault search |
| `Cmd/Ctrl + ,` | Open settings |
| `Escape` | Close dropdowns, cancel streaming |
| `Enter` | Send message (when input focused) |
| `Shift + Enter` | New line in input |
| `@` | Trigger @-mention dropdown |
| `↑` (in empty input) | Recall last message for editing |

---

## Microcopy

### Tooltips
- **Copy message**: "Copy to clipboard"
- **Regenerate**: "Regenerate response"
- **Delete message**: "Delete message"
- **Bookmark**: "Save to bookmarks"
- **Source glow indicator**: "Active — bound to context"
- **Token warning**: "Approaching context limit"

### Status Indicators
- **Parsing**: "Extracting text..."
- **Streaming**: "Thinking..."
- **Saving**: "Saving..."
- **Indexing**: "Building search index..."

### Time Formatting
- `< 1 min`: "Just now"
- `< 1 hour`: "{N}m ago"
- `< 24 hours`: "{N}h ago"
- `≥ 24 hours`: "{Month} {Day}"
- `≥ 1 year`: "{Month} {Day}, {Year}"
