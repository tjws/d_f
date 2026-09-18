from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dao.admin_tag_dao import AdminTagDAO
from app.models.tag import Tag
from app.models.user import User
from app.schemas.admin_tag import AdminTagCreate, AdminTagUpdate
from app.services.audit_log_service import append_audit_log


admin_tag_dao = AdminTagDAO()


def _read_rows(db: Session) -> list[dict[str, object]]:
    tags, assignments = admin_tag_dao.list_with_assignments(db)
    by_tag: dict[int, list] = defaultdict(list)
    for assignment in assignments:
        by_tag[assignment.tag_id].append(assignment)

    rows = []
    for tag in tags:
        related = by_tag[tag.id]
        rows.append(
            {
                "id": tag.id,
                "key": tag.key,
                "name": tag.name,
                "category": tag.category,
                "description": tag.description,
                "color": tag.color,
                "status": tag.status,
                "assignment_count": len(related),
                "customer_count": len({item.customer_id for item in related}),
                "suggested_count": sum(item.status == "suggested" for item in related),
                "confirmed_count": sum(item.status == "confirmed" for item in related),
                "rejected_count": sum(item.status == "rejected" for item in related),
                "created_at": tag.created_at,
                "updated_at": tag.updated_at,
            }
        )
    return rows


def list_admin_tags(db: Session) -> list[dict[str, object]]:
    return _read_rows(db)


def create_admin_tag(db: Session, actor: User, payload: AdminTagCreate) -> dict[str, object]:
    if admin_tag_dao.get_by_key(db, payload.key) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="标签 key 已存在")
    tag = Tag(**payload.model_dump())
    admin_tag_dao.add(db, tag)
    db.flush()
    append_audit_log(db, actor, "tag.created", "tag", str(tag.id), {"key": tag.key, "name": tag.name})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="标签 key 已存在") from None
    return next(item for item in _read_rows(db) if item["id"] == tag.id)


def update_admin_tag(db: Session, actor: User, tag_id: int, payload: AdminTagUpdate) -> dict[str, object]:
    tag = admin_tag_dao.get_by_id(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
    changes = payload.model_dump(exclude_unset=True)
    if "key" in changes and changes["key"] != tag.key:
        duplicate = admin_tag_dao.get_by_key(db, changes["key"])
        if duplicate is not None and duplicate.id != tag.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="标签 key 已存在")
    before = {field: getattr(tag, field) for field in changes}
    for field, value in changes.items():
        setattr(tag, field, value)
    append_audit_log(db, actor, "tag.updated", "tag", str(tag.id), {"before": before, "after": changes})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="标签更新发生冲突") from None
    return next(item for item in _read_rows(db) if item["id"] == tag.id)
