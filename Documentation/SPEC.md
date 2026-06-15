# Aria — Product Specification

## Vision
Aria is a premium, desktop-first cognitive workspace that transforms static document storage into a real-time contextual intelligence environment. It bridges the gap between file management and AI-assisted thinking through an interactive two-panel laboratory interface.

## MVP Feature Set

### Core Modules

#### 1. Sources Vault (Left Panel)
- **Document Upload**: Support for PDF, TXT, DOCX, CSV, XLSX, and Markdown files
- **Vault Management**: Drag-and-drop upload, file deletion, rename, and organization
- **Document Parsing**: Automatic text extraction and tokenization on upload
- **Metadata Display**: File name, upload date, word count, and document type icon
- **Quick Search**: Real-time filtering of vault contents by filename or content preview
- **Source Toggling**: Click-to-activate documents for context injection (glow indicator)

#### 2. AI Chat Canvas (Right Panel)
- **Persistent Conversation Thread**: Scrollable message history with user/AI differentiation
- **Rich Message Rendering**: Markdown support, code blocks with syntax highlighting, tables
- **Streaming Responses**: Real-time token-by-token display for API responses
- **Message Actions**: Copy, regenerate, delete, and bookmark individual messages
- **Conversation Management**: New chat, rename, archive, and delete conversation threads

#### 3. @-Mention System (Context Injection)
- **Trigger**: Typing `@` in the message input activates a dynamic file picker dropdown
- **Semantic Hook**: Fuzzy search across vault filenames and content previews
- **Inline Tagging**: Selected files appear as styled chips within the input field
- **Context Binding**: Tagged files are programmatically injected into the system prompt
- **Multi-Source Support**: Allow multiple `@mentions` in a single prompt for cross-document analysis

#### 4. Prompt Input Bar
- **Auto-expanding Textarea**: Grows with content up to a max height
- **Send Shortcuts**: `Enter` to send, `Shift+Enter` for newline
- **Character/Token Counter**: Live count display with context window usage indicator
- **Clear Button**: One-click input clearing

### User Flow

```
1. LAUNCH → Aria opens to a clean two-panel workspace
   ├── Left: Empty Sources Vault with upload CTA
   └── Right: Empty Chat Canvas with welcome message

2. UPLOAD → User drags files into the vault or clicks upload
   ├── File is parsed, tokenized, and stored in local memory
   └── Document appears in vault list with metadata

3. ACTIVATE → User clicks a document to bind it to context
   ├── Document row highlights with electric-blue glow
   └── Status indicator shows "Active Source" in header

4. CHAT → User types a question in the input bar
   ├── Optional: Type `@` to tag specific files inline
   ├── Message + active sources are sent to LLM API
   └── Streaming response appears in chat canvas

5. ITERATE → User continues conversation with full context persistence
   ├── Previous messages maintain source bindings
   └── User can toggle sources on/off mid-conversation
```

### Out-of-Scope for MVP
- Cloud sync / multi-device support
- Collaborative editing or shared workspaces
- Plugin/extension architecture
- Voice input/output
- Image generation or vision model support
- Advanced RAG with vector embeddings (use raw text injection instead)

## Success Metrics
- Sub-2-second document parse time for files under 10MB
- Sub-5-second first token latency for API responses
- @-mention dropdown renders within 100ms of trigger
- Interface maintains 60fps during all interactions
