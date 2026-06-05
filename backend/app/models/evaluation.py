from sqlalchemy import Integer, String, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 10", name="ck_evaluation_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 评价人（boss / super_admin）
    evaluator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # 被评价员工
    subject_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # 业务单据类型：followup / inquiry / formal_order
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    evaluator: Mapped["User"] = relationship(foreign_keys=[evaluator_id])  # type: ignore
    subject: Mapped["User"] = relationship(foreign_keys=[subject_id])  # type: ignore
