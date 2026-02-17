---
phase: 10
plan: 01
subsystem: collaboration
tags: [roles, permissions, rbac, database, models]

# Dependency graph
requires:
  - 09-07  # User authentication system for user table FK
provides:
  - collaboration-data-layer
  - permission-system
  - role-templates
affects:
  - 10-02  # Invitation system will use roles
  - 10-03  # Access control middleware will check permissions
  - 11-01  # Activity tracking will link to collaborators

# Tech tracking
tech-stack:
  added:
    - jsondiff>=2.2.0  # For audit trail in future plans
  patterns:
    - "Role-based access control (RBAC) with course-scoped roles"
    - "Many-to-many role-permission mapping via junction table"
    - "Direct SQL queries for collaboration models (no ORM)"

# File tracking
key-files:
  created:
    - src/collab/__init__.py
    - src/collab/permissions.py
    - src/collab/models.py
  modified:
    - instance/schema.sql
    - requirements.txt

# Decisions
decisions:
  - code: "13-permission-codes"
    impact: "All course operations covered by granular permissions"
    rationale: "Balances granularity with usability - enough to enforce least privilege without overwhelming users"
  - code: "course-scoped-roles"
    impact: "Roles belong to specific courses, not global"
    rationale: "Different courses need different collaboration structures; avoids permission sprawl"
  - code: "4-role-templates"
    impact: "Predefined Owner/Designer/Reviewer/SME templates"
    rationale: "Common collaboration patterns ready out-of-box while allowing custom roles"
  - code: "unique-user-per-course"
    impact: "One role per user per course (UNIQUE constraint)"
    rationale: "Simplifies permission checks and prevents conflicting role assignments"

# Metrics
duration: 271s
completed: 2026-02-10
---

# Phase 10 Plan 01: Collaboration Data Models Summary

**One-liner:** Role-based access control foundation with 13 granular permissions, 4 predefined templates, and course-scoped role management

## What Was Built

Created the data layer for multi-user course collaboration with role-based access control:

**Database schema (instance/schema.sql):**
- `course_role` table: Custom per-course roles with unique course_id + name constraint
- `permission` table: 13 granular permission codes across 3 categories
- `role_permission` junction: Many-to-many mapping with CASCADE delete
- `collaborator` table: User-course-role links with invitation tracking
- Index on `collaborator.course_id` for fast course-based queries

**Permission system (src/collab/permissions.py):**
- 13 permissions in 3 categories:
  - Content: view, edit, delete, generate, approve (5)
  - Structure: add, reorder, delete, manage outcomes (4)
  - Course: invite collaborators, export, publish, delete (4)
- 4 role templates:
  - Owner: All 13 permissions
  - Designer: 7 permissions (content creation + structure)
  - Reviewer: 3 permissions (view + approve + export)
  - SME: 2 permissions (view + export only)
- Helper functions: `has_permission()`, `get_user_permissions()`, `get_user_role()`, `seed_permissions()`

**Data models (src/collab/models.py):**
- `Role` class: CRUD for course-specific roles with permission sets
  - `create_from_template()` for instant role setup from templates
  - `get_for_course()` to list all roles on a course
- `Collaborator` class: CRUD for user-course-role relationships
  - `get_by_user_and_course()` for permission checks
  - `update_role()` to change collaborator permissions
  - Joins with user and role tables for complete context

**Key design patterns:**
- Direct SQL queries (no ORM) for consistency with existing codebase
- `get_db()` from `src.auth.db` for request-scoped connections
- Cascade deletes protect referential integrity
- `to_dict()` methods for API serialization
- Class methods for all database operations (stateless model pattern)

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Extend database schema | 056a66d | instance/schema.sql |
| 2 | Create permission definitions | ac0cee9 | src/collab/__init__.py, src/collab/permissions.py |
| 3 | Create collaboration models | f341134 | src/collab/models.py, requirements.txt |

## Verification Results

