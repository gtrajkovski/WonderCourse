"""Collaboration API endpoints for roles, invitations, comments, and activity feed."""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from src.collab.decorators import require_permission
from src.collab.models import Role, Collaborator
from src.collab.invitations import Invitation, accept_invitation, validate_invitation_token
from src.collab.permissions import PERMISSIONS, ROLE_TEMPLATES, seed_permissions, get_user_role
from src.collab.comments import Comment, Mention
from src.collab.audit import log_audit_entry, get_activity_feed, AuditEntry, ACTION_COLLABORATOR_JOINED
from src.auth.db import get_db

collab_bp = Blueprint("collab", __name__)
_project_store = None

def init_collab_bp(project_store):
    global _project_store
    _project_store = project_store

# Role Endpoints
@collab_bp.route("/api/courses/<course_id>/roles", methods=["GET"])
@login_required
@require_permission("view_content")
def list_roles(course_id):
    roles = Role.get_for_course(course_id)
    return jsonify([r.to_dict() for r in roles])

@collab_bp.route("/api/courses/<course_id>/roles", methods=["POST"])
@login_required
@require_permission("invite_collaborators")
def create_role(course_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "name" not in data:
        return jsonify({"error": "Missing required field: name"}), 400
    if "permissions" not in data or not isinstance(data["permissions"], list):
        return jsonify({"error": "Missing required field: permissions (array)"}), 400
    role = Role.create(course_id, data["name"], data["permissions"])
    return jsonify(role.to_dict()), 201

@collab_bp.route("/api/courses/<course_id>/roles/from-template", methods=["POST"])
@login_required
@require_permission("invite_collaborators")
def create_role_from_template(course_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "template" not in data:
        return jsonify({"error": "Missing required field: template"}), 400
    template_name = data["template"]
    if template_name not in ROLE_TEMPLATES:
        return jsonify({"error": f"Unknown template: {template_name}"}), 400
    role = Role.create_from_template(course_id, template_name)
    return jsonify(role.to_dict()), 201

@collab_bp.route("/api/courses/<course_id>/roles/<int:role_id>", methods=["DELETE"])
@login_required
@require_permission("invite_collaborators")
def delete_role(course_id, role_id):
    collaborators = Collaborator.get_for_course(course_id)
    for collab in collaborators:
        if collab.role_id == role_id:
            return jsonify({"error": "Cannot delete role that is in use"}), 400
    Role.delete(role_id)
    return "", 204

# Invitation Endpoints
@collab_bp.route("/api/courses/<course_id>/invitations", methods=["POST"])
@login_required
@require_permission("invite_collaborators")
def create_invitation(course_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "role_id" not in data:
        return jsonify({"error": "Missing required field: role_id"}), 400
    invitation = Invitation.create(
        course_id=course_id,
        role_id=data["role_id"],
        invited_by=current_user.id,
        email=data.get("email"),
        expires_in=data.get("expires_in", 604800)
    )
    return jsonify(invitation.to_dict()), 201

@collab_bp.route("/api/courses/<course_id>/invitations", methods=["GET"])
@login_required
@require_permission("invite_collaborators")
def list_invitations(course_id):
    invitations = Invitation.get_for_course(course_id)
    return jsonify([inv.to_dict() for inv in invitations])

@collab_bp.route("/api/courses/<course_id>/invitations/<int:invitation_id>", methods=["DELETE"])
@login_required
@require_permission("invite_collaborators")
def revoke_invitation(course_id, invitation_id):
    Invitation.revoke(invitation_id)
    return "", 204

@collab_bp.route("/api/invitations/<token>/accept", methods=["POST"])
@login_required
def accept_invitation_endpoint(token):
    result = validate_invitation_token(token)
    if not result:
        return jsonify({"error": "Invalid or expired invitation"}), 400
    course_id, role_id = result
    existing = Collaborator.get_by_user_and_course(current_user.id, course_id)
    if existing:
        return jsonify({"error": "Already a collaborator on this course"}), 400
    collaborator = accept_invitation(token, current_user.id)
    if not collaborator:
        return jsonify({"error": "Failed to accept invitation"}), 400
    log_audit_entry(course_id=course_id, user_id=current_user.id,
        action=ACTION_COLLABORATOR_JOINED, entity_type="collaborator", entity_id=str(collaborator["id"]))
    return jsonify(collaborator)

# Collaborator Endpoints
@collab_bp.route("/api/courses/<course_id>/collaborators", methods=["GET"])
@login_required
@require_permission("view_content")
def list_collaborators(course_id):
    collaborators = Collaborator.get_for_course(course_id)
    return jsonify([c.to_dict() for c in collaborators])

@collab_bp.route("/api/courses/<course_id>/collaborators/<int:collaborator_id>", methods=["PUT"])
@login_required
@require_permission("invite_collaborators")
def update_collaborator(course_id, collaborator_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "role_id" not in data:
        return jsonify({"error": "Missing required field: role_id"}), 400
    collaborator = Collaborator.update_role(collaborator_id, data["role_id"])
    if not collaborator:
        return jsonify({"error": "Collaborator not found"}), 404
    return jsonify(collaborator.to_dict())

@collab_bp.route("/api/courses/<course_id>/collaborators/<int:collaborator_id>", methods=["DELETE"])
@login_required
@require_permission("invite_collaborators")
def remove_collaborator(course_id, collaborator_id):
    target = Collaborator.get_by_id(collaborator_id)
    if not target:
        return jsonify({"error": "Collaborator not found"}), 404
    if target.user_id == current_user.id:
        collaborators = Collaborator.get_for_course(course_id)
        owner_count = sum(1 for c in collaborators if c.role_name == "Owner")
        if owner_count <= 1:
            return jsonify({"error": "Cannot remove the only owner"}), 400
    Collaborator.delete(collaborator_id)
    return "", 204

# Permission/Template Info
@collab_bp.route("/api/permissions", methods=["GET"])
def list_permissions():
    return jsonify(PERMISSIONS)

@collab_bp.route("/api/role-templates", methods=["GET"])
def list_role_templates():
    return jsonify(ROLE_TEMPLATES)

# Comment Endpoints
@collab_bp.route("/api/courses/<course_id>/comments", methods=["GET"])
@login_required
@require_permission("view_content")
def get_course_comments(course_id):
    include_resolved = request.args.get("include_resolved", "false").lower() == "true"
    comments = Comment.get_with_replies(course_id, activity_id=None, include_resolved=include_resolved)
    return jsonify([c.to_dict() for c in comments])

@collab_bp.route("/api/courses/<course_id>/comments", methods=["POST"])
@login_required
@require_permission("view_content")
def create_course_comment(course_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "content" not in data:
        return jsonify({"error": "Missing required field: content"}), 400
    parent_id = data.get("parent_id")
    try:
        comment = Comment.create(
            course_id=course_id,
            user_id=current_user.id,
            content=data["content"],
            activity_id=None,
            parent_id=parent_id
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    log_audit_entry(course_id=course_id, user_id=current_user.id,
        action="comment_added", entity_type="comment", entity_id=str(comment.id))
    return jsonify(comment.to_dict()), 201

@collab_bp.route("/api/courses/<course_id>/activities/<activity_id>/comments", methods=["GET"])
@login_required
@require_permission("view_content")
def get_activity_comments(course_id, activity_id):
    include_resolved = request.args.get("include_resolved", "false").lower() == "true"
    comments = Comment.get_with_replies(course_id, activity_id=activity_id, include_resolved=include_resolved)
    return jsonify([c.to_dict() for c in comments])

@collab_bp.route("/api/courses/<course_id>/activities/<activity_id>/comments", methods=["POST"])
@login_required
@require_permission("view_content")
def create_activity_comment(course_id, activity_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "content" not in data:
        return jsonify({"error": "Missing required field: content"}), 400
    parent_id = data.get("parent_id")
    try:
        comment = Comment.create(
            course_id=course_id,
            user_id=current_user.id,
            content=data["content"],
            activity_id=activity_id,
            parent_id=parent_id
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    log_audit_entry(course_id=course_id, user_id=current_user.id,
        action="comment_added", entity_type="comment", entity_id=str(comment.id))
    return jsonify(comment.to_dict()), 201

@collab_bp.route("/api/courses/<course_id>/comments/<int:comment_id>", methods=["PUT"])
@login_required
def update_comment(course_id, comment_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "content" not in data:
        return jsonify({"error": "Missing required field: content"}), 400
    comment = Comment.get_by_id(comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404
    user_role = get_user_role(current_user.id, course_id)
    if comment.user_id != current_user.id and user_role != "Owner":
        return jsonify({"error": "Permission denied"}), 403
    updated = Comment.update(comment_id, data["content"])
    return jsonify(updated.to_dict())

@collab_bp.route("/api/courses/<course_id>/comments/<int:comment_id>/resolve", methods=["POST"])
@login_required
@require_permission("view_content")
def resolve_comment(course_id, comment_id):
    Comment.resolve(comment_id)
    log_audit_entry(course_id=course_id, user_id=current_user.id,
        action="comment_resolved", entity_type="comment", entity_id=str(comment_id))
    return jsonify({"status": "resolved"})

@collab_bp.route("/api/courses/<course_id>/comments/<int:comment_id>/unresolve", methods=["POST"])
@login_required
@require_permission("view_content")
def unresolve_comment(course_id, comment_id):
    Comment.unresolve(comment_id)
    return jsonify({"status": "unresolved"})

@collab_bp.route("/api/courses/<course_id>/comments/<int:comment_id>", methods=["DELETE"])
@login_required
def delete_comment(course_id, comment_id):
    comment = Comment.get_by_id(comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404
    user_role = get_user_role(current_user.id, course_id)
    if comment.user_id != current_user.id and user_role != "Owner":
        return jsonify({"error": "Permission denied"}), 403
    Comment.delete(comment_id)
    return "", 204

# Notification Endpoints (Mentions)
@collab_bp.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    mentions = Mention.get_unread_for_user(current_user.id)
    notifications = []
    for mention in mentions:
        comment = Comment.get_by_id(mention.comment_id)
        notifications.append({
            "id": mention.id,
            "comment_id": mention.comment_id,
            "course_id": comment.course_id if comment else None,
            "activity_id": comment.activity_id if comment else None,
            "comment_content": comment.content if comment else None,
            "comment_author": comment.author_name if comment else None,
            "created_at": mention.created_at.isoformat() if mention.created_at else None,
        })
    return jsonify(notifications)

@collab_bp.route("/api/notifications/<int:mention_id>/read", methods=["POST"])
@login_required
def mark_notification_read(mention_id):
    Mention.mark_read(mention_id)
    return "", 204

@collab_bp.route("/api/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    mentions = Mention.get_unread_for_user(current_user.id)
    count = len(mentions)
    Mention.mark_all_read(current_user.id)
    return jsonify({"marked_read": count})

# Activity Feed Endpoint
@collab_bp.route("/api/courses/<course_id>/activity", methods=["GET"])
@login_required
@require_permission("view_content")
def get_course_activity_feed(course_id):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    limit = min(limit, 100)
    feed = get_activity_feed(course_id, limit=limit + 1, offset=offset)
    has_more = len(feed) > limit
    if has_more:
        feed = feed[:limit]
    return jsonify({"feed": feed, "limit": limit, "offset": offset, "has_more": has_more})
