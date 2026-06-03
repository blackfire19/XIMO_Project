from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)     # CI / PL
    version: Mapped[str] = mapped_column(String(10), nullable=False)      # customer / internal
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    generated_at: Mapped[str] = mapped_column(server_default="NOW()")


class OrderAttachment(Base):
    __tablename__ = "order_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)     # MTC / CO / export_license / customs / other
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[str] = mapped_column(server_default="NOW()")
