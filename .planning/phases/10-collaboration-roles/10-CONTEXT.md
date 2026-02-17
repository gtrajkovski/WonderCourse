# Phase 10: Collaboration & Roles - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable course owners to invite collaborators with role-based permissions, supporting team-based course development with commenting and audit trails. Users can create custom roles with granular permissions, invite collaborators via email or shareable links, add threaded comments with @mentions, and view comprehensive audit history of all changes.

</domain>

<decisions>
## Implementation Decisions

### Role Definitions
- Custom roles supported with granular permissions
- 4 predefined role templates (Owner, Designer, Reviewer, SME) that can be cloned and modified
- Roles defined per-course, not globally
- Full permission granularity across three levels:
  - **Content-level:** View, Edit content, Delete content, Generate content, Approve content
  - **Structure-level:** Add modules/lessons, Reorder structure, Delete structure, Manage outcomes
  - **Course-level:** Invite collaborators, Export course, Publish course, Delete course
- Permissions enforced at both API level (security) and UI level (hide/disable unavailable features)

### Invitation Flow
- Both email invites and shareable links supported
- Configurable expiry with 7-day default (owner can set custom or no expiry)
- Invitees without accounts are prompted to register, then auto-join the course
- Shareable links can be revoked independently

### Commenting System
- Single-level threading (comments can have replies, replies cannot have replies)
- Comments can be marked as resolved (hidden but not deleted)
- @mentions supported to notify specific collaborators
- Comments trigger notifications to mentioned users

### Audit Trail
- Track everything: content, structure, collaborator changes, exports, state transitions
- Retain history forever (as long as course exists)
- Store before/after diffs for content changes
- All collaborators can view the audit trail

### Claude's Discretion
- Single owner vs multiple owners per course (recommend single for simplicity)
- Whether collaborators can see other collaborators (recommend full visibility)
- Revocation behavior (recommend immediate removal)
- Accept/decline vs accept/ignore for invitations (recommend simpler accept/ignore)
- Comment attachment level (recommend activity-level primarily, with course-level for general discussions)

</decisions>

<specifics>
## Specific Ideas

No specific product references mentioned. Open to standard collaboration patterns used in tools like Google Docs, Notion, or Figma.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-collaboration-roles*
*Context gathered: 2026-02-07*