All verification criteria met:

- ✅ Schema creates all 4 tables with correct relationships
- ✅ Permission definitions cover all 13 codes in 3 categories
- ✅ Role templates match phase context (Owner/Designer/Reviewer/SME)
- ✅ Models support CRUD operations with proper joins
- ✅ `has_permission` function queries database correctly
- ✅ `jsondiff>=2.2.0` added to requirements.txt

## Decisions Made

**13 permission codes organized by category:**
Chose content (5), structure (4), course (4) breakdown to cover all collaboration needs while keeping permission checks simple. Each permission maps to clear actions users can/can't take.

**Course-scoped roles instead of global roles:**
Roles belong to specific courses (UNIQUE constraint on course_id + name). This allows different collaboration structures per course and prevents permission sprawl as the system scales.

**4 predefined role templates:**
Established Owner (full control), Designer (content creation), Reviewer (approval workflow), SME (consultant/advisor) as starting templates. Covers 80% of collaboration patterns while allowing custom roles for edge cases.

**One role per user per course:**
UNIQUE constraint on (course_id, user_id) in collaborator table. Simplifies permission checks (no role priority logic needed) and prevents conflicting role assignments.

**Junction table for role-permission mapping:**
Many-to-many design allows flexible permission sets without hardcoding. Supports both templates and custom roles. CASCADE delete ensures cleanup when roles removed.

## Deviations from Plan

None - plan executed exactly as written.

## Technical Notes

**Permission check query performance:**
`has_permission()` uses 3-table join (collaborator → role_permission → permission). Index on `collaborator.course_id` makes this fast for typical use case (checking permissions for current course).

**Role template instantiation:**
`create_from_template()` looks up permission IDs by code during role creation, then inserts junction records. Idempotent `seed_permissions()` ensures permission table populated before first role created.

**Model pattern consistency:**
Followed existing codebase pattern from `src.auth.models.User`: class methods for database operations, instance methods for serialization, no ORM. All queries use `get_db()` for request-scoped connections.

**Future audit trail foundation:**
Added `jsondiff>=2.2.0` to support role change tracking in later plans. Will enable "who changed what permissions when" audit log.

## Integration Points

**Database initialization:**
`seed_permissions()` should be called during `flask init-db` to populate permission table with all 13 codes.

**User model:**
Foreign keys from `collaborator` table to `user.id` for user_id and invited_by columns.

**Course data:**
`course_id` columns reference course data from `src.core.project_store.ProjectStore` (JSON files, not database).

**Authentication:**
Uses `get_db()` from `src.auth.db` for database access within Flask request context.

## Next Phase Readiness

**Blockers:** None

**Concerns:**
- Permission seeding needs to happen before roles can be created
- No migration system yet - schema changes require manual database recreation

**Recommendations:**
- Add `seed_permissions()` call to `flask init-db` command
- Consider adding database migration tool (e.g., Alembic) in future phase
- May want permission caching for high-traffic scenarios (not needed yet)

**What's ready for next plans:**
- ✅ Role and Collaborator models ready for invitation system (10-02)
- ✅ Permission infrastructure ready for access control middleware (10-03)
- ✅ Database schema supports audit trail (10-04)

## Key Files Reference

**src/collab/permissions.py (176 lines)**
- Exports: `PERMISSIONS`, `ROLE_TEMPLATES`, `has_permission`, `get_user_permissions`, `get_user_role`, `seed_permissions`
- Defines all permission codes and role templates
- Permission check queries for access control

**src/collab/models.py (406 lines)**
- Exports: `Role`, `Collaborator`
- Full CRUD operations for both models
- Template support for instant role creation
- JOIN queries for complete context in serialization

**instance/schema.sql**
- 4 new tables: `course_role`, `permission`, `role_permission`, `collaborator`
- Foreign key constraints with CASCADE deletes
- UNIQUE constraints for data integrity
- Index on `collaborator.course_id` for query performance
