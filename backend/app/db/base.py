from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All SQLAlchemy models must inherit from this Base."""

    pass
