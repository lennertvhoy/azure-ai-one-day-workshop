# Ideas / Backlog

## TUI app: create Azure “desktops” for participants (IaC)
**Idea:** Build a terminal UI (TUI) that can provision per-participant Azure dev environments (“Azure desktops”) for this workshop session using Infrastructure-as-Code.

### Goal
- One command/TUI flow to create, track, and tear down environments for N participants.

### Options
- **Bicep** (Azure-native)
  - Pros: no Terraform state headaches; best Azure integration
  - Cons: fewer multi-cloud patterns
- **Terraform**
  - Pros: very common in enterprise; strong ecosystem
  - Cons: state management; credential complexity

### What an “Azure desktop” could mean
Pick one pattern:
- **Azure Virtual Desktop (AVD)** pooled host pool + per-user assignment
- **Dev Box** (if available) per user
- **Plain VM** per participant (fast + cheap + simple)
- **Container-based dev env** (ACA/AKS) + VS Code Server

### MVP scope (recommended)
- Provision per participant:
  - Resource group
  - Web App + Key Vault + AI Search + (optional) AOAI (if quota allows)
  - Optional Ubuntu VM with cloud-init for tooling
- Generate an output table: participant → endpoints → teardown command

### TUI features
- Import participant list (CSV)
- Preview plan (cost + counts)
- Apply / Destroy
- Progress view (per participant)

### Notes / Risks
- AOAI access/quota may block per-participant provisioning; may need shared AOAI.
- AVD/Dev Box may require extra licensing/admin readiness.
