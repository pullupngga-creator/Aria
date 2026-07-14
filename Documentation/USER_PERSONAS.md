# USER_PERSONAS.md — Aria

## Persona 1: "The Office Collaborator"

**Name**: Priya
**Age**: 31
**Role**: Product Manager at a tech startup
**Tech Comfort**: Medium-High
**Primary Device**: MacBook Air (M2), office Wi-Fi

### Goals
- Quickly share mockups, PRDs, and spreadsheets with designers and engineers in the same office
- Avoid Slack/file-sharing bloat for simple "here's the latest" exchanges
- Keep sensitive product docs off cloud servers (pre-launch confidentiality)
- Send quick voice notes instead of scheduling another meeting

### Pain Points
- Slack file uploads have size limits and compression
- AirDrop works but is unreliable with mixed Mac/Windows teams
- Email feels too formal for quick internal shares
- Cloud drives require login, sync, and create version chaos

### How Aria Helps
- Zero setup: opens app, sees team members auto-discovered
- Direct file send at full LAN speed (no upload bottleneck)
- Voice messages for async updates without typing long explanations
- No cloud = no data leaves the building

### Typical Session
1. Opens Aria in the morning, sees 6 teammates online
2. Drops a Figma export into the design lead's chat
3. Sends a 2-minute voice note explaining feedback
4. Receives a revised PDF back in under 10 seconds
5. Closes laptop — no sync, no cloud cleanup

---

## Persona 2: "The Classroom Educator"

**Name**: Marcus
**Age**: 45
**Role**: High school computer science teacher
**Tech Comfort**: Medium
**Primary Device**: Windows laptop, school Wi-Fi (filtered, no cloud access)

### Goals
- Distribute code examples and assignment files to students during class
- Collect student projects without USB drives or email attachments
- Work within strict school network policies (no Google Drive, no Dropbox)
- Keep student data local and private (FERPA compliance)

### Pain Points
- School Wi-Fi blocks most cloud services
- USB drives are slow, unreliable, and a security risk
- Email is cumbersome for 30 students × 4 classes
- No budget for institutional file-sharing software

### How Aria Helps
- Works entirely on the local network — no internet required
- Auto-discovers all student laptops in the classroom
- Batch-send files to multiple peers (post-MVP group feature; MVP = one-to-one repeated)
- No accounts, no passwords, no IT approval needed

### Typical Session
1. Students open Aria at the start of class
2. Marcus sees all 28 student devices appear in the peer list
3. Sends the day's starter code to each student individually
4. Students work, then send completed assignments back
5. Marcus has all files in his Downloads folder by end of period

---

## Persona 3: "The Co-Working Nomad"

**Name**: Sasha
**Age**: 26
**Role**: Freelance graphic designer
**Tech Comfort**: High
**Primary Device**: Custom Linux workstation, various co-working spaces

### Goals
- Share large design files (PSDs, AI files, 500MB+ renders) with clients in the same co-working space
- Avoid uploading massive files to WeTransfer or Dropbox on slow shared Wi-Fi
- Maintain privacy — client work must not touch public cloud
- Work across Linux, Mac, and Windows clients seamlessly

### Pain Points
- WeTransfer is slow on shared Wi-Fi and has expiration limits
- Dropbox/Google Drive sync eats bandwidth and storage
- AirDrop doesn't work with Linux or Windows
- Most P2P tools are either too technical (CLI) or too sketchy (adware)

### How Aria Helps
- Cross-platform native desktop app (Tauri/Rust)
- Direct LAN transfer at full Wi-Fi speed (no internet bottleneck)
- No file size limits, no expiration, no compression
- Clean, professional UI that clients trust

### Typical Session
1. Sasha and client both open Aria on the co-working Wi-Fi
2. Sasha drags a 1.2GB render into the chat
3. Transfer completes in 90 seconds at 110 MB/s
4. Client opens file directly from Downloads
5. No upload queue, no email link, no "file expired" message

---

## Persona 4: "The Privacy-First Professional"

**Name**: Dr. Elena Voss
**Age**: 52
**Role**: Medical researcher, handles sensitive patient data
**Tech Comfort**: Medium
**Primary Device**: Windows desktop, hospital LAN (air-gapped from internet)

### Goals
- Exchange de-identified research datasets with colleagues on the same hospital floor
- Guarantee zero data leakage to external servers (HIPAA compliance)
- Avoid any cloud service due to institutional policy
- Simple enough that non-technical colleagues can use it without training

### Pain Points
- Hospital network is isolated from the internet
- Most communication tools require cloud connectivity
- IT department is slow to approve new software
- Colleagues are not technically savvy — needs to "just work"

### How Aria Helps
- Pure local network — zero external connectivity
- No accounts, no cloud, no data leaves the LAN
- Auto-discovery means colleagues don't need to type IP addresses
- Simple three-pane UI with minimal cognitive load

### Typical Session
1. Opens Aria on the research floor LAN
2. Sees 3 colleagues' devices auto-discovered
3. Sends a dataset file to the biostatistician
4. Receives a confirmation voice note back
5. IT audit log shows only local traffic — compliance satisfied

---

## Anti-Personas (Who This Is NOT For)
- **Remote teams**: Needs internet relay or central server → Slack, Discord, Zoom
- **Users wanting cloud backup**: Aria is local-only, no sync across devices → Dropbox, iCloud
- **Users needing group chat**: MVP is one-to-one only → WhatsApp, Telegram
- **Users on mobile**: Aria is desktop-first → AirDrop, Nearby Share
