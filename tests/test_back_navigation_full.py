import asyncio
import tempfile
from pathlib import Path

from app.db.database import Database, DBConfig
from app.repositories.shops_repo import ShopsRepo
from app.repositories.categories_repo import CategoriesRepo
from app.repositories.products_repo import ProductsRepo
from app.repositories.cart_repo import CartRepo
from app.repositories.orders_repo import OrdersRepo
from app.repositories.promotions_repo import PromotionsRepo
from app.repositories.chat_repo import ChatRepo

from app.handlers_client import catalog as client_catalog
from app.handlers_admin_shop import orders as admin_shop_orders
from app.handlers_admin_shop import extra as admin_shop_extra
from app.handlers_admin_shop import chat as admin_shop_chat

from app.handlers_admin_restaurant import orders as admin_rest_orders
from app.handlers_admin_restaurant import extra as admin_rest_extra
from app.handlers_admin_restaurant import products as admin_rest_products


# -------------------------
# Minimal fakes for aiogram
# -------------------------
class FakeUser:
    def __init__(self, user_id: int):
        self.id = user_id


class FakeBot:
    async def send_message(self, user_id: int, text: str, reply_markup=None):
        return


class FakeMessage:
    def __init__(self):
        self.text = None
        self.reply_markup = None
        self.history = []  # list[(text, reply_markup)]

    async def edit_text(self, text: str, reply_markup=None):
        self.text = text
        self.reply_markup = reply_markup
        self.history.append((text, reply_markup))
        return self


class FakeCallbackQuery:
    def __init__(self, data: str, user_id: int, message: FakeMessage):
        self.data = data
        self.from_user = FakeUser(user_id)
        self.message = message
        self.bot = FakeBot()
        self._answers = []

    async def answer(self, text: str | None = None, show_alert: bool = False):
        self._answers.append((text, show_alert))
        return


class FakeFSMContext:
    def __init__(self):
        self._data = {}
        self._state = None

    async def set_state(self, state):
        self._state = state

    async def clear(self):
        self._data = {}
        self._state = None

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def get_data(self):
        return dict(self._data)


# -------------------------
# Seed helpers
# -------------------------
async def _seed_base(db: Database, user_id: int) -> dict:
    shops = ShopsRepo(db)
    cats = CategoriesRepo(db)
    products = ProductsRepo(db)
    cart = CartRepo(db)

    shop_id = await shops.create_shop("Shop A", "shop")
    rest_id = await shops.create_shop("Rest A", "restaurant")

    shop_cat = await cats.create(shop_id, "Молочка")
    rest_cat = await cats.create(rest_id, "Салаты")

    milk_id = await products.create(shop_id, shop_cat, "Молоко", 50.0, "Свежее")
    salad_id = await products.create(rest_id, rest_cat, "Салат", 30.0, "Овощной")

    await cart.add(user_id=user_id, product_id=milk_id, qty=1)
    await cart.add(user_id=user_id, product_id=salad_id, qty=1)

    return {
        "shop_id": shop_id,
        "rest_id": rest_id,
        "shop_cat": shop_cat,
        "rest_cat": rest_cat,
        "milk_id": milk_id,
        "salad_id": salad_id,
    }


async def _seed_shop_order_and_chat(db: Database, user_id: int, shop_id: int) -> int:
    orders = OrdersRepo(db)
    order_id = await orders.create_order_from_cart(shop_id=shop_id, client_user_id=user_id)

    chat = ChatRepo(db)
    await chat.add_message(order_id, sender_user_id=user_id, sender_role="client", message_text="Привет")
    await chat.add_message(order_id, sender_user_id=999, sender_role="admin", message_text="Здравствуйте")
    return order_id


async def _seed_promo(db: Database, shop_id: int, title="Скидка 10%") -> int:
    promos = PromotionsRepo(db)
    return await promos.create(shop_id=shop_id, title=title, description="Тестовая акция")


async def _grant_admin(db: Database, user_id: int, shop_id: int) -> None:
    async with db.conn() as conn:
        await conn.execute(
            "INSERT INTO shop_admins(user_id, shop_id) VALUES (?, ?)",
            (user_id, shop_id),
        )
        await conn.commit()


