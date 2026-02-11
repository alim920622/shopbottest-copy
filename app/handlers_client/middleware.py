from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db.database import Database
from app.repositories.client_profiles_repo import ClientProfilesRepo


class ClientLocaleMiddleware(BaseMiddleware):
    """Кладёт locale клиента в контекст обработчиков и FSM state."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        db = data.get("db")
        event_from_user = getattr(event, "from_user", None)
        if isinstance(db, Database) and event_from_user is not None:
            user_id = int(event_from_user.id)
            repo = ClientProfilesRepo(db)
            locale = await repo.get_locale(user_id)
            data["locale"] = locale
            state = data.get("state")
            if state is not None:
                await state.update_data(user_id=user_id, locale=locale)
        return await handler(event, data)
