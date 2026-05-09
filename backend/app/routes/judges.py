"""Judge routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.db import get_db
from app.models.judge import Judge
from app.schemas.judge import JudgeCreate, JudgeOut
from app.services import judge as svc

router = APIRouter(tags=["judges"])


@router.post(
    "/tournaments/{tournament_id}/judges",
    status_code=status.HTTP_201_CREATED,
    response_model=JudgeOut,
)
def create_judge(
    tournament_id: UUID,
    body: JudgeCreate,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> Judge:
    return svc.create_judge(
        db, tournament_id, body, actor_id=admin.user_id, actor_email=admin.email
    )


@router.get("/tournaments/{tournament_id}/judges", response_model=list[JudgeOut])
def list_judges(
    tournament_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[Judge]:
    return svc.list_judges(db, tournament_id)


@router.delete("/judges/{judge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_judge(
    judge_id: UUID,
    admin: AdminUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    svc.delete_judge(db, judge_id, actor_id=admin.user_id, actor_email=admin.email)