# -------------------------
# CLIENT tests (core back targets)
# -------------------------
def test_client_back_main_from_anywhere():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            user_id = 1101
            ids = await _seed_base(db, user_id)

            state = FakeFSMContext()
            msg = FakeMessage()

            # Go to shops list then back to main
            cq_shops = FakeCallbackQuery("c:shops", user_id, msg)
            await client_catalog.list_shops(cq_shops, db, state)
            assert msg.text == "Выберите магазин:"

            cq_back_main = FakeCallbackQuery("c:back:main", user_id, msg)
            await client_catalog.back(cq_back_main, db, state)
            assert msg.text == "Выберите раздел:"

    asyncio.run(_run())


def test_client_back_order_menu():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            user_id = 1102
            await _seed_base(db, user_id)

            state = FakeFSMContext()
            msg = FakeMessage()

            # From anywhere -> order menu
            cq_back_order = FakeCallbackQuery("c:back:order_menu", user_id, msg)
            await client_catalog.back(cq_back_order, db, state)
            assert msg.text == "Что будем заказывать?"

    asyncio.run(_run())


def test_client_back_cart_menu():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            user_id = 1103
            await _seed_base(db, user_id)

            state = FakeFSMContext()
            msg = FakeMessage()

            cq_back_cart_menu = FakeCallbackQuery("c:back:cart_menu", user_id, msg)
            await client_catalog.back(cq_back_cart_menu, db, state)
            assert msg.text == "Выберите корзину:"

    asyncio.run(_run())


# -------------------------
# ADMIN SHOP tests
# -------------------------
def test_admin_shop_back_from_orders_list_to_main():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 2201
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["shop_id"])
            await _seed_shop_order_and_chat(db, user_id=admin_id, shop_id=base["shop_id"])

            msg = FakeMessage()

            cq_orders = FakeCallbackQuery("a:orders", admin_id, msg)
            await admin_shop_orders.list_orders(cq_orders, db)
            assert "Текущие заказы" in (msg.text or "")

            cq_back = FakeCallbackQuery("a:back:main", admin_id, msg)
            await admin_shop_orders.back_main(cq_back)
            assert msg.text == "Админ-меню магазина:"

    asyncio.run(_run())


def test_admin_shop_back_from_order_card_to_orders_list():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 2202
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["shop_id"])
            order_id = await _seed_shop_order_and_chat(db, user_id=admin_id, shop_id=base["shop_id"])

            msg = FakeMessage()

            cq_card = FakeCallbackQuery(f"a:order:{order_id}", admin_id, msg)
            await admin_shop_orders.order_card(cq_card, db)
            assert f"Заказ #{order_id}" in (msg.text or "")

            cq_back = FakeCallbackQuery("a:orders", admin_id, msg)
            await admin_shop_orders.list_orders(cq_back, db)
            assert "Текущие заказы" in (msg.text or "")

    asyncio.run(_run())


def test_admin_shop_promos_back_to_promos_list():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 2203
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["shop_id"])
            promo_id = await _seed_promo(db, shop_id=base["shop_id"])

            state = FakeFSMContext()
            msg = FakeMessage()

            cq_promos = FakeCallbackQuery("a:promos", admin_id, msg)
            await admin_shop_extra.promos(cq_promos, db)
            assert "Акции" in (msg.text or "")

            cq_card = FakeCallbackQuery(f"a:promo:{promo_id}", admin_id, msg)
            await admin_shop_extra.promo_card(cq_card, db, state)
            assert "Акция" in (msg.text or "")

            cq_back = FakeCallbackQuery("a:promos", admin_id, msg)
            await admin_shop_extra.promos(cq_back, db)
            assert "Акции" in (msg.text or "")

    asyncio.run(_run())


def test_admin_shop_chat_back_to_chat_list():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 2204
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["shop_id"])
            order_id = await _seed_shop_order_and_chat(db, user_id=admin_id, shop_id=base["shop_id"])

            msg = FakeMessage()

            cq_list = FakeCallbackQuery("a:chat", admin_id, msg)
            await admin_shop_chat.chat_list(cq_list, db)
            assert "Чаты" in (msg.text or "")

            cq_open = FakeCallbackQuery(f"a:chat:{order_id}", admin_id, msg)
            await admin_shop_chat.open_chat(cq_open, db)
            assert f"Чат по заказу #{order_id}" in (msg.text or "")

            cq_back = FakeCallbackQuery("a:chat", admin_id, msg)
            await admin_shop_chat.chat_list(cq_back, db)
            assert "Чаты" in (msg.text or "")

    asyncio.run(_run())


