"""Model re-exports.

Import every model here so that Alembic and SQLAlchemy "see" them during
migration autogeneration (a model just needs to be imported at least once).
"""
from app.db.models.issued_ticket import IssuedTicket
from app.db.models.user import User
from app.db.models.user_history import UserEvent, UserHistory

__all__ = ["User", "UserHistory", "UserEvent", "IssuedTicket"]
