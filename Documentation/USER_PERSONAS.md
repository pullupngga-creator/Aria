# Aria — User Personas

## Primary Personas

---

### Persona: Dr. Elena Vasquez
**The Research Academic**

| Attribute | Detail |
|-----------|--------|
| **Age** | 34 |
| **Role** | Postdoctoral researcher in computational linguistics |
| **Location** | Barcelona, Spain |
| **Tech Comfort** | High — uses Python, LaTeX, Zotero daily |

**Context**:
Elena manages 40–60 PDFs per research project. She currently uses a combination of Zotero for storage, Obsidian for notes, and ChatGPT for synthesis. The friction of copy-pasting excerpts between tools costs her 2–3 hours per week. She needs to cross-reference findings across multiple papers without losing the thread of her argument.

**Goals**:
- Upload a batch of papers and query them as a unified corpus
- Extract specific methodological comparisons across studies
- Maintain a persistent "conversation" with her literature that evolves as she reads more
- Export synthesized findings into her LaTeX workflow

**Pain Points**:
- "I paste the same paper excerpts into ChatGPT five times a day"
- "I forget which sources I already fed to the model"
- "Context windows are too small for my 80-page methodology reviews"

**How Aria Helps**:
- Sources Vault acts as her persistent paper library
- @-mention lets her isolate specific studies for methodological comparison
- Gemini's 1M token context handles her longest review documents
- Conversation history preserves her analytical thread across sessions

**Quote**: *"I don't want another tool. I want one tool that finally understands my research is a conversation, not a filing cabinet."*

---

### Persona: Marcus Chen
**The Technical Strategist**

| Attribute | Detail |
|-----------|--------|
| **Age** | 41 |
| **Role** | Principal at a boutique technology strategy consultancy |
| **Location** | Singapore |
| **Tech Comfort** | Very High — former software engineer, builds internal tools |

**Context**:
Marcus advises Fortune 500 companies on AI adoption. Each engagement generates 10–15 deliverables: market analysis PDFs, competitor spreadsheets, technical architecture documents, and interview transcripts. He synthesizes these into board-ready strategy memos. Currently, he uses a mix of Notion, Excel, and Claude — but the context switching destroys his flow state.

**Goals**:
- Bind all engagement documents to a single AI context for holistic analysis
- Run "what-if" scenarios across financial models and technical roadmaps simultaneously
- Generate executive summaries that cite specific source documents
- Maintain client confidentiality (no cloud document storage beyond API calls)

**Pain Points**:
- "I have 12 tabs open and I still can't find the right spreadsheet cell"
- "My assistant spends hours formatting source citations in my memos"
- "I need to know exactly which document each insight came from"

**How Aria Helps**:
- Local-first document storage satisfies client confidentiality requirements
- @-mention enables precise citations: "Compare the revenue model in @q3_financials.xlsx with @competitor_analysis.pdf"
- Active source binding keeps his current engagement documents always in context
- Markdown export preserves formatting for memo generation

**Quote**: *"My clients pay for clarity. I need a tool that thinks as fast as I do, but never forgets the source."*

---

### Persona: Sarah Okafor
**The Non-Fiction Writer**

| Attribute | Detail |
|-----------|--------|
| **Age** | 29 |
| **Role** | Independent journalist and essayist |
| **Location** | Lagos, Nigeria / Remote |
| **Tech Comfort** | Medium — proficient with Scrivener, Google Docs, basic automation |

**Context**:
Sarah writes long-form investigative pieces requiring deep research across primary sources, interview transcripts, and historical documents. Her current workflow involves Scrivener for drafting, Google Docs for collaboration, and a messy folder of PDFs and audio transcripts. She often loses track of which source contains which quote.

**Goals**:
- Organize hundreds of source documents by project/topic
- Query her research archive for specific quotes, facts, and connections
- Maintain narrative voice while leveraging AI for structural suggestions
- Keep her research portable (works from coffee shops, co-working spaces, home)

**Pain Points**:
- "I know I read that quote somewhere, but I can't remember which PDF"
- "AI suggestions feel generic because it doesn't know my sources"
- "I need to see my sources and my writing at the same time"

**How Aria Helps**:
- Two-panel layout mirrors her natural workflow (research on left, writing on right)
- @-mention lets her pull exact quotes without leaving the chat
- Conversation threads become her "research notebooks" — searchable, persistent
- Dark theme reduces eye strain during late-night writing sessions

**Quote**: *"Writing is thinking. Aria lets me think with my entire research library open beside me."*

---

## Secondary Personas

### Persona: David Park
**The Solo Founder**
- Builds MVPs alone, needs to digest technical documentation quickly
- Uses Aria to parse API docs, GitHub readmes, and competitor landing pages
- Values speed over depth — wants answers in seconds, not minutes

### Persona: Dr. Amara Singh
**The Policy Analyst**
- Works with legislative text, statistical reports, and stakeholder submissions
- Needs to compare policy language across jurisdictions
- Requires audit trails for every AI-generated insight

---

## Anti-Personas (Not the Target)

| Persona | Why Not |
|---------|---------|
| Casual ChatGPT users | Aria is document-centric; overkill for simple Q&A |
| Mobile-first users | Desktop-first design; no mobile app in MVP |
| Teams needing real-time collaboration | No multi-user support; single-player focus |
| Users wanting image/video analysis | Text-only document support in MVP |
| Non-technical users afraid of API keys | Requires manual API key configuration |

---

## Persona-Driven Feature Priorities

| Feature | Elena | Marcus | Sarah | Priority |
|---------|-------|--------|-------|----------|
| Large context windows | Critical | Critical | High | P0 |
| @-mention precision | High | Critical | High | P0 |
| Local document storage | Medium | Critical | Medium | P0 |
| Markdown export | High | High | Medium | P1 |
| Conversation persistence | High | Medium | High | P0 |
| Dark theme | Medium | Low | High | P1 |
| Citation tracking | Critical | Critical | Medium | P1 |
| Batch upload | High | High | Low | P1 |