# -------------------------
# ADMIN RESTAURANT tests
# -------------------------
def test_admin_restaurant_back_from_orders_list_to_main():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 3301
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["rest_id"])
            # create an order for restaurant too (use cart for rest shop_id)
            await _seed_shop_order_and_chat(db, user_id=admin_id, shop_id=base["rest_id"])

            msg = FakeMessage()

            cq_orders = FakeCallbackQuery("r:orders", admin_id, msg)
            await admin_rest_orders.list_orders(cq_orders, db)
            assert "Текущие заказы" in (msg.text or "")

            cq_back = FakeCallbackQuery("r:back:main", admin_id, msg)
            await admin_rest_orders.back_main(cq_back)
            assert "Админ-меню ресторана" in (msg.text or "")

    asyncio.run(_run())


def test_admin_restaurant_back_from_order_card_to_orders_list():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 3302
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["rest_id"])
            order_id = await _seed_shop_order_and_chat(db, user_id=admin_id, shop_id=base["rest_id"])

            msg = FakeMessage()

            cq_card = FakeCallbackQuery(f"r:order:{order_id}", admin_id, msg)
            await admin_rest_orders.order_card(cq_card, db)
            assert f"Заказ #{order_id}" in (msg.text or "")

            cq_back = FakeCallbackQuery("r:orders", admin_id, msg)
            await admin_rest_orders.list_orders(cq_back, db)
            assert "Текущие заказы" in (msg.text or "")

    asyncio.run(_run())


def test_admin_restaurant_promos_back_to_promos_list():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 3303
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["rest_id"])
            promo_id = await _seed_promo(db, shop_id=base["rest_id"], title="Комбо")

            state = FakeFSMContext()
            msg = FakeMessage()

            cq_promos = FakeCallbackQuery("r:promos", admin_id, msg)
            await admin_rest_extra.promos(cq_promos, db)
            assert "Акции" in (msg.text or "")

            cq_card = FakeCallbackQuery(f"r:promo:{promo_id}", admin_id, msg)
            await admin_rest_extra.promo_card(cq_card, db, state)
            assert "Акция" in (msg.text or "")

            cq_back = FakeCallbackQuery("r:promos", admin_id, msg)
            await admin_rest_extra.promos(cq_back, db)
            assert "Акции" in (msg.text or "")

    asyncio.run(_run())


def test_admin_restaurant_chat_back_to_chat_list():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 3304
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["rest_id"])
            order_id = await _seed_shop_order_and_chat(db, user_id=admin_id, shop_id=base["rest_id"])

            msg = FakeMessage()

            cq_list = FakeCallbackQuery("r:chat", admin_id, msg)
            await admin_rest_extra.chat_list(cq_list, db)
            assert "Чаты" in (msg.text or "")

            cq_open = FakeCallbackQuery(f"r:chat:{order_id}", admin_id, msg)
            await admin_rest_extra.open_chat(cq_open, db)
            assert f"Чат по заказу #{order_id}" in (msg.text or "")

            cq_back = FakeCallbackQuery("r:chat", admin_id, msg)
            await admin_rest_extra.chat_list(cq_back, db)
            assert "Чаты" in (msg.text or "")

    asyncio.run(_run())


def test_admin_restaurant_products_back_chain():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()

            admin_id = 3305
            base = await _seed_base(db, user_id=admin_id)
            await _grant_admin(db, admin_id, base["rest_id"])

            msg = FakeMessage()

            # Open categories (r:cats) then open a category (r:cat:{id}) then back to cats
            cq_cats = FakeCallbackQuery("r:cats", admin_id, msg)
            await admin_rest_products.list_categories(cq_cats, db)
            assert "Категории" in (msg.text or "")

            cq_cat = FakeCallbackQuery(f"r:cat:{base['rest_cat']}", admin_id, msg)
            await admin_rest_products.open_category(cq_cat, db)
            assert "Товары категории" in (msg.text or "")

            cq_back_to_cats = FakeCallbackQuery("r:cats", admin_id, msg)
            await admin_rest_products.list_categories(cq_back_to_cats, db)
            assert "Категории" in (msg.text or "")

            # Back to main
            cq_back_main = FakeCallbackQuery("r:back:main", admin_id, msg)
            await admin_rest_orders.back_main(cq_back_main)
            assert "Админ-меню ресторана" in (msg.text or "")

    asyncio.run(_run())
