from aiogram.fsm.state import StatesGroup, State

class MenuStates(StatesGroup):
    main = State()

    orders_list = State()
    order_card = State()

    history_list = State()
    history_card = State()

    promos_list = State()
    promo_create = State()

    cabinet = State()

    categories = State()
    products_list = State()
    product_edit = State()
