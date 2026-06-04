from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CompanyInfo(Base):
    __tablename__ = "company_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_zh: Mapped[str | None] = mapped_column(String(100))
    name_en: Mapped[str | None] = mapped_column(String(100))
    address_zh: Mapped[str | None] = mapped_column(String(255))
    address_en: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    fax: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(100))
    mobile: Mapped[str | None] = mapped_column(String(50))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    bank_name_full: Mapped[str | None] = mapped_column(String(200))
    bank_code: Mapped[str | None] = mapped_column(String(20))
    bank_address: Mapped[str | None] = mapped_column(String(500))
    bank_account: Mapped[str | None] = mapped_column(String(100))
    swift_code: Mapped[str | None] = mapped_column(String(20))
    logo_path: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
