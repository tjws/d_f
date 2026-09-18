from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.customer_transfer_dao import CustomerTransferDAO
from app.dao.user_dao import UserDAO
from app.models.customer_transfer import CustomerTransfer
from app.models.user import User
from app.schemas.customer_transfer import CustomerTransferCreate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404


transfer_dao = CustomerTransferDAO()
user_dao = UserDAO()


def transfer_customer(db: Session, customer_id: int, current_user: User, payload: CustomerTransferCreate) -> CustomerTransfer:
    customer = get_customer_or_404(db, customer_id, current_user, "transfer")
    target = user_dao.get_by_id(db, payload.to_user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目标用户不存在或已停用")
    if target.id == customer.owner_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="客户已经归属于该用户")
    if current_user.role == "manager" and target.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="经理只能转移给同组织用户")

    transfer = CustomerTransfer(
        customer_id=customer.id,
        from_user_id=customer.owner_id,
        to_user_id=target.id,
        operator_id=current_user.id,
        reason=payload.reason,
        snapshot_json={"before": {"owner_id": customer.owner_id}, "after": {"owner_id": target.id}},
    )
    customer.owner_id = target.id
    transfer_dao.add(db, transfer)
    append_audit_log(db, current_user, "customer.transferred", "customer", str(customer.id), {"from_user_id": transfer.from_user_id, "to_user_id": target.id, "reason": payload.reason})
    # 客户归属、转移历史和审计日志共用一次提交，避免出现半成功状态。
    db.commit()
    db.refresh(transfer)
    return transfer


def list_customer_transfers(db: Session, customer_id: int, current_user: User) -> list[CustomerTransfer]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return transfer_dao.list_by_customer(db, customer_id)
