from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.sales_script_dao import SalesScriptDAO
from app.models.sales_script import SalesScript
from app.models.user import User
from app.schemas.sales_script import SalesScriptCreate, SalesScriptUpdate
from app.services.audit_log_service import append_audit_log


script_dao = SalesScriptDAO()
VALID_TRANSITIONS = {"draft": {"pending_review", "disabled"}, "pending_review": {"draft", "published", "disabled"}, "published": {"disabled", "draft"}, "disabled": {"draft"}}


def list_scripts(db: Session) -> list[SalesScript]:
    return script_dao.list_all(db)


def to_script_read(script: SalesScript) -> dict[str, object]:
    return {"id": script.id, "scene": script.scene, "customer_stage": script.customer_stage, "objection_type": script.objection_type, "title": script.title, "content": script.content, "tone": script.tone, "status": script.status, "version": script.version, "created_by": script.created_by, "approved_by": script.approved_by, "created_at": script.created_at, "updated_at": script.updated_at}


def create_script(db: Session, actor: User, payload: SalesScriptCreate) -> SalesScript:
    script = SalesScript(**payload.model_dump(), status="draft", version=1, created_by=actor.id)
    script_dao.add(db, script)
    db.flush()
    append_audit_log(db, actor, "sales_script.created", "sales_script", str(script.id), {"title": script.title, "status": script.status})
    db.commit(); db.refresh(script)
    return script


def update_script(db: Session, script_id: int, actor: User, payload: SalesScriptUpdate) -> SalesScript:
    script = script_dao.get_by_id(db, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="话术不存在")
    changes = payload.model_dump(exclude_unset=True)
    new_status = changes.pop("status", None)
    if new_status is not None and new_status != script.status and new_status not in VALID_TRANSITIONS.get(script.status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"话术不能从 {script.status} 变更为 {new_status}")
    content_changed = any(field in changes for field in ("scene", "customer_stage", "objection_type", "title", "content", "tone"))
    for field, value in changes.items():
        setattr(script, field, value)
    if content_changed:
        script.version += 1
        if script.status == "published":
            script.status = "draft"
            script.approved_by = None
    if new_status is not None:
        script.status = new_status
        if new_status == "published":
            script.approved_by = actor.id
    append_audit_log(db, actor, "sales_script.updated", "sales_script", str(script.id), {"status": script.status, "version": script.version})
    db.commit(); db.refresh(script)
    return script
