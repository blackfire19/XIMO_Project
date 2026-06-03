from sqlalchemy import Boolean, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    trade_terms: Mapped[str | None] = mapped_column(String(50))
    payment_terms: Mapped[str | None] = mapped_column(String(100))
    grade: Mapped[str] = mapped_column(String(10), default="potential", nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    follow_freq: Mapped[str] = mapped_column(String(10), default="daily", nullable=False)
    follow_freq_updated_at: Mapped[str] = mapped_column(String, nullable=False)
    consecutive_miss_cycles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])  # type: ignore
    follow_up_records: Mapped[list["FollowUpRecord"]] = relationship(back_populates="customer")


class FollowUpRecord(Base):
    __tablename__ = "follow_up_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_effective: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="follow_up_records")
    images: Mapped[list["FollowUpImage"]] = relationship(back_populates="follow_up", cascade="all, delete-orphan")


class FollowUpImage(Base):
    __tablename__ = "follow_up_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    follow_up_id: Mapped[int] = mapped_column(ForeignKey("follow_up_records.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[str] = mapped_column(String, nullable=False)

    follow_up: Mapped[FollowUpRecord] = relationship(back_populates="images")
