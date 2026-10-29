from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """The base of the tables of the settings store. The migrations make the same tables."""
