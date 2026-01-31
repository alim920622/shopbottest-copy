import asyncio
import tempfile
from pathlib import Path

from app.db.database import Database, DBConfig
from app.repositories.shops_repo import ShopsRepo
from app.repositories.categories_repo import CategoriesRepo
from app.repositories.products_repo import ProductsRepo
from app.repositories.cart_repo import CartRepo
from app.repositories.orders_repo import OrdersRepo
from app.handlers_client import catalog as client_catalog
from app.handlers_admin_shop import orders as admin_shop_orders


class FakeUser:
    def __init__(self, user_id: int):
        self.id = user_id


class FakeBot:
    async def send_message(self, user_id: int, text: str):
        # For these tests we don't need to assert sends.
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


async def _seed_db(db: Database, user_id: int) -> dict:
    shops = ShopsRepo(db)
    cats = CategoriesRepo(db)
    products = ProductsRepo(db)
    cart = CartRepo(db)
    orders = OrdersRepo(db)

    # создаём магазины и рестораны
    shop_id = await shops.create_shop("Shop A", "shop")
    rest_id = await shops.create_shop("Rest A", "restaurant")

    # категории
    shop_cat = await cats.create(shop_id, "Молочка")
    rest_cat = await cats.create(rest_id, "Салаты")

    # товары
    milk_id = await products.create(shop_id, shop_cat, "Молоко", 50.0, "Свежее")
    salad_id = await products.create(rest_id, rest_cat, "Салат", 30.0, "Овощной")

    # кладём по одному товару в корзину shop и restaurant
    await cart.add(user_id=user_id, product_id=milk_id, qty=1)
    await cart.add(user_id=user_id, product_id=salad_id, qty=1)

    # теперь создаём заказ корректным методом: create_order_from_cart
    # !!! важно: этот метод сам пересчитает total_amount и создаст order_items
    order_id = await orders.create_order_from_cart(shop_id=shop_id, client_user_id=user_id)

    return {
        "shop_id": shop_id,
        "rest_id": rest_id,
        "shop_cat": shop_cat,
        "rest_cat": rest_cat,
        "milk_id": milk_id,
        "salad_id": salad_id,
        "order_id": order_id,
    }


def test_client_back_from_cart_to_products():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()
            user_id = 101
            ids = await _seed_db(db, user_id=user_id)

            state = FakeFSMContext()
            msg = FakeMessage()

            # Open category -> products list (sets last_view=products)
            cq_open_cat = FakeCallbackQuery(f"c:cat:{ids['shop_id']}:{ids['shop_cat']}", user_id, msg)
            await client_catalog.open_category(cq_open_cat, db, state)
            assert msg.text == "Список товаров:"

            # Open cart from products list, with explicit back-target encoding
            cq_cart = FakeCallbackQuery(
                f"c:cart:auto:products:{ids['shop_id']}:{ids['shop_cat']}",
                user_id,
                msg,
            )
            await client_catalog.open_cart(cq_cart, db, state)
            assert "Корзина" in (msg.text or "")

            # Back from cart must return to products list screen
            cq_back = FakeCallbackQuery(
                f"c:back:from_cart:products:{ids['shop_id']}:{ids['shop_cat']}",
                user_id,
                msg,
            )
            await client_catalog.back(cq_back, db, state)
            assert msg.text == "Список товаров:"

    asyncio.run(_run())


def test_client_back_from_cart_to_shops_list():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()
            user_id = 102
            await _seed_db(db, user_id=user_id)

            state = FakeFSMContext()
            msg = FakeMessage()

            # Go to shops list (sets last_view=shops_list)
            cq_shops = FakeCallbackQuery("c:shops", user_id, msg)
            await client_catalog.list_shops(cq_shops, db, state)
            assert msg.text == "Выберите магазин:"

            # Open cart from shops list; back_target 'shops_list' should restore shops list
            cq_cart = FakeCallbackQuery("c:cart:shop:shops_list", user_id, msg)
            await client_catalog.open_cart(cq_cart, db, state)
            assert "Корзина" in (msg.text or "")

            cq_back = FakeCallbackQuery("c:back:from_cart:shops_list", user_id, msg)
            await client_catalog.back(cq_back, db, state)
            assert msg.text == "Выберите магазин:"

    asyncio.run(_run())


def test_client_back_from_cart_to_cart_menu():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()
            user_id = 103
            await _seed_db(db, user_id=user_id)

            state = FakeFSMContext()
            msg = FakeMessage()

            cq_cart_menu = FakeCallbackQuery("c:cart_menu", user_id, msg)
            await client_catalog.cart_menu(cq_cart_menu, state)
            assert msg.text == "Выберите корзину:"

            # Open shop cart from cart_menu; pass back_target=cart_menu
            cq_cart = FakeCallbackQuery("c:cart:shop:cart_menu", user_id, msg)
            await client_catalog.open_cart(cq_cart, db, state)
            assert "Корзина" in (msg.text or "")

            cq_back = FakeCallbackQuery("c:back:from_cart:cart_menu", user_id, msg)
            await client_catalog.back(cq_back, db, state)
            assert msg.text == "Выберите корзину:"

    asyncio.run(_run())


def test_admin_shop_back_from_order_card_to_orders_list():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(DBConfig(path=str(Path(tmpdir) / "t.db")))
            await db.init_schema()
            user_id = 201
            ids = await _seed_db(db, user_id=user_id)

            # Grant this user admin access to shop_id
            async with db.conn() as conn:
                await conn.execute(
                    "INSERT INTO shop_admins(user_id, shop_id) VALUES (?, ?)",
                    (user_id, ids["shop_id"]),
                )
                await conn.commit()

            msg = FakeMessage()

            cq_orders = FakeCallbackQuery("a:orders", user_id, msg)
            await admin_shop_orders.list_orders(cq_orders, db)
            assert "Текущие заказы" in (msg.text or "")

            cq_card = FakeCallbackQuery(f"a:order:{ids['order_id']}", user_id, msg)
            await admin_shop_orders.order_card(cq_card, db)
            assert f"Заказ #{ids['order_id']}" in (msg.text or "")

            # Back button on card is a:orders
            cq_back = FakeCallbackQuery("a:orders", user_id, msg)
            await admin_shop_orders.list_orders(cq_back, db)
            assert "Текущие заказы" in (msg.text or "")

    asyncio.run(_run())
