from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from veil.adapters.postgres.orm.base import Base


class SettingRow(Base):
    """One value of one setting in one scope. The scope is `org` or `repo:owner/name`.

    The migrations hold the checks and the triggers: the type, the bounds, the secret refusal and the copy of
    the type and the bounds from the org row to a repo row. This class describes the columns and the key.
    """

    __tablename__ = "settings"
    scope: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    min_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
