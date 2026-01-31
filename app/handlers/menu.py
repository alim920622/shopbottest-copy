from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from app.states import MenuStates
from app.keyboards import kb_main, kb_back

router = Router()

@router.callback_query(F.data == "m:orders")
async def go_orders(cq: CallbackQuery, state: FSMContext, auth_role: str):
    if auth_role == "none":
        await cq.answer("Нет доступа", show_alert=True); return
    await state.set_state(MenuStates.orders_list)
    await cq.message.edit_text("Текущие заказы (заглушка).", reply_markup=kb_back("main"))
    await cq.answer()

@router.callback_query(F.data == "m:history")
async def go_history(cq: CallbackQuery, state: FSMContext, auth_role: str):
    if auth_role == "none":
        await cq.answer("Нет доступа", show_alert=True); return
    await state.set_state(MenuStates.history_list)
    await cq.message.edit_text("История заказов (заглушка).", reply_markup=kb_back("main"))
    await cq.answer()

@router.callback_query(F.data == "m:promos")
async def go_promos(cq: CallbackQuery, state: FSMContext, auth_role: str):
    if auth_role == "none":
        await cq.answer("Нет доступа", show_alert=True); return
    await state.set_state(MenuStates.promos_list)
    await cq.message.edit_text("Акции (заглушка).", reply_markup=kb_back("main"))
    await cq.answer()

@router.callback_query(F.data == "m:cabinet")
async def go_cabinet(cq: CallbackQuery, state: FSMContext, auth_role: str):
    if auth_role == "none":
        await cq.answer("Нет доступа", show_alert=True); return
    await state.set_state(MenuStates.cabinet)
    await cq.message.edit_text(
        "Кабинет магазина (только просмотр).\n"
        "Телефон/Адрес/Лого/О компании (заглушка).",
        reply_markup=kb_back("main")
    )
    await cq.answer()

@router.callback_query(F.data == "m:products")
async def go_products(cq: CallbackQuery, state: FSMContext, auth_role: str):
    if auth_role == "none":
        await cq.answer("Нет доступа", show_alert=True); return
    await state.set_state(MenuStates.categories)
    await cq.message.edit_text(
        "Категории (заглушка): Овощи, Фрукты, Кондитерские, Молочные, Сладости ...",
        reply_markup=kb_back("main")
    )
    await cq.answer()

@router.callback_query(F.data.startswith("back:"))
async def back_handler(cq: CallbackQuery, state: FSMContext):
    target = cq.data.split(":", 1)[1]

    if target == "main":
        await state.set_state(MenuStates.main)
        await cq.message.edit_text("Главное меню:", reply_markup=kb_main())
        await cq.answer()
        return

    await cq.answer("Неизвестный переход", show_alert=True)
