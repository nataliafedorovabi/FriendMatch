from __future__ import annotations

from typing import Any
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from sqlalchemy import select, delete

from .config import get_settings
from .db import get_session
from .models import User, ProfileAnswer, GuessAnswer
from .questions import QUESTIONS, get_question_key, get_question_text


logger = logging.getLogger(__name__)
settings = get_settings()
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
# Enable FSM storage (in-memory). For production scaling, switch to RedisStorage later.
dp = Dispatcher(storage=MemoryStorage())
router = Router()


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    logger.info("/ping from chat_id=%s user_id=%s", message.chat.id, message.from_user.id)
    await message.answer("pong")


class FillProfile(StatesGroup):
    waiting_answer = State()


class GuessProfile(StatesGroup):
    waiting_guess = State()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext) -> None:
    logger.info("/start entered chat_id=%s user_id=%s args=%s", message.chat.id, message.from_user.id, command.args)
    args = (command.args or "").strip()

    try:
        async with get_session() as session:
            user = await session.scalar(select(User).where(User.tg_id == message.from_user.id))
            if not user:
                user = User(
                    tg_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                )
                session.add(user)
                await session.commit()
    except Exception as e:
        logger.warning("DB unavailable on /start, continuing without persisting user: %s", e)

    if args.startswith("guess_"):
        target_tg_id_str = args.removeprefix("guess_")
        if not target_tg_id_str.isdigit():
            await message.answer("Неверная ссылка. Попроси подругу прислать новую.")
            return
        await state.clear()
        await state.update_data(target_tg_id=int(target_tg_id_str), idx=0, guesses={})
        await message.answer("Играем! Я покажу вопросы, а ты угадывай ответы подруги.")
        await ask_next_guess_question(message, state)
        return

    await state.clear()
    await state.update_data(idx=0, answers={})
    await message.answer(
        "Привет! Заполним твою анкету. Отвечай искренне — потом подруга попробует угадать!"
    )
    await ask_next_profile_question(message, state)


async def ask_next_profile_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    idx: int = int(data.get("idx", 0))
    logger.info("ask_next_profile_question idx=%s chat_id=%s", idx, message.chat.id)
    if idx >= len(QUESTIONS):
        await save_profile_answers(message, state)
        link = f"https://t.me/{settings.BOT_USERNAME}?start=guess_{message.from_user.id}"
        await message.answer(
            "Готово! Отправь эту ссылку подруге, пусть попробует угадать твои ответы:\n" + link
        )
        await state.clear()
        return

    await message.answer(f"Вопрос {idx + 1}. {get_question_text(idx)}")
    await state.set_state(FillProfile.waiting_answer)
    logger.info("state set -> FillProfile.waiting_answer chat_id=%s", message.chat.id)


@router.message(StateFilter(FillProfile.waiting_answer))
async def on_profile_answer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    idx: int = int(data.get("idx", 0))
    logger.info("on_profile_answer idx=%s chat_id=%s text=%s", idx, message.chat.id, message.text)
    answers: dict[str, str] = dict(data.get("answers", {}))
    answers[get_question_key(idx)] = (message.text or "").strip()
    await state.update_data(answers=answers, idx=idx + 1)
    await ask_next_profile_question(message, state)


async def save_profile_answers(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    answers: dict[str, str] = dict(data.get("answers", {}))

    try:
        async with get_session() as session:
            user = await session.scalar(select(User).where(User.tg_id == message.from_user.id))
            if user:
                await session.execute(
                    delete(ProfileAnswer).where(ProfileAnswer.owner_user_id == user.id)
                )
                for key, value in answers.items():
                    session.add(ProfileAnswer(owner_user_id=user.id, question_key=key, answer_text=value))
                await session.commit()
            else:
                logger.info("User not found when saving profile answers; skipping persist")
    except Exception as e:
        logger.warning("DB unavailable when saving profile answers; proceeding without persist: %s", e)


async def ask_next_guess_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    idx: int = int(data.get("idx", 0))
    logger.info("ask_next_guess_question idx=%s chat_id=%s", idx, message.chat.id)
    if idx >= len(QUESTIONS):
        await finish_guessing_and_score(message, state)
        await state.clear()
        return

    await message.answer(f"Угадай: {get_question_text(idx)}")
    await state.set_state(GuessProfile.waiting_guess)
    logger.info("state set -> GuessProfile.waiting_guess chat_id=%s", message.chat.id)


@router.message(StateFilter(GuessProfile.waiting_guess))
async def on_guess_answer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    idx: int = int(data.get("idx", 0))
    logger.info("on_guess_answer idx=%s chat_id=%s text=%s", idx, message.chat.id, message.text)
    guesses: dict[str, str] = dict(data.get("guesses", {}))
    guesses[get_question_key(idx)] = (message.text or "").strip()
    await state.update_data(guesses=guesses, idx=idx + 1)
    await ask_next_guess_question(message, state)


@router.message()
async def fallback_log(message: Message, state: FSMContext) -> None:
    # Log unmatched messages with current FSM state for diagnostics
    try:
        current = await state.get_state()
    except Exception:
        current = None
    logger.info("fallback_log: unmatched message chat_id=%s text=%s state=%s", message.chat.id, message.text, current)


async def finish_guessing_and_score(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    target_tg_id: int = int(data.get("target_tg_id", 0))
    guesses: dict[str, str] = dict(data.get("guesses", {}))

    try:
        async with get_session() as session:
            owner = await session.scalar(select(User).where(User.tg_id == target_tg_id))
            guesser = await session.scalar(select(User).where(User.tg_id == message.from_user.id))
            if not owner:
                await message.answer("Не нашла анкету подруги. Пусть она сначала заполнит её.")
                return
            if not guesser:
                await message.answer("Обнови /start и попробуй снова.")
                return
            owner_answers = {
                pa.question_key: pa.answer_text for pa in (await session.scalars(select(ProfileAnswer).where(ProfileAnswer.owner_user_id == owner.id))).all()
            }
            for key, value in guesses.items():
                session.add(
                    GuessAnswer(
                        owner_user_id=owner.id,
                        guesser_user_id=guesser.id,
                        question_key=key,
                        guessed_answer_text=value,
                    )
                )
            await session.commit()
    except Exception as e:
        logger.warning("DB unavailable when scoring guesses: %s", e)
        await message.answer("Сейчас недоступно вычислить совпадения (БД). Попробуйте позже.")
        return

    total = len(QUESTIONS)
    matches = 0
    for q in QUESTIONS:
        key = q["key"]
        real = (owner_answers.get(key, "") or "").strip().lower()
        guessed = (guesses.get(key, "") or "").strip().lower()
        if real and guessed and real == guessed:
            matches += 1

    percent = int(round((matches / max(total, 1)) * 100))
    comment = fun_comment(percent)
    await message.answer(
        f"Совпадений: {matches}/{total} — {percent}%\n{comment}"
    )


def fun_comment(percent: int) -> str:
    if percent >= 90:
        return "Вы — одно целое! 💞"
    if percent >= 70:
        return "Вы знаете друг друга почти идеально! ✨"
    if percent >= 50:
        return "Очень неплохо! Ещё чуть-чуть — и будет топ! 😊"
    if percent >= 30:
        return "Есть над чем посмеяться и что обсудить! 😄"
    return "Главное — дружить и узнавать друг друга! 💖"


dp.include_router(router)
