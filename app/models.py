from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    first_name: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    profile_answers: Mapped[list["ProfileAnswer"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    guesses_made: Mapped[list["GuessAnswer"]] = relationship(back_populates="guesser", foreign_keys=lambda: GuessAnswer.guesser_user_id)
    guesses_received: Mapped[list["GuessAnswer"]] = relationship(back_populates="owner", foreign_keys=lambda: GuessAnswer.owner_user_id)


class ProfileAnswer(Base):
    __tablename__ = "profile_answers"
    __table_args__ = (UniqueConstraint("owner_user_id", "question_key", name="uq_owner_question"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question_key: Mapped[str]
    answer_text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    owner: Mapped[User] = relationship(back_populates="profile_answers")


class GuessAnswer(Base):
    __tablename__ = "guess_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    guesser_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_key: Mapped[str]
    guessed_answer_text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)

    owner: Mapped[User] = relationship(back_populates="guesses_received", foreign_keys=[owner_user_id])
    guesser: Mapped[User] = relationship(back_populates="guesses_made", foreign_keys=[guesser_user_id])
