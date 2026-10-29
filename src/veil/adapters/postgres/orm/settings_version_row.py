from sqlalchemy import BigInteger, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column

from veil.adapters.postgres.orm.base import Base


class SettingsVersionRow(Base):
    """The one row that counts the changes of the settings. A snapshot carries this number.

    The cache of a Shell uses it in its key, so a write makes the old entry stale at once.
    """

    __tablename__ = "settings_version"
    id: Mapped[bool] = mapped_column(
        Boolean, primary_key=True, server_default=text("true")
    )
    version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
