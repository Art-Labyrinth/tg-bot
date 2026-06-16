"""Echo stub for any text.

THIS is the future entry point into the neural-network conversation. For now it
just repeats the text back. Once the AI layer exists, replace the body with a
call to the response-generation service (e.g. app/services/ai.py), passing the
text and the dialog context from FSM.
"""
from aiogram import F, Router
from aiogram.types import Message

from app.db.models.user import User
from app.i18n import t

router = Router(name="echo")


@router.message(F.text)
async def echo_text(message: Message, user: User) -> None:
    await message.answer(t("error.unknown", user.locale))
