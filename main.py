import sys
import aiosqlite
import time
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import LabeledPrice, PreCheckoutQuery, SuccessfullPayment,BufferedInputFile
import asyncio
from aiogram.filters import BaseFilter
import os
import io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import datetime as dt_module

# Настраиваем проверку на админа
class AdminFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == ADMIN_ID

# Создаем экземпляр фильтра для использования в декораторах
is_admin = AdminFilter()

# Фикс для Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TOKEN = "8394069192:AAGUq6l0X5Leyi8ZgLnIHoOm_Sw6udrhXtg"
bot = Bot(token=TOKEN)
dp = Dispatcher()


async def generate_map(towers, farms, factories, houses):
    width, height = 800, 800
    # Создаем фон (трава)
    img = Image.new('RGB', (width, height), color=(60, 140, 60))
    draw = ImageDraw.Draw(img)

    # --- НОВАЯ ФИШКА: РЕКА 🌊 ---
    # Рисуем извилистую линию воды через всю карту
    river_points = []
    current_x = 0
    current_y = random.randint(100, 700)
    for i in range(0, 850, 50):
        current_x = i
        current_y += random.randint(-60, 60)  # Изгибы
        river_points.append((current_x, current_y))

    # Рисуем саму реку (широкая синяя линия)
    draw.line(river_points, fill=(50, 120, 200), width=45)
    # Добавим «блики» на воде (тонкая светлая линия внутри)
    draw.line(river_points, fill=(80, 150, 230), width=10)

    # Добавим немного текстуры травы (точки)
    for _ in range(300):
        draw.point((random.randint(0, 799), random.randint(0, 799)), fill=(70, 150, 70))

    used_coords = []

    def get_safe_coords(size):
        for _ in range(150):
            x = random.randint(50, width - 100)
            y = random.randint(50, height - 120)

            # Проверка, чтобы здания не ставились ПРЯМО на реку
            # (Грубая проверка по y-координате реки в этой точке x)
            on_river = False
            for rx, ry in river_points:
                if abs(x - rx) < 60 and abs(y - ry) < 60:
                    on_river = True
                    break

            if not on_river and all(abs(x - cx) > size and abs(y - cy) > size for cx, cy in used_coords):
                used_coords.append((x, y))
                return x, y
        return None

    # --- Остальной код отрисовки зданий (Заводы, Башни, Фермы, Дома) остается таким же ---
    # (Тут идут твои циклы отрисовки рисунков...)

    # --- 1. ЗАВОДЫ ---
    for _ in range(factories):
        coords = get_safe_coords(110)
        if coords:
            x, y = coords
            draw.rectangle([x, y + 20, x + 80, y + 60], fill=(120, 120, 120), outline=(40, 40, 40))
            draw.rectangle([x + 10, y, x + 25, y + 20], fill=(100, 100, 100), outline=(40, 40, 40))
            draw.rectangle([x + 35, y, x + 50, y + 20], fill=(100, 100, 100), outline=(40, 40, 40))
            draw.ellipse([x + 5, y - 15, x + 25, y - 5], fill=(200, 200, 200))
            draw.ellipse([x + 30, y - 20, x + 50, y - 10], fill=(200, 200, 200))

    # --- 2. БАШНИ ---
    for _ in range(towers):
        coords = get_safe_coords(80)
        if coords:
            x, y = coords
            draw.rectangle([x, y, x + 40, y + 80], fill=(100, 100, 100), outline=(30, 30, 30))
            draw.rectangle([x - 5, y - 5, x + 45, y + 15], fill=(80, 80, 80), outline=(30, 30, 30))
            draw.rectangle([x + 15, y + 25, x + 25, y + 45], fill=(20, 20, 20))

            # --- 3. ФЕРМЫ ---
    for _ in range(farms):
        coords = get_safe_coords(75)
        if coords:
            x, y = coords
            draw.rectangle([x, y, x + 70, y + 45], fill=(101, 67, 33), outline=(50, 30, 0))
            for i in range(x + 5, x + 70, 12):
                draw.line([(i, y + 5), (i, y + 40)], fill=(139, 69, 19), width=2)

    # --- 4. ДОМА ---
    for _ in range(houses):
        coords = get_safe_coords(60)
        if coords:
            x, y = coords
            draw.rectangle([x, y + 20, x + 45, y + 50], fill=(200, 180, 150), outline=(50, 50, 50))
            draw.polygon([(x - 5, y + 20), (x + 22, y), (x + 50, y + 20)], fill=(150, 50, 50), outline=(50, 50, 50))
            draw.rectangle([x + 18, y + 35, x + 28, y + 50], fill=(80, 50, 20))

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr
# Словарь рангов
RANKS = {
    1: "Уборщик 🧹",
    2: "Крестьянин 🌾",
    5: "Рыцарь ⚔️",
    9: "Десница 📜",
    10: "Король 👑",
    11: "Император 👑🏛"
}

# Временное хранилище приглашений (в памяти)
# ID приглашенного -> Название империи
pending_invites = {}
# Кулдауны работы
cooldowns = {}


async def init_db():
    async with aiosqlite.connect("game.db") as db:
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS players
                         (
                             user_id
                             INTEGER
                             PRIMARY
                             KEY,
                             name
                             TEXT,
                             empire_name
                             TEXT,
                             owner_id
                             INTEGER,
                             gold
                             INTEGER
                             DEFAULT
                             500,
                             total_mined
                             INTEGER
                             DEFAULT
                             0,
                             rank
                             INTEGER
                             DEFAULT
                             1,
                             towers
                             INTEGER
                             DEFAULT
                             0,
                             soldiers
                             INTEGER
                             DEFAULT
                             0,
                             weapon_power
                             INTEGER
                             DEFAULT
                             0,
                             age
                             INTEGER
                             DEFAULT
                             1,
                             population
                             INTEGER
                             DEFAULT
                             0,
                             farms
                             INTEGER
                             DEFAULT
                             0, -- ДОБАВИЛИ ФЕРМЫ
                             factories
                             INTEGER
                             DEFAULT
                             0, -- ДОБАВИЛИ ЗАВОДЫ
                             last_daily
                             TEXT
                             DEFAULT
                             '2000-01-01',
                             join_date
                             TEXT
                         )
                         """)

        # --- ВАЖНО: Код ниже добавит колонки, если база уже создана ---
        try:
            await db.execute("ALTER TABLE players ADD COLUMN farms INTEGER DEFAULT 0")
        except:
            pass
        try:
            await db.execute("ALTER TABLE players ADD COLUMN factories INTEGER DEFAULT 0")
        except:
            pass
        try:
            await db.execute("ALTER TABLE players ADD COLUMN houses INTEGER DEFAULT 1")
        except:
            pass
        # Добавь это в init_db()
        try:
            await db.execute("ALTER TABLE players ADD COLUMN is_vip INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE players ADD COLUMN shield_until TEXT DEFAULT '2000-01-01 00:00:00'")
        except:
            pass
        try:
            await db.execute("ALTER TABLE players ADD COLUMN wood INTEGER DEFAULT 100")
            await db.execute("ALTER TABLE players ADD COLUMN stone INTEGER DEFAULT 50")
            await db.execute("ALTER TABLE players ADD COLUMN iron INTEGER DEFAULT 0")
        except:
            pass  # Колонки уже есть
        try:
            # Прогресс текущих заданий
            await db.execute("ALTER TABLE players ADD COLUMN q_build_count INTEGER DEFAULT 0")  # Сколько построил
            await db.execute("ALTER TABLE players ADD COLUMN q_attack_count INTEGER DEFAULT 0")  # Сколько напал
            await db.execute(
                "ALTER TABLE players ADD COLUMN q_completed TEXT DEFAULT ''")  # Список выполненных сегодня (ID)
        except:
            pass
        # --------------------------------------------------------------

        await db.commit()

AGES = {
    1: "Каменный век 🪨",
    2: "Бронзовый век 🪵",
    3: "Железный век ⚔️",
    4: "Имперская эпоха 🏰"
}
AGE_COSTS = {2: 5000, 3: 20000, 4: 100000}

WEAPONS = {
    1: {"name": "Каменные топоры 🪓", "cost": 2000, "power": 10},
    2: {"name": "Бронзовые копья 🗡", "cost": 7000, "power": 30},
    3: {"name": "Стальные мечи ⚔️", "cost": 25000, "power": 100},
    4: {"name": "Мушкеты и пушки 🔫", "cost": 100000, "power": 500}
}
# Базовые цены продажи (за 100 единиц ресурса)
MARKET_PRICES = {
    "wood": 200,  # 100 дерева = 200 золота
    "stone": 400,  # 100 камня = 400 золота
    "iron": 1500  # 100 железа = 1500 золота (дорогое!)
}

ADMIN_ID = 7222282910  # ЗАМЕНИ НА СВОЙ ID (цифрами)

DAILY_QUESTS = {
    "build": {"desc": "🏗 Построить 3 любых здания", "target": 3, "reward": 2000, "res": "wood", "res_amt": 500},
    "attack": {"desc": "⚔️ Совершить 5 нападений", "target": 5, "reward": 5000, "res": "iron", "res_amt": 30}
}

# --- ДАННЫЕ ГЕРОЕВ ---
HEROES_DATA = {
    1: {"name": "Бродяга с палкой", "power": 10, "rarity": "Мусор", "color": (100, 100, 100)},
    2: {"name": "Пьяный ополченец", "power": 30, "rarity": "Обычный", "color": (150, 150, 150)},
    3: {"name": "Деревенский копейщик", "power": 60, "rarity": "Обычный", "color": (150, 150, 150)},
    4: {"name": "Наемный арбалетчик", "power": 120, "rarity": "Обычный", "color": (150, 150, 150)},
    5: {"name": "Орк-разведчик", "power": 200, "rarity": "Необычный", "color": (50, 200, 50)},
    6: {"name": "Железный страж", "power": 350, "rarity": "Необычный", "color": (50, 200, 50)},
    7: {"name": "Маг-недоучка", "power": 500, "rarity": "Необычный", "color": (50, 200, 50)},
    8: {"name": "Эльфийский следопыт", "power": 750, "rarity": "Редкий", "color": (0, 150, 255)},
    9: {"name": "Тёмный ассасин", "power": 1000, "rarity": "Редкий", "color": (0, 150, 255)},
    10: {"name": "Рыцарь Авангарда", "power": 1500, "rarity": "Редкий", "color": (0, 150, 255)},
    11: {"name": "Берсерк Севера", "power": 2200, "rarity": "Мифический", "color": (200, 0, 255)},
    12: {"name": "Мастер стихий", "power": 3000, "rarity": "Мифический", "color": (200, 0, 255)},
    13: {"name": "Паладин Света", "power": 4500, "rarity": "Мифический", "color": (200, 0, 255)},
    14: {"name": "Некромант Бездны", "power": 6000, "rarity": "Эпический", "color": (255, 0, 100)},
    15: {"name": "Верховный инквизитор", "power": 8500, "rarity": "Эпический", "color": (255, 0, 100)},
    16: {"name": "Демон ярости", "power": 12000, "rarity": "Эпический", "color": (255, 0, 100)},
    17: {"name": "Древний Дракон", "power": 20000, "rarity": "ЛЕГЕНДАРНЫЙ", "color": (255, 215, 0)},
    18: {"name": "Ангел мщения", "power": 35000, "rarity": "ЛЕГЕНДАРНЫЙ", "color": (255, 215, 0)},
    19: {"name": "Титановый Голем", "power": 50000, "rarity": "ЛЕГЕНДАРНЫЙ", "color": (255, 215, 0)},
    20: {"name": "Владыка Миров", "power": 100000, "rarity": "БОЖЕСТВЕННЫЙ", "color": (255, 255, 255)}
}

# Разные словари для разных команд
warrior_cooldowns = {}  # Для команды .воин
work_cooldowns = {}     # Для команды .работать


@dp.message(F.text.lower() == ".воин")
async def get_hero_card(message: types.Message):
    try:
        uid = message.from_user.id

        # ИСПРАВЛЕННАЯ СТРОКА (ПОЛНЫЙ ПУТЬ)
        import datetime as dt_lib
        now = dt_lib.datetime.now()
        td = dt_lib.timedelta

        # 1. Проверка кулдауна (используем warrior_cooldowns!)
        if uid in warrior_cooldowns:
            last_time = warrior_cooldowns[uid]
            if now < last_time + td(hours=4):
                remaining = (last_time + td(hours=4)) - now
                h, r = divmod(int(remaining.total_seconds()), 3600)
                m, s = divmod(r, 60)
                return await message.answer(f"⏳ Рано! Жди `{h}ч {m}м {s}с`")
        # 2. Выбор героя
        weights = [100 - (i * 4.5) for i in range(20)]
        hero_id = random.choices(range(1, 21), weights=weights)[0]
        hero = HEROES_DATA[hero_id]

        image_path = f"heroes/{hero_id}.png"
        if not os.path.exists(image_path):
            return await message.answer(f"⚠️ Файл heroes/{hero_id}.png не найден!")

        # ОБНОВЛЯЕМ КУЛДАУН
        warrior_cooldowns[uid] = now

        # 3. Рисование карточки
        card = Image.new('RGB', (500, 750), color=(10, 10, 10))
        draw = ImageDraw.Draw(card)

        try:
            hero_img = Image.open(image_path).convert("RGBA").resize((440, 440))
            card.paste(hero_img, (30, 130), hero_img)
        except Exception as e:
            print(f"Ошибка фото: {e}")

        draw.rectangle([15, 15, 485, 735], outline=hero['color'], width=12)

        try:
            f_name = ImageFont.truetype("arial.ttf", 45)
            f_stats = ImageFont.truetype("arial.ttf", 30)
        except:
            f_name = f_stats = ImageFont.load_default()

        draw.text((40, 40), hero['name'], fill=(255, 255, 255), font=f_name)
        draw.text((40, 590), f"⚔️ МОЩЬ: {hero['power']}", fill=(255, 255, 255), font=f_stats)



        # Шкала
        draw.rectangle([40, 640, 460, 670], fill=(40, 40, 40))
        bar_w = int((hero['power'] / 100000) * 420)
        draw.rectangle([40, 640, 40 + max(10, bar_w), 670], fill=hero['color'])

        draw.text((40, 690), f"ID: #{hero_id:03} | 2026", fill=(70, 70, 70), font=f_stats)

        # 4. Отправка
        buf = io.BytesIO()
        card.save(buf, format='PNG')
        buf.seek(0)

        await message.answer_photo(
            BufferedInputFile(buf.read(), filename="hero.png"),
            caption=f"✨ Ты призвал: **{hero['name']}**!"
        )

        # ... (после отправки фото) ...

        async with aiosqlite.connect("game.db") as db:
            # Прибавляем мощь героя к общему показателю игрока
            await db.execute(
                "UPDATE players SET weapon_power = weapon_power + ? WHERE user_id = ?",
                (hero['power'], uid)
            )
            await db.commit()

        await message.answer(f"✅ Мощь вашей империи навсегда увеличена на `{hero['power']}` ед.!")

    except Exception as e:
        print(f"Критическая ошибка: {e}")
@dp.message(F.text.lower() == ".задания")
async def show_quests(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT q_build_count, q_attack_count, q_completed FROM players WHERE user_id = ?",
                              (uid,)) as c:
            row = await c.fetchone()
            if not row: return

            b_count, a_count, completed = row
            completed_list = completed.split(',') if completed else []

            # --- НОВАЯ ФИШКА: РАСЧЕТ БОНУСА СЕРИИ ---
            is_all_done = "build" in completed_list and "attack" in completed_list
            bonus_status = "⭐ **Бонус дня получен!** (+1000 💰)" if is_all_done else "🎁 Выполни все задания, чтобы получить бонус дня!"

            text = "📜 **ЕЖЕДНЕВНЫЕ ПОРУЧЕНИЯ**\n━━━━━━━━━━━━━━━━━━\n"

            # Квест на стройку
            status_b = "✅ Выполнено" if "build" in completed_list else f"⏳ Прогресс: `{b_count}/3`"
            text += f"{DAILY_QUESTS['build']['desc']}\n└ {status_b}\n\n"

            # Квест на атаку
            status_a = "✅ Выполнено" if "attack" in completed_list else f"⏳ Прогресс: `{a_count}/5`"
            text += f"{DAILY_QUESTS['attack']['desc']}\n└ {status_a}\n"

            text += "━━━━━━━━━━━━━━━━━━\n"
            text += f"{bonus_status}\n"  # Выводим статус бонуса
            text += "━━━━━━━━━━━━━━━━━━\n💰 Награда выдается автоматически!"

            await message.answer(text, parse_mode="Markdown")


async def check_quest(uid, quest_type, message):
    async with aiosqlite.connect("game.db") as db:
        # Увеличиваем прогресс
        col = "q_build_count" if quest_type == "build" else "q_attack_count"
        await db.execute(f"UPDATE players SET {col} = {col} + 1 WHERE user_id = ?", (uid,))

        # Проверяем прогресс
        async with db.execute(f"SELECT {col}, q_completed FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            if not row: return
            count, completed = row

            q = DAILY_QUESTS[quest_type]
            # Проверяем, выполнено ли конкретное задание впервые за сегодня
            if count >= q['target'] and quest_type not in (completed or ""):
                # Обновляем список выполненных
                new_completed = (completed + f",{quest_type}") if completed else quest_type

                # --- НОВАЯ ФИШКА: ПРОВЕРКА КОМБО-БОНУСА ---
                combo_text = ""
                all_quests = ["build", "attack"]
                # Если после этого квеста все задания из списка DAILY_QUESTS выполнены
                if all(item in new_completed.split(',') for item in all_quests):
                    combo_gold = 1000  # Размер бонуса
                    await db.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (combo_gold, uid))
                    combo_text = f"\n\n🌟 **КОМБО!** Все задания дня выполнены!\nДополнительный бонус: `+{combo_gold}` 💰"

                # Выдаем основную награду и обновляем статус
                await db.execute(
                    f"UPDATE players SET gold = gold + ?, {q['res']} = {q['res']} + ?, q_completed = ? WHERE user_id = ?",
                    (q['reward'], q['res_amt'], new_completed, uid)
                )

                await message.answer(
                    f"🎊 **ЗАДАНИЕ ВЫПОЛНЕНО!**\n"
                    f"Награда за «{q['desc']}»:\n"
                    f"💰 +{q['reward']} золота\n"
                    f"📦 +{q['res_amt']} {q['res']}"
                    f"{combo_text}"  # Добавляем текст комбо, если он есть
                )
        await db.commit()


@dp.message(F.text.lower() == ".админ")
async def admin_help(message: types.Message):
    if not is_admin(message): return

    text = (
        "👑 **ПАНЕЛЬ СОЗДАТЕЛЯ**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 `.дать [ресурс] [кол-во]` — (ответом) выдать\n"
        "🚫 `.забрать [ресурс] [кол-во]` — (ответом) изъять\n"
        "⚡️ `.обнулить` — (ответом) удалить империю\n"
        "📢 `.рассылка [текст]` — сообщение всем\n"
        "📊 `.стат` — общая статистика мира\n"  # Новая кнопка в меню
        "━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(text, parse_mode="Markdown")


# --- НОВАЯ ФИШКА: ГЛОБАЛЬНАЯ СТАТИСТИКА ---
@dp.message(F.text.lower() == ".стат", is_admin)
async def global_stats(message: types.Message):
    async with aiosqlite.connect("game.db") as db:
        async with db.execute(
                "SELECT COUNT(*), SUM(gold), SUM(population), AVG(gold) FROM players"
        ) as c:
            count, total_gold, total_pop, avg_gold = await c.fetchone()

        # Узнаем самого богатого игрока для контроля
        async with db.execute("SELECT name, gold FROM players ORDER BY gold DESC LIMIT 1") as c:
            top_player = await c.fetchone()

    text = (
        "📊 **ГЛОБАЛЬНАЯ СТАТИСТИКА МИРА**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👥 Всего игроков: `{count}`\n"
        f"👨‍👩‍👧‍👦 Общее население: `{total_pop or 0}`\n"
        f"💰 Золота в обороте: `{total_gold or 0}`\n"
        f"📈 Средний чек игрока: `{int(avg_gold or 0)}` 💰\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👑 Богатейший: `{top_player[0] if top_player else 'Нет'}` (`{top_player[1] if top_player else 0}` 💰)"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text.lower().startswith(".забрать"))
async def take_res(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    if not message.reply_to_message:
        return await message.answer("❌ Ответь на сообщение игрока!")

    cmd = message.text.lower().split()
    if len(cmd) < 3:
        return await message.answer("❌ Формат: `.забрать золото 100`")

    res_type = cmd[1]
    try:
        amount = int(cmd[2])
    except:
        return await message.answer("❌ Количество должно быть числом!")

    target_id = message.reply_to_message.from_user.id
    res_map = {"золото": "gold", "дерево": "wood", "камень": "stone", "железо": "iron"}

    if res_type not in res_map:
        return await message.answer("❌ Неверный ресурс (золото/дерево/камень/железо)")

    async with aiosqlite.connect("game.db") as db:
        # Уменьшаем ресурс, но следим, чтобы баланс не ушел в минус ниже нуля
        col = res_map[res_type]
        await db.execute(f"UPDATE players SET {col} = MAX(0, {col} - ?) WHERE user_id = ?",
                         (amount, target_id))
        await db.commit()

    await message.answer(f"🚫 Вы изъяли `{amount}` {res_type} у игрока {message.reply_to_message.from_user.first_name}")

@dp.message(F.text.lower().startswith(".дать"), is_admin)
async def give_res(message: types.Message):
    if not message.reply_to_message:
        return await message.answer("❌ Ответь на сообщение игрока!")

    cmd = message.text.lower().split()
    if len(cmd) < 3: return

    res_type = cmd[1]
    amount = int(cmd[2])
    target_id = message.reply_to_message.from_user.id

    res_map = {"золото": "gold", "дерево": "wood", "камень": "stone", "железо": "iron"}
    if res_type not in res_map: return await message.answer("❌ Неверный ресурс")

    async with aiosqlite.connect("game.db") as db:
        await db.execute(f"UPDATE players SET {res_map[res_type]} = {res_map[res_type]} + ? WHERE user_id = ?",
                         (amount, target_id))
        await db.commit()

    await message.answer(f"✅ Вы выдали `{amount}` {res_type} игроку {message.reply_to_message.from_user.first_name}")


@dp.message(F.text.lower().startswith(".рассылка"), is_admin)
async def broadcast(message: types.Message):
    text = message.text[10:]  # Отрезаем команду ".рассылка "
    if not text: return

    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT user_id FROM players") as c:
            users = await c.fetchall()

    count = 0
    for user in users:
        try:
            await bot.send_message(user[0], f"📢 **ОПОВЕЩЕНИЕ ОТ АДМИНИСТРАЦИИ:**\n\n{text}", parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)  # Защита от спам-фильтра Telegram
        except:
            pass

    await message.answer(f"✅ Рассылка завершена. Получили `{count}` игроков.")


@dp.message(F.text.lower() == ".обнулить", is_admin)
async def reset_player(message: types.Message):
    if not message.reply_to_message: return

    target_id = message.reply_to_message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        await db.execute("DELETE FROM players WHERE user_id = ?", (target_id,))
        await db.commit()

    await message.answer("💥 Империя игрока полностью стерта с лица земли.")


@dp.message(F.text.lower() == ".империя")
async def empire_stats(message: types.Message):
    uid = message.from_user.id

    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT empire_name FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            if not row:
                return await message.answer("❌ Ты не состоишь в империи! Создай свою через `.создать`.")
            emp_name = row[0]

        # --- НОВАЯ ФИШКА: СБОР ДАННЫХ ОБ ОБОРОНЕ ---
        async with db.execute(
                "SELECT COUNT(*), SUM(gold), SUM(population), SUM(towers) FROM players WHERE empire_name = ?",
                (emp_name,)
        ) as c:
            stats = await c.fetchone()
            count_members, total_gold, total_pop, total_towers = stats

        async with db.execute(
                "SELECT name, gold, rank FROM players WHERE empire_name = ? ORDER BY gold DESC LIMIT 10",
                (emp_name,)
        ) as c:
            top_players = await c.fetchall()

    # Рассчитываем статус защиты на основе общего кол-ва башен
    towers_val = total_towers or 0
    if towers_val == 0: def_status = "❌ Беззащитна"
    elif towers_val < 10: def_status = "🛡 Слабая"
    elif towers_val < 30: def_status = "⚔️ Средняя"
    else: def_status = "🏰 Неприступная крепость"

    text = (
        f"🏰 **ИНФОЦЕНТР ИМПЕРИИ: {emp_name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Участников: `{count_members}`\n"
        f"👨‍👩‍👧‍👦 Нас: `{total_pop}` подданных\n"
        f"💰 Общий капитал: `{total_gold}` 💰\n"
        f"🗼 Всего башен: `{towers_val}`\n"
        f"🛡 Оборона: **{def_status}**\n" # Новая строка статуса
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 **ТОП-10 ПРАВИТЕЛЕЙ:**\n"
    )

    for i, p in enumerate(top_players, 1):
        p_name, p_gold, p_rank_id = p
        rank_name = RANKS.get(p_rank_id, "Житель")
        text += f"{i}. {p_name} — `{p_gold}` 💰 ({rank_name})\n"

    text += "\n📍 Чтобы позвать друзей, используй `.пригласить`"
    await message.answer(text, parse_mode="Markdown")


import datetime


@dp.message(F.text.lower() == ".рынок")
async def market_info(message: types.Message):
    # --- НОВАЯ ФИШКА: ДИНАМИЧЕСКИЕ НАЦЕНКИ ---
    now = datetime.now()
    # Если сегодня суббота или воскресенье (5 или 6)
    is_weekend = now.weekday() >= 5

    status_text = ""
    multiplier = 1.0

    if is_weekend:
        multiplier = 0.8  # В выходные перекупщики наглеют, цена ниже на 20%
        status_text = "⚠️ **Выходные на бирже:** Цены снижены на 20%!"
    elif 0 <= now.hour <= 6:
        multiplier = 1.2  # Ночная контрабанда: цена выше на 20%
        status_text = "🌙 **Ночная торговля:** Спрос велик, цены выше на 20%!"
    else:
        status_text = "🏢 **Рынок работает в штатном режиме.**"

    # Рассчитываем временные цены
    w_price = int(MARKET_PRICES['wood'] * multiplier)
    s_price = int(MARKET_PRICES['stone'] * multiplier)
    i_price = int(MARKET_PRICES['iron'] * multiplier)

    text = (
        "⚖️ **ГОСУДАРСТВЕННЫЙ РЫНОК**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{status_text}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🪵 100 Дерева  ➡️  `{w_price}` 💰\n"
        f"🪨 100 Камня   ➡️  `{s_price}` 💰\n"
        f"⛓ 100 Железа  ➡️  `{i_price}` 💰\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📝 **Как продать:**\n"
        "Напиши: `.продать [ресурс] [кол-во]`\n"
        "Пример: `.продать дерево 100`"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text.lower().startswith(".продать"))
async def sell_resource(message: types.Message):
    uid = message.from_user.id
    cmd = message.text.lower().split()

    if len(cmd) < 3:
        return await message.answer("❌ Формат: `.продать [дерево/камень/железо] [кол-во]`")

    res_type = cmd[1]
    try:
        amount = int(cmd[2])
    except ValueError:
        return await message.answer("❌ Укажи числовое количество!")

    if amount <= 0: return await message.answer("❌ Нельзя продать воздух!")

    res_map = {"дерево": "wood", "камень": "stone", "железо": "iron"}
    if res_type not in res_map:
        return await message.answer("❌ Нет такого ресурса!")

    db_col = res_map[res_type]

    # --- НОВАЯ ФИШКА: СИНХРОНИЗАЦИЯ ЦЕН И ОПТОВЫЙ БОНУС ---
    now = datetime.now()
    multiplier = 1.0

    # Те же условия, что в .рынок
    if now.weekday() >= 5:
        multiplier = 0.8  # Выходные
    elif 0 <= now.hour <= 6:
        multiplier = 1.2  # Ночь

    # Дополнительный бонус за опт (от 1000 единиц)
    wholesale_bonus = 1.05 if amount >= 1000 else 1.0

    price_per_100 = MARKET_PRICES[db_col]
    # Итоговая цена с учетом времени и опта
    final_price = int((amount / 100) * price_per_100 * multiplier * wholesale_bonus)

    async with aiosqlite.connect("game.db") as db:
        async with db.execute(f"SELECT {db_col} FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            if not row: return
            current_res = row[0]

            if current_res < amount:
                return await message.answer(f"❌ Недостаточно ресурса! У тебя: `{current_res}`")

            await db.execute(
                f"UPDATE players SET {db_col} = {db_col} - ?, gold = gold + ? WHERE user_id = ?",
                (amount, final_price, uid)
            )
            await db.commit()

            bonus_msg = "\n📦 **Бонус оптовика +5% применен!**" if wholesale_bonus > 1 else ""
            await message.answer(
                f"⚖️ **Сделка совершена!**\n"
                f"📉 Продано: `{amount}` {res_type}\n"
                f"💰 Получено: `{final_price}` золота (курс: {multiplier}x){bonus_msg}"
            )


@dp.message(F.text.lower() == ".карта")
async def show_map(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        async with db.execute(
                "SELECT towers, farms, factories, population, IFNULL(houses, 1), empire_name FROM players WHERE user_id = ?",
                (uid,)
        ) as c:
            row = await c.fetchone()

            if not row:
                return await message.answer("❌ У тебя еще нет империи! Напиши `.старт`.")

            towers, farms, factories, pop, houses, emp_name = row

            # --- НОВАЯ ФИШКА: ПОИСК СОСЕДЕЙ ---
            async with db.execute(
                    "SELECT name FROM players WHERE empire_name = ? AND user_id != ? ORDER BY RANDOM() LIMIT 3",
                    (emp_name, uid)
            ) as c:
                neighbors = await c.fetchall()

            neighbor_text = ""
            if neighbors:
                names = ", ".join([n[0] for n in neighbors])
                neighbor_text = f"\n\n👥 **Соседи по империи:**\n_{names}_"
            else:
                neighbor_text = "\n\n📍 В этом районе пока пусто... Позови друзей!"

            # Генерируем изображение
            map_image = await generate_map(towers, farms, factories, houses)

            # Отправка
            photo = BufferedInputFile(map_image.read(), filename=f"map_{uid}.png")

            caption = (
                f"🏰 **Империя: {emp_name}**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👥 Население: `{pop}` чел.\n"
                f"🏠 Жилых домов: `{houses}`\n"
                f"🚜 Фермерских угодий: `{farms}`\n"
                f"🏭 Заводов: `{factories}`\n"
                f"🗼 Оборонных башен: `{towers}`"
                f"{neighbor_text}"  # Добавляем список соседей
            )

            await message.answer_photo(photo, caption=caption, parse_mode="Markdown")


# 1. Выставление счета
@dp.message(F.text.lower() == ".купить вип")
async def buy_vip(message: types.Message):
    # --- НОВАЯ ФИШКА: ПРОВЕРКА НАЛИЧИЯ И УЛУЧШЕННОЕ ОПИСАНИЕ ---
    uid = message.from_user.id

    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT is_vip FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            if row and row[0] == 1:
                return await message.answer("👑 **У вас уже есть VIP-статус!**\nВы — истинный правитель этой империи.")

    # Красивое описание привилегий
    description = (
        "💎 ПРИВИЛЕГИИ VIP:\n"
        "📈 Доход x2 со всех работ\n"
        "🏰 Уникальная иконка 👑 в профиле\n"
        "🛡 +10% к шансу победы при штурме\n"
        "✨ Навсегда и без подписок!"
    )

    await message.answer_invoice(
        title="👑 VIP-Статус Императора",
        description=description,
        prices=[LabeledPrice(label="Активация статуса", amount=250)],  # 250 звезд
        payload="buy_vip_permanent",
        currency="XTR",
        provider_token="",  # Для Stars оставляем пустым
        photo_url="https://img.freepik.com/premium-photo/golden-crown-with-blue-gems-dark-background_931878-31653.jpg",
        # Добавим картинку в счет!
        photo_size=512,
        photo_width=512,
        photo_height=512
    )


@dp.message(F.text.lower() == ".купить щит")
async def buy_shield(message: types.Message):
    # --- НОВАЯ ФИШКА: КАРТИНКА И УТОЧНЕНИЕ СТАТУСА ---
    uid = message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT shield_until FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            current_shield = row[0] if row and row[0] else None

    status_msg = ""
    if current_shield:
        status_msg = f"\n⚠️ У вас уже есть активный щит! Покупка продлит его еще на 24ч."

    await message.answer_invoice(
        title="🛡 Божественный Щит",
        description=f"Полная неуязвимость империи на 24 часа. Вас нельзя будет ограбить!{status_msg}",
        prices=[LabeledPrice(label="Активация защиты", amount=100)],
        payload="buy_shield_24h",
        currency="XTR",
        provider_token="",
        photo_url="https://img.freepik.com/premium-photo/magic-shield-protecting-from-arrows-generative-ai_955925-50.jpg",
        photo_size=512,
        photo_width=512,
        photo_height=512
    )


@dp.message(F.successful_payment)
async def success_payment_handler(message: types.Message):
    payload = message.successful_payment.invoice_payload
    uid = message.from_user.id
    now = datetime.now()

    async with aiosqlite.connect("game.db") as db:
        if payload == "buy_vip_permanent":
            await db.execute("UPDATE players SET is_vip = 1 WHERE user_id = ?", (uid,))
            await message.answer(
                "👑 **Оплата прошла!**\nВы получили статус VIP. Твоё величие теперь неоспоримо, а доходы удвоены!")

        elif payload == "buy_shield_24h":
            # --- НОВАЯ ФИШКА: СУММИРОВАНИЕ ВРЕМЕНИ ---
            async with db.execute("SELECT shield_until FROM players WHERE user_id = ?", (uid,)) as c:
                row = await c.fetchone()
                # Если щит уже есть и он не истек, прибавляем к нему. Иначе — от текущего времени.
                if row and row[0]:
                    current_shield = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    start_from = max(now, current_shield)
                else:
                    start_from = now

                new_shield_time = (start_from + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

            await db.execute("UPDATE players SET shield_until = ? WHERE user_id = ?", (new_shield_time, uid))
            await message.answer(f"🛡 **Магия активирована!**\nЩит будет оберегать твой покой до: `{new_shield_time}`")

        await db.commit()

    async with aiosqlite.connect("game.db") as db:
        if payload == "buy_vip_permanent":
            await db.execute("UPDATE players SET is_vip = 1 WHERE user_id = ?", (uid,))
            await message.answer("👑 Оплата прошла! Вы теперь VIP-персона. Ваши налоги удвоены!")

        elif payload == "buy_shield_24h":
            # Устанавливаем время щита: текущее время + 24 часа
            shield_time = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("UPDATE players SET shield_until = ? WHERE user_id = ?", (shield_time, uid))
            await message.answer("🛡 Щит активирован! Вас невозможно ограбить в течение 24 часов.")

        await db.commit()



@dp.message(F.text.lower() == ".купить оружие")
async def buy_weapon(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT gold, age, weapon_power, name FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            if not row: return

            gold, age, current_power, p_name = row
            weapon = WEAPONS[age]

            if current_power >= weapon["power"]:
                return await message.answer(f"✅ У ваших солдат уже есть лучшее оружие этой эпохи: {weapon['name']}")

            if gold < weapon["cost"]:
                return await message.answer(f"❌ {weapon['name']} стоят {weapon['cost']} 💰. У тебя {gold} 💰")

            # --- НОВАЯ ФИШКА: ВОЕННЫЙ ПАРАД И БОНУСНЫЕ РЕКРУТЫ ---
            # При покупке есть 20% шанс получить бонусных солдат (новобранцы потянулись на блеск стали)
            bonus_soldiers = 0
            bonus_text = ""
            if random.randint(1, 100) <= 20:
                bonus_soldiers = random.randint(5, 15)
                bonus_text = f"\n\n🎺 **Военный парад!** Потрясенные новым вооружением, в вашу армию добровольно вступили `{bonus_soldiers}` рекрутов!"

            # Обновляем золото, силу и добавляем солдат, если они есть
            await db.execute(
                "UPDATE players SET gold = gold - ?, weapon_power = ?, soldiers = soldiers + ? WHERE user_id = ?",
                (weapon["cost"], weapon["power"], bonus_soldiers, uid)
            )
            await db.commit()

            await message.answer(
                f"⚒ **Армия «{p_name}» перевооружена!**\n"
                f"Экипировано: **{weapon['name']}**\n"
                f"⚔️ Базовая сила атаки установлена на `{weapon['power']}`."
                f"{bonus_text}"
            )


@dp.message(F.text.lower() == ".улучшить")
async def upgrade_age(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT gold, age FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            if not row: return

            gold, current_age = row
            next_age = current_age + 1

            if next_age not in AGE_COSTS:
                return await message.answer("🏛 У вас максимальная эпоха!")

            cost = AGE_COSTS[next_age]
            if gold < cost:
                return await message.answer(f"❌ Нужно `{cost}` 💰 для перехода в **{AGES[next_age]}**")

            # --- НОВАЯ ФИШКА: ТЕХНОЛОГИЧЕСКИЙ РЫВОК ---
            # При переходе даем случайный бонус ресурсов новой эпохи
            bonus_res = random.choice(["wood", "stone", "iron"])
            bonus_amount = 100 * next_age  # Чем выше эпоха, тем больше бонус
            res_names = {"wood": "🪵 Дерева", "stone": "🪨 Камня", "iron": "⛓ Железа"}

            # Списываем золото, обновляем эпоху и выдаем бонус
            query = f"UPDATE players SET gold = gold - ?, age = ?, {bonus_res} = {bonus_res} + ? WHERE user_id = ?"
            await db.execute(query, (cost, next_age, bonus_amount, uid))
            await db.commit()

            await message.answer(
                f"📈 **ВЕЛИКИЙ ПРОРЫВ!**\n"
                f"Ваша империя перешла в **{AGES[next_age]}**!\n\n"
                f"🔬 Наши ученые совершили открытие в честь новой эры:\n"
                f"🎁 Получено бонусом: `+{bonus_amount}` {res_names[bonus_res]}!"
            )

@dp.message(F.text.lower() == ".напасть")
async def attack(message: types.Message):
    if not message.reply_to_message:
        return await message.answer("⚔️ Ответь этой командой на сообщение жертвы!")

    attacker_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id
    if attacker_id == target_id: return

    async with aiosqlite.connect("game.db") as db:
        async with db.execute(
                "SELECT gold, soldiers, weapon_power, empire_name, IFNULL(is_vip, 0) FROM players WHERE user_id = ?",
                (attacker_id,)
        ) as c:
            att = await c.fetchone()

        async with db.execute(
                "SELECT gold, towers, empire_name, shield_until FROM players WHERE user_id = ?",
                (target_id,)
        ) as c:
            tar = await c.fetchone()

        if not att or not tar:
            return await message.answer("❌ Кто-то из вас не в игре!")

        # Проверка щита
        if tar[3]:
            shield_until = datetime.datetime.strptime(tar[3], "%Y-%m-%d %H:%M:%S")
            if shield_until > datetime.datetime.now():
                time_left = shield_until - datetime.datetime.now()
                hours = time_left.seconds // 3600
                return await message.answer(
                    f"🛡 **У империи «{tar[2]}» активирован Божественный щит!**"
                )

        a_gold, a_soldiers, a_power, a_name, a_is_vip = att
        t_gold, t_towers, t_name, t_shield_time = tar

        army_force = (a_soldiers * a_power) // 100
        defense_bonus = t_towers * 5
        vip_bonus = 10 if a_is_vip else 0

        win_chance = 40 + army_force - defense_bonus + vip_bonus
        win_chance = max(5, min(95, win_chance))

        if random.randint(1, 100) <= win_chance:
            loot_percent = 0.35 if a_is_vip else 0.25
            loot = int(t_gold * loot_percent)

            # --- НОВАЯ ФИШКА: ОСАДА И РАЗРУШЕНИЕ ---
            destruction_text = ""
            if t_towers > 0 and random.randint(1, 100) <= 10:  # 10% шанс снести башню
                await db.execute("UPDATE players SET towers = towers - 1 WHERE user_id = ?", (target_id,))
                destruction_text = f"\n🏚 **Осада была жестокой:** У «{t_name}» разрушена одна оборонная башня!"

            await db.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (loot, attacker_id))
            await db.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (loot, target_id))
            await db.commit()

            vip_tag = "👑 [VIP] " if a_is_vip else ""
            await message.answer(
                f"🔥 {vip_tag}Армия «{a_name}» прорвала оборону «{t_name}»!\n"
                f"💰 Награблено: `{loot}` золота. {destruction_text}"
            )
        else:
            # Логика поражения
            loss = 300 * (2 if a_is_vip else 1)
            dead = a_soldiers // 5
            await db.execute("UPDATE players SET gold = gold - ?, soldiers = soldiers - ? WHERE user_id = ?",
                             (loss, dead, attacker_id))
            await db.commit()
            await message.answer(f"💀 **Поражение!** Вы потеряли `{loss}` 💰 и `{dead}` воинов.")

        await check_quest(attacker_id, "attack", message)


@dp.message(F.text.lower().in_({".коды", ".команды", ".помощь"}))
async def help_cmd(message: types.Message):
    # Можно добавить время, чтобы игрок понимал актуальность бонусов
    server_time = datetime.datetime.now().strftime("%H:%M")

    text = (
        f"📜 **ГРАМОТА ПРАВИТЕЛЯ (v1.2)**\n"
        f"🕒 Время в столице: `{server_time}` | 🌐 Сервер: `RU-1`\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        "👤 **УПРАВЛЕНИЕ ЛОРДОМ**\n"
        "• `.кто я` — Профиль и индекс мощи\n"
        "• `.работать` — Добыча (раз в 60 сек) ⛏\n"
        "• `.склад` — Ресурсы и лимиты 📦\n"
        "• `.бонус` — Забрать дары дня 🎁\n"
        "• `.топ` — Великие империи мира 🏆\n"
        "• `.уйти` — Стать вольным странником 🏳️\n\n"

        "🏛 **ГРАДОСТРОИТЕЛЬСТВО**\n"
        "• `.построить дом/ферму/завод/башну [кол-во]` — Жилье для рабочих,ресурсы и сталь🏭,укрепить границы 🗼\n"
        "• `.магазин` — рынок и оборона 🏢\n"

        "⚔️ **ВОЙНА И ЭВОЛЮЦИЯ**\n"
        "• `.улучшить` — Сменить эпоху (новые юниты)\n"
        "• `.купить оружие` — Перевооружить армию\n"
        "• `.напасть` — Штурм (ответом на игрока) 🏰\n"
        "• `.нанять воинов [кол-во]` — Вербовка рекрутов\n\n"

        "👑 **ДИПЛОМАТИЯ (10+ ранг)**\n"
        "• `.имя [текст]` — Смена названия страны\n"
        "• `.пригласить` — Позвать в альянс 📜\n"
        "• `.выше` / `.ниже` [ранг] — Управление чинами\n"
        "• `.изгнать` — Выдворить предателя 👢\n\n"

        "🎰 **РАЗВЛЕЧЕНИЯ**\n"
        "• `.казино [ставка]` — Испытать удачу 🍒\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "💎 **МАГАЗИН ВЕЛИЧИЯ**\n"
        "• `.купить вип` — Ресурсы x2 навсегда\n"
        "• `.купить щит` — Иммунитет к грабежам (24ч)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 *Совет: Чаще заглядывай в профиль, чтобы следить за индексом мощи!*"
    )
    await message.answer(text, parse_mode="Markdown")
@dp.message(F.text.lower() == ".склад")
async def show_storage(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        # Добавляем в запрос houses, чтобы рассчитать лимит
        async with db.execute(
                "SELECT gold, wood, stone, iron, IFNULL(houses, 1) FROM players WHERE user_id = ?",
                (uid,)
        ) as c:
            row = await c.fetchone()
            if not row: return await message.answer("❌ Ты не в игре!")

            gold, wood, stone, iron, houses = row

            # --- НОВАЯ ФИШКА: СИСТЕМА ВМЕСТИМОСТИ ---
            # Базовая вместимость 1000 + 500 за каждый дом
            max_capacity = 1000 + (houses * 500)
            total_res = wood + stone + iron

            # Определяем статус заполненности
            if total_res >= max_capacity:
                status = "🔴 **СКЛАД ПЕРЕПОЛНЕН!** Построй больше домов."
            elif total_res > max_capacity * 0.8:
                status = "🟡 **Склад почти полон.**"
            else:
                status = "🟢 **Места достаточно.**"

            text = (
                f"📦 **ГОСУДАРСТВЕННЫЙ СКЛАД**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 Золото: `{gold}` (не занимает места)\n\n"
                f"🪵 Дерево: `{wood}`\n"
                f"🪨 Камень: `{stone}`\n"
                f"⛓ Железо: `{iron}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 Занято: `{total_res}` / `{max_capacity}`\n"
                f"{status}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💡 Каждые 🏠 **5 домов** увеличивают склад на **2500** ед."
            )
            await message.answer(text, parse_mode="Markdown")@dp.message(F.text.lower() == ".топ")
async def top_players(message: types.Message):
    async with aiosqlite.connect("game.db") as db:
        # --- НОВАЯ ФИШКА: РАСЧЕТ ИНДЕКСА МОЩИ ---
        # Считаем суммарную силу империи: золото + население + здания
        query = """
            SELECT name, empire_name, gold, 
            (gold + (population * 5) + (towers * 200) + (factories * 500)) as power_index 
            FROM players 
            ORDER BY power_index DESC 
            LIMIT 10
        """
        async with db.execute(query) as c:
            rows = await c.fetchall()

            if not rows:
                return await message.answer("🏆 Список лидеров пока пуст!")

            text = "🏆 **МИРОВОЙ РЕЙТИНГ МОЩИ** 🏆\n━━━━━━━━━━━━━━━━━━\n"
            for i, row in enumerate(rows, 1):
                name, emp, gold, p_index = row
                medals = {1: "🥇", 2: "🥈", 3: "🥉"}
                prefix = medals.get(i, f"{i}.")

                # Показываем и золото, и общий индекс мощи
                text += f"{prefix} **{emp}**\n└ 🎖 Мощь: `{int(p_index)}` | 💰 `{gold}`\n"

            text += "━━━━━━━━━━━━━━━━━━\n💡 Индекс мощи зависит от золота, населения и количества твоих зданий!"
            await message.answer(text, parse_mode="Markdown")


@dp.message(F.text.lower().startswith(".создать"))
async def create(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("❌ Напиши название своей империи!\nПример: `.создать Рим`")

    emp_name = args[1]
    uid = message.from_user.id
    user_name = message.from_user.first_name

    # --- ВОТ ТУТ ИСПРАВЛЕНИЕ ---
    import datetime as dt_lib
    now = dt_lib.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # ---------------------------

    async with aiosqlite.connect("game.db") as db:
        try:
            await db.execute("""
                             INSERT INTO players (user_id, name, empire_name, owner_id, rank, join_date,
                                                  gold, wood, stone, iron, population, houses)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (uid, user_name, emp_name, uid, 11, now,
                              1000, 300, 0, 0, 10, 1)
                             )
            await db.commit()

            text = (
                f"🏛 **Да здравствует Император {user_name}!**\n"
                f"Империя «{emp_name}» официально основана.\n\n"
                f"📦 **Ваш стартовый пакет:**\n"
                f"💰 Золото: `1000`\n"
                f"🪵 Дерево: `300`\n\n"
                f"📍 **С чего начать?**\n"
                f"1. Построй жилье: `.построить дом`\n"
                f"2. Загляни на склад: `.склад`"
            )
            await message.answer(text, parse_mode="Markdown")

        except Exception as e:
            await message.answer(
                "❌ **Ошибка!** Скорее всего, ваша империя уже существует или название занято.")
@dp.message(F.text.lower() == ".пригласить")
async def invite(message: types.Message):
    if not message.reply_to_message:
        return await message.answer("⚠️ Ответь на сообщение того, кого хочешь позвать!")

    sender_id = message.from_user.id
    target = message.reply_to_message.from_user

    if target.id == sender_id:
        return await message.answer("❌ Нельзя пригласить самого себя! Ты и так великий.")

    async with aiosqlite.connect("game.db") as db:
        # 1. Проверяем права отправителя
        async with db.execute("SELECT empire_name, rank FROM players WHERE user_id = ?", (sender_id,)) as c:
            sender_row = await c.fetchone()
            if not sender_row or sender_row[1] < 10:
                return await message.answer("❌ У тебя недостаточно полномочий для вербовки (нужен ранг 10+).")

            emp_name = sender_row[0]

        # 2. Проверяем, не состоит ли цель уже в какой-то империи
        async with db.execute("SELECT empire_name FROM players WHERE user_id = ?", (target.id,)) as c:
            target_row = await c.fetchone()
            if target_row:
                return await message.answer(f"❌ {target.first_name} уже служит другой империи!")

    # --- НОВАЯ ФИШКА: ВРЕМЕННЫЙ ИНВАЙТ ---
    pending_invites[target.id] = emp_name

    msg = await message.answer(
        f"📜 **ГОСУДАРСТВЕННЫЙ ПРИЗЫВ**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {target.mention_markdown()}, тебя приглашают в империю **«{emp_name}»**!\n\n"
        f"✅ Напиши `.вступить` в течение 5 минут, чтобы принять присягу."
    )

    # --- ИСПРАВЛЕННАЯ ФУНКЦИЯ ЭКСПИРАЦИИ ---
    async def expire_invite(t_id):
        await asyncio.sleep(300)  # 5 минут
        if t_id in pending_invites and pending_invites[t_id] == emp_name:
            del pending_invites[t_id]

    # ИСПРАВЛЕНО: Убрана лишняя скобка и добавлен правильный вызов задачи
    asyncio.create_task(expire_invite(target.id))

# --- КОМАНДА ВСТУПИТЬ (ОТДЕЛЕНА ОТ ПРЕДЫДУЩЕЙ) ---
@dp.message(F.text.lower() == ".вступить")
async def join(message: types.Message):
    uid = message.from_user.id
    user_name = message.from_user.first_name

    if uid not in pending_invites:
        return await message.answer("❌ **У вас нет активных приглашений!**\nПопросите Императора прислать вам его через `.пригласить`.")

    emp_name = pending_invites[uid]

    # --- ИСПРАВЛЕННЫЙ БЛОК ВРЕМЕНИ ---
    import datetime as dt_lib
    now = dt_lib.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # --------------------------------

    start_bonus = 500

    async with aiosqlite.connect("game.db") as db:
        try:
            # Проверяем, нет ли игрока уже в базе
            async with db.execute("SELECT user_id FROM players WHERE user_id = ?", (uid,)) as c:
                if await c.fetchone():
                    return await message.answer("❌ Ты уже состоишь в империи! Чтобы сменить сторону, сначала напиши `.уйти`.")

            # Вставляем данные нового игрока
            await db.execute("""
                INSERT INTO players (user_id, name, empire_name, rank, join_date, gold, population, houses)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (uid, user_name, emp_name, 1, now, start_bonus, 5, 1)
            )
            await db.commit()

            # Удаляем приглашение из памяти, так как оно использовано
            if uid in pending_invites:
                del pending_invites[uid]

            text = (
                f"🎊 **ПРИСЯГА ПРИНЯТА!** 🎊\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 **{user_name}**, теперь ты часть империи **«{emp_name}»**!\n\n"
                f"🎁 Тебе выданы подъемные: `+{start_bonus}` 💰\n"
                f"🏠 Твоё первое поселение готово к развитию.\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ Слава Империи!"
            )
            await message.answer(text, parse_mode="Markdown")

        except Exception as e:
            await message.answer(f"❌ Ошибка при регистрации присяги: {e}")
@dp.message(F.text.lower() == ".изгнать")
async def kick(message: types.Message):
    if not message.reply_to_message:
        return await message.answer("👢 Чтобы изгнать предателя, ответь этой командой на его сообщение!")

    target_id = message.reply_to_message.from_user.id
    admin_id = message.from_user.id

    if target_id == admin_id:
        return await message.answer("🤔 Ты не можешь изгнать самого себя. Для этого есть команда `.уйти`.")

    async with aiosqlite.connect("game.db") as db:
        # 1. Проверяем права изгнанника (кто кикает)
        async with db.execute("SELECT rank, empire_name, name FROM players WHERE user_id = ?", (admin_id,)) as c:
            me = await c.fetchone()
            if not me or me[0] < 10:
                return await message.answer("❌ **У вас нет власти!** Только Высший совет (Ранг 10+) может изгонять.")

        # 2. Проверяем цель (кого кикают)
        async with db.execute("SELECT rank, empire_name, name, gold FROM players WHERE user_id = ?", (target_id,)) as c:
            target = await c.fetchone()
            if not target:
                return await message.answer("❌ Этот человек не состоит в нашей летописи.")
            if target[1] != me[1]:
                return await message.answer("❌ Он не из вашей империи! Нельзя изгнать того, кто вам не служит.")
            if target[0] >= 11:
                return await message.answer("🛡 **Святотатство!** Нельзя изгнать Императора-основателя.")

        # --- НОВАЯ ФИШКА: КОНФИСКАЦИЯ И ОДИНОЧЕСТВО ---
        fine = int(target[3] * 0.10)  # 10% золота изымается в пользу правителя

        # Переводим игрока в статус одиночки (очищаем empire_name и сбрасываем ранг)
        await db.execute("""
                         UPDATE players
                         SET empire_name = NULL,
                             rank        = 1,
                             gold        = gold - ?,
                             population  = CAST(population * 0.8 AS INTEGER)
                         WHERE user_id = ?""", (fine, target_id))

        # Добавляем золото правителю
        await db.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (fine, admin_id))

        await db.commit()

        text = (
            f"👢 **АКТ ИЗГНАНИЯ**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Игрок **{target[2]}** лишен всех титулов и изгнан из **«{me[1]}»**!\n\n"
            f"⚖️ **Последствия:**\n"
            f"💰 В казну конфисковано: `{fine}` 💰\n"
            f"📉 Население сократилось на 20% (бежали за господином).\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📢 *«Твое имя будет стерто из истории нашего величия!»*"
        )
        await message.answer(text, parse_mode="Markdown")


@dp.message(F.text.lower() == ".кто я")
async def who_am_i(message: types.Message):
    async with aiosqlite.connect("game.db") as db:
        async with db.execute(
                "SELECT empire_name, rank, gold, total_mined, join_date, age, towers, soldiers, weapon_power, population, IFNULL(is_vip, 0) FROM players WHERE user_id = ?",
                (message.from_user.id,)
        ) as c:
            row = await c.fetchone()
            if not row:
                return await message.answer(
                    "👤 **Ты вольный странник.**\nСоздай империю через `.создать` или вступи в чужую.")

            # Распаковка (добавили is_vip)
            emp_name, r_id, gold, mined, join_date, age, towers, sld, wp, pop, is_vip = row

            # --- НОВАЯ ФИШКА: ВИЗУАЛЬНЫЙ СТАТУС ---
            # Расчет титула
            if sld * wp > 5000:
                status = "⚔️ Гроза морей"
            elif towers > 20:
                status = "🧱 Великий зодчий"
            else:
                status = "🌱 Начинающий лорд"

            # Прогресс-бар эпохи (допустим, для перехода нужно 10 построек)
            progress = min(10, towers)
            bar = "🟩" * progress + "⬜" * (10 - progress)

            start_dt = datetime.datetime.strptime(join_date, "%Y-%m-%d %H:%M:%S")
            days = (datetime.datetime.now() - start_dt).days
            age_label = AGES.get(age, "Каменный век 🪨")
            vip_prefix = "💎 " if is_vip else ""

            text = (
                f"{vip_prefix}**ПРОФИЛЬ: {message.from_user.first_name}**\n"
                f"📜 Статус: _{status}_\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🌍 Эпоха: `{age_label}`\n"
                f"└ {bar} `({progress * 10}%)`\n\n"
                f"🏰 Империя: **{emp_name or 'Одиночка'}**\n"
                f"🎖 Ранг: `{RANKS.get(r_id, 'Житель')}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 Золото: `{gold}` 💰\n"
                f"👥 Население: `{pop}` чел.\n"
                f"⚔️ Армия: `{sld}` чел. (сила `{wp}`)\n"
                f"⛏ Добыто за всё время: `{mined}`\n"
                f"⏳ В игре: `{days}` дн.\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            await message.answer(text, parse_mode="Markdown")


import random


@dp.message(F.text.lower() == ".работать")
async def work(message: types.Message):
    uid = message.from_user.id

    # --- СТАБИЛЬНЫЙ БЛОК ВРЕМЕНИ ---
    import datetime as dt_lib
    now = dt_lib.datetime.now()
    td = dt_lib.timedelta
    # ------------------------------

    # Проверка кулдауна (используем отдельный словарь work_cooldowns)
    if uid in work_cooldowns:
        if now < work_cooldowns[uid] + td(seconds=60):
            remaining = (work_cooldowns[uid] + td(seconds=60)) - now
            return await message.answer(f"⏳ Твои рабочие устали! Еще {remaining.seconds} сек.")

    async with aiosqlite.connect("game.db") as db:
        async with db.execute(
                "SELECT rank, towers, age, population, factories, IFNULL(is_vip, 0) FROM players WHERE user_id = ?",
                (uid,)
        ) as c:
            row = await c.fetchone()
            if not row:
                return await message.answer("❌ Ты не в империи!")

            rank, towers, age, pop, factories, is_vip = row

            # --- РАСЧЕТ РЕСУРСОВ ---
            # Убедись, что переменная age в базе не равна 0, иначе всё будет 0
            current_age = age if age > 0 else 1

            base_income = 50 * (rank * 0.5 + 1)
            total_gold = int((base_income + (pop * 2) + (towers * 20) + (factories * 500)) * current_age)
            wood_gain = int(30 * current_age)
            stone_gain = int(15 * current_age)
            iron_gain = int((factories * 10) * current_age)

            # --- СЛУЧАЙНЫЕ СОБЫТИЯ ---
            event_text = ""
            event_roll = random.randint(1, 100)

            if event_roll <= 10:  # 10% - Золотая жила
                multiplier = random.uniform(1.5, 3.0)
                total_gold = int(total_gold * multiplier)
                event_text = f"\n✨ **СОБЫТИЕ:** Найден самородок! Доход x{multiplier:.1f}!"
            elif event_roll <= 15:  # 5% - Забастовка
                total_gold //= 2
                wood_gain //= 2
                event_text = f"\n⚠️ **СОБЫТИЕ:** Забастовка рабочих! Получена лишь половина ресурсов."

            # --- VIP-БОНУС ---
            vip_text = ""
            if is_vip == 1:
                total_gold *= 2
                wood_gain *= 2
                stone_gain *= 2
                iron_gain *= 2
                vip_text = "\n💎 **VIP-бонус применен (x2)**"

            await db.execute("""
                             UPDATE players
                             SET gold        = gold + ?,
                                 wood        = wood + ?,
                                 stone       = stone + ?,
                                 iron        = iron + ?,
                                 total_mined = total_mined + ?
                             WHERE user_id = ?""",
                             (total_gold, wood_gain, stone_gain, iron_gain, total_gold, uid)
                             )
            await db.commit()

            # ЗАПИСЫВАЕМ ВРЕМЯ В ОТДЕЛЬНЫЙ СЛОВАРЬ
            work_cooldowns[uid] = now

            await message.answer(
                f"⛏ **ОТЧЕТ О РАБОТЕ**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 Золото: `+{total_gold}`\n"
                f"🪵 Дерево: `+{wood_gain}`\n"
                f"🪨 Камень: `+{stone_gain}`\n"
                f"⛓ Железо: `+{iron_gain}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🏭 Сталь (с заводов): `+{iron_gain}`"
                f"{event_text}"
                f"{vip_text}",
                parse_mode="Markdown"
            )
@dp.message(F.text.lower().startswith(".имя"))
async def rename_empire(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("❌ Напиши: `.имя Новое Название`")

    new_name = args[1]
    if len(new_name) > 20:
        return await message.answer("❌ Название слишком длинное! (макс. 20 символов)")

    uid = message.from_user.id
    price = 500

    async with aiosqlite.connect("game.db") as db:
        # Тянем данные Императора
        async with db.execute("SELECT rank, gold, empire_name, owner_id FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()

            if not row:
                return await message.answer("❌ Ты еще не основал свою династию!")

            rank, gold, old_name, owner_id = row

            if rank < 11:
                return await message.answer("❌ Только законный Император-основатель может менять имя государства!")

            if gold < price:
                return await message.answer(f"❌ Казна пуста! Нужно `{price}` 💰, а у вас всего `{gold}` 💰.")

            # --- ИСПРАВЛЕННАЯ ЛОГИКА: ОБНОВЛЯЕМ ПО OWNER_ID ---
            # Это гарантирует, что мы переименуем только СВОЮ империю,
            # даже если где-то есть империя с таким же названием.
            await db.execute(
                "UPDATE players SET empire_name = ? WHERE owner_id = ?",
                (new_name, owner_id)
            )

            # Снимаем оплату за услуги летописцев
            await db.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (price, uid))
            await db.commit()

            text = (
                f"📢 **ГОСУДАРСТВЕННЫЙ УКАЗ**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🏛 Отныне и навеки, земли, известные как «{old_name}», "
                f"будут именоваться **«{new_name}»**!\n\n"
                f"📜 Летописцы внесли правки во все карты мира.\n"
                f"💰 Из казны уплачено: `{price}` золотых."
            )
            await message.answer(text, parse_mode="Markdown")
# --- КОМАНДА УЙТИ (.уйти) ---
@dp.message(F.text.lower() == ".уйти")
async def leave_empire(message: types.Message):
    uid = message.from_user.id
    user_name = message.from_user.first_name

    async with aiosqlite.connect("game.db") as db:
        # Проверяем статус игрока
        async with db.execute("SELECT empire_name, rank FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()

            if not row or row[0] is None:
                return await message.answer("❌ Ты и так вольный странник! Тебе некуда уходить.")

            emp_name, rank = row

        if rank >= 11:
            # --- ЛОГИКА РАСПАДА (БЕЗ УДАЛЕНИЯ ЛЮДЕЙ) ---
            # Мы не удаляем записи, а делаем всех участников одиночками (empire_name = NULL)
            await db.execute(
                "UPDATE players SET empire_name = NULL, rank = 1 WHERE empire_name = ?",
                (emp_name,)
            )
            await db.commit()

            text = (
                f"💥 **КРАХ ИМПЕРИИ!**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Император **{user_name}** отрекся от престола. \n"
                f"Государство «{emp_name}» прекратило свое существование. \n\n"
                f"🏘 Все жители сохранили свои постройки, но стали вольными странниками."
            )
        else:
            # --- ЛОГИКА ВЫХОДА ОДИНОЧКИ ---
            # Игрок просто покидает фракцию, сохраняя ресурсы и здания
            await db.execute(
                "UPDATE players SET empire_name = NULL, rank = 1 WHERE user_id = ?",
                (uid,)
            )
            await db.commit()

            text = (
                f"🚪 **СВОБОДА!**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Ты покинул ряды империи «{emp_name}».\n"
                f"Твои дома и ресурсы остались при тебе, но ты больше не под защитой короны."
            )

        await message.answer(text, parse_mode="Markdown")


@dp.message(F.text.lower() == ".бонус")
async def daily_bonus(message: types.Message):
    uid = message.from_user.id
    today = datetime.date.today().isoformat()

    async with aiosqlite.connect("game.db") as db:
        async with db.execute(
                "SELECT last_daily, age, IFNULL(is_vip, 0) FROM players WHERE user_id = ?",
                (uid,)
        ) as c:
            row = await c.fetchone()

        if not row:
            return await message.answer("❌ Сначала создай империю через `.создать`!")

        last_daily, age, is_vip = row
        if last_daily == today:
            return await message.answer(
                "⏳ **Терпение, мой Лорд!**\nВаши подданные еще собирают дары. Приходите завтра!")

        # --- НОВАЯ ФИШКА: РАНДОМНЫЕ ПОДАРКИ ---
        # Базовое золото + случайный бонус от эпохи
        gold_reward = (1000 * age) + random.randint(100, 500)
        wood_reward = random.randint(50, 200) * age

        # Если VIP, удваиваем награду
        multiplier = 2 if is_vip else 1
        gold_reward *= multiplier
        wood_reward *= multiplier

        # Обновляем базу
        await db.execute(
            "UPDATE players SET gold = gold + ?, wood = wood + ?, last_daily = ? WHERE user_id = ?",
            (gold_reward, wood_reward, today, uid)
        )
        await db.commit()

        vip_star = "🌟" if is_vip else "📦"
        text = (
            f"{vip_star} **ЕЖЕДНЕВНЫЙ СУНДУК ОТКРЫТ!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Золото: `+{gold_reward}`\n"
            f"🪵 Материалы: `+{wood_reward}` дерева\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 Чем выше ваша эпоха, тем ценнее дары в сундуке!"
        )
        if is_vip:
            text += "\n💎 *Применен бонус VIP x2!*"

        await message.answer(text, parse_mode="Markdown")


@dp.message(F.text.lower().startswith(".выше") | F.text.lower().startswith(".ниже"))
async def change_rank(message: types.Message):
    if not message.reply_to_message:
        return await message.answer("📜 **Указ:** Ответьте на сообщение того, чей статус хотите изменить!")

    cmd_parts = message.text.split()
    try:
        new_rank = int(cmd_parts[-1])
    except (ValueError, IndexError):
        return await message.answer("🔢 Укажите числовой индекс ранга после команды (например: `.выше 5`)")

    # Валидация границ ранга
    if new_rank >= 11:
        return await message.answer("❌ **Святотатство!** Трон Императора не может быть занят вторым лицом.")
    if new_rank < 1:
        new_rank = 1  # Ранг не может быть меньше 1

    admin_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id

    if admin_id == target_id:
        return await message.answer("🤔 Самоназначение запрещено уставом империи!")

    async with aiosqlite.connect("game.db") as db:
        # 1. Данные того, кто отдает приказ (Админ)
        async with db.execute("SELECT rank, empire_name FROM players WHERE user_id = ?", (admin_id,)) as c:
            admin_row = await c.fetchone()
            if not admin_row or admin_row[0] < 10:
                return await message.answer("❌ У вас нет полномочий для изменения титулов (нужен ранг 10+).")

        # 2. Данные того, кого повышают/понижают (Цель)
        async with db.execute("SELECT rank, empire_name, name FROM players WHERE user_id = ?", (target_id,)) as c:
            target_row = await c.fetchone()
            if not target_row:
                return await message.answer("❌ Этот человек не числится в списках игроков.")

            # ПРОВЕРКА: Из одной ли они империи?
            if target_row[1] != admin_row[1]:
                return await message.answer("❌ Вы не можете командовать в чужом государстве!")

            # ПРОВЕРКА: Не пытается ли админ прыгнуть выше головы?
            if new_rank >= admin_row[0]:
                return await message.answer(
                    f"❌ Вы не можете назначить ранг `{new_rank}`, так как ваш собственный — `{admin_row[0]}`.")

            # ПРОВЕРКА: Не пытается ли админ понизить того, кто выше него?
            if target_row[0] > admin_row[0]:
                return await message.answer("❌ Вы не имеете права изменять статус старшего по званию!")

        # 3. Применение указа
        await db.execute("UPDATE players SET rank = ? WHERE user_id = ?", (new_rank, target_id))
        await db.commit()

        rank_name = RANKS.get(new_rank, 'Житель')
        await message.answer(
            f"🎖 **НОВЫЙ ТИТУЛ**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Имя: **{target_row[2]}**\n"
            f"📜 Звание: `{rank_name}` (Ранг: {new_rank})\n"
            f"⚖️ Статус: Указ вступил в силу немедленно."
        )


@dp.message(F.text.lower().startswith(".нанять воинов"))
async def buy_soldiers(message: types.Message):
    uid = message.from_user.id
    args = message.text.split()

    # 1. Считываем количество (если не указано, берем 10 по умолчанию)
    try:
        count = int(args[-1]) if args[-1].isdigit() else 10
    except (ValueError, IndexError):
        count = 10

    if count < 1:
        return await message.answer("❌ Вы не можете нанять меньше одного воина!")

    price_per_one = 50  # 500 за 10 = 50 за 1
    total_price = count * price_per_one

    async with aiosqlite.connect("game.db") as db:
        async with db.execute(
                "SELECT gold, soldiers, houses FROM players WHERE user_id = ?",
                (uid,)
        ) as c:
            row = await c.fetchone()

        if not row:
            return await message.answer("❌ Сначала создай империю!")

        gold, current_soldiers, houses = row

        # 2. ПРОВЕРКА ЛИМИТА АРМИИ (20 мест на 1 дом)
        max_soldiers = houses * 20

        if current_soldiers + count > max_soldiers:
            can_hire = max_soldiers - current_soldiers
            if can_hire <= 0:
                return await message.answer(
                    f"🏘 **Бараки переполнены!**\n"
                    f"У вас `{houses}` домов, лимит армии: `{max_soldiers}`.\n"
                    f"Чтобы нанять больше, стройте новые дома!"
                )
            else:
                return await message.answer(
                    f"🏘 **Недостаточно места!**\n"
                    f"Вы пытаетесь нанять `{count}`, но мест осталось только на `{can_hire}` воинов."
                )

        # 3. ПРОВЕРКА ЗОЛОТА
        if gold < total_price:
            return await message.answer(
                f"❌ Казна пуста! Для найма `{count}` воинов нужно `{total_price}` 💰\n"
                f"Ваш баланс: `{gold}` 💰"
            )

        # 4. БОНУСНОЕ СОБЫТИЕ (Масштабируем бонус под размер отряда)
        bonus_text = ""
        final_amount = count
        # Если отряд большой, шанс на бонус выше или ветеранов больше
        if random.randint(1, 100) <= 15:
            # Бонус ветеранов: 10% от нанимаемого числа
            bonus_soldiers = max(1, int(count * 0.2))
            final_amount += bonus_soldiers
            bonus_text = f"\n✨ **Славный призыв!** К вашему отряду примкнуло `{bonus_soldiers}` опытных ветеранов бесплатно."

        # 5. ЗАПИСЬ В БАЗУ
        await db.execute(
            "UPDATE players SET gold = gold - ?, soldiers = soldiers + ? WHERE user_id = ?",
            (total_price, final_amount, uid)
        )
        await db.commit()

        await message.answer(
            f"⚔️ **Военный трибунал докладывает:**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🗡 Нанято рекрутов: `{count}`\n"
            f"💰 Потрачено: `{total_price}` золотых\n"
            f"📊 Общая мощь: `{current_soldiers + final_amount}` воинов\n"
            f"{bonus_text}",
            parse_mode="Markdown"
        )

        # Если у тебя есть квесты на армию, можно добавить проверку тут
        # await check_quest(uid, "army", message)
@dp.message(F.text.lower() == ".магазин")
async def shop(message: types.Message):
    # Можно добавить запрос к базе, чтобы показывать баланс игрока прямо в магазине
    uid = message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT gold, age FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()

    gold_balance = row[0] if row else 0
    age = row[1] if row else 1
    age_name = AGES.get(age, "Эпоха")

    text = (
        f"🏢 **ЦЕНТРАЛЬНЫЙ РЫНОК ({age_name})**\n"
        f"💰 Твой баланс: `{gold_balance}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏰 **АРХИТЕКТУРА**\n"
        f"🏠 **Жилой дом**\n"
        f"└ Цена: `500` 💰 | `+500` к лимиту склада\n"
        f"└ Команда: `.построить дом`\n\n"
        f"🗼 **Сторожевая башня**\n"
        f"└ Цена: `1000` 💰 | `+5%` к шансу защиты\n"
        f"└ Команда: `.купить башню`\n\n"
        f"⚔️ **ВОЕННЫЙ ЛАГЕРЬ**\n"
        f"🗡 **Нанять отряд (10 чел.)**\n"
        f"└ Цена: `500` 💰 | Сила зависит от оружия\n"
        f"└ Команда: `.нанять воинов`\n\n"
        f"⚒ **Купить оружие**\n"
        f"└ Цена: По эпохе | Увеличивает мощь армии\n"
        f"└ Команда: `.купить оружие`\n\n"
        f"📦 **РЕСУРСЫ**\n"
        f"🪵 **Дерево (100 ед.)** — `300` 💰\n"
        f"🪨 **Камень (100 ед.)** — `600` 💰\n"
        f"└ Команда: `.купить дерево` / `.купить камень`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 *В следующей эпохе товары станут дороже, но мощнее!*"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text.lower().startswith(".казино"))
async def casino_cmd(message: types.Message):
    uid = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        return await message.answer("🎰 **Укажи ставку!**\nПример: `.казино 100` или `.казино ва-банк`")

    async with aiosqlite.connect("game.db") as db:
        async with db.execute("SELECT gold, empire_name, owner_id FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            if not row: return

            gold, emp_name, owner_id = row

            # Обработка ставки
            if args[1].lower() == "ва-банк":
                bet = gold
            else:
                try:
                    bet = int(args[1])
                except:
                    return await message.answer("❌ Ставка должна быть числом или `ва-банк`!")

            if bet < 10:
                return await message.answer("❌ Минимальная ставка — 10 💰")

            if gold < bet:
                return await message.answer(f"❌ Недостаточно золота! В казне всего: `{gold}` 💰")

            # --- СИСТЕМА ИКСОВ ---
            multipliers = [0, 0.5, 1.0, 1.5, 2.0, 5.0, 15.0]
            weights = [40, 20, 15, 10, 8, 5, 2]  # 40% на полный слив

            multiplier = random.choices(multipliers, weights=weights)[0]
            win_amount = int(bet * multiplier)

            # --- НОВАЯ ФИШКА: НАЛОГ И КАЗНА ---
            # Если игрок проиграл, 5% от его ставки идет Императору его империи (если он не сам Император)
            tax_text = ""
            if multiplier < 1 and emp_name and uid != owner_id:
                tax = int(bet * 0.05)
                await db.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (tax, owner_id))
                tax_text = f"\n🏛 *Налог штата (5%):* `{tax}` 💰 *ушли в казну.*"

            new_gold = gold - bet + win_amount
            await db.execute("UPDATE players SET gold = ? WHERE user_id = ?", (new_gold, uid))
            await db.commit()

            # Красивое оформление слотов
            slots = ["🍒", "🍋", "💎", "7️⃣", "🔔"]
            line = "".join(random.choices(slots, k=3))

            if multiplier >= 2:
                status = f"🌟 **ВЕЛИКИЙ КУШ!** (x{multiplier})"
            elif multiplier == 1:
                status = "⚖️ **ВОЗВРАТ СТАВКИ**"
            else:
                status = "💨 **ПРОИГРЫШ**"

            await message.answer(
                f"🎰 **КАЗИНО: {line}**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 Игрок: **{message.from_user.first_name}**\n"
                f"💰 Ставка: `{bet}`\n"
                f"📊 Итог: {status}\n\n"
                f"💵 Выигрыш: `+{win_amount}` 💰\n"
                f"🏦 Баланс: `{new_gold}` 💰"
                f"{tax_text}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )


@dp.message(F.text.lower().startswith(".построить"))
async def build_anything(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.answer(
            "🏗 **Меню строительства**\n"
            "Использование: `.построить [тип] [кол-во]`\n"
            "Пример: `.построить башня 3`\n\n"
            "🏠 дом | 🚜 ферма | 🗼 башня | 🏭 завод"
        )

    # 1. Определяем тип здания и количество
    target = args[1].lower()
    try:
        count = int(args[2]) if len(args) > 2 else 1
    except ValueError:
        return await message.answer("❌ Количество должно быть числом!")

    if count < 1:
        return await message.answer("❌ Нельзя построить меньше одного здания.")
    if count > 10000:
        return await message.answer("❌ Указ: нельзя строить более 10000 зданий за раз.")

    # 2. Параметры зданий: цена, ресурс, колонка в БД, прирост населения
    config = {
        "дом": {"gold": 500, "res": "wood", "res_price": 200, "col": "houses", "pop": 10},
        "ферма": {"gold": 1200, "res": "wood", "res_price": 500, "col": "farms", "pop": 40},
        "башня": {"gold": 1000, "res": "stone", "res_price": 300, "col": "towers", "pop": 0},
        "завод": {"gold": 3000, "res": "stone", "res_price": 1000, "col": "factories", "pop": 0}
    }

    if target not in config:
        return await message.answer("❌ Такого чертежа нет! Выберите: дом, ферма, башня или завод.")

    conf = config[target]
    total_gold = conf["gold"] * count
    total_res = conf["res_price"] * count
    res_name = conf["res"]  # 'wood' или 'stone'
    res_label = "🪵 Дерево" if res_name == "wood" else "🪨 Камень"

    uid = message.from_user.id
    async with aiosqlite.connect("game.db") as db:
        # Тянем текущие ресурсы игрока
        async with db.execute(f"SELECT gold, {res_name}, {conf['col']} FROM players WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
            if not row: return await message.answer("❌ Сначала создай империю!")

            u_gold, u_res, u_current_builds = row

        # 3. Проверка ресурсов
        if u_gold < total_gold:
            return await message.answer(f"❌ Недостаточно золота! Нужно: `{total_gold}` 💰")
        if u_res < total_res:
            return await message.answer(f"❌ Недостаточно материалов! Нужно: `{total_res}` {res_label}")

        # 4. Обновление базы данных
        await db.execute(f"""
            UPDATE players 
            SET gold = gold - ?, 
                {res_name} = {res_name} - ?, 
                {conf['col']} = {conf['col']} + ?, 
                population = population + ?
            WHERE user_id = ?""",
                         (total_gold, total_res, count, conf['pop'] * count, uid)
                         )
        await db.commit()

    # 5. Красивый отчет
    pop_bonus = f"\n👥 Жители: `+{conf['pop'] * count}`" if conf['pop'] > 0 else ""
    await message.answer(
        f"🛠 **СТРОЙКА ЗАВЕРШЕНА**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔨 Возведено: `{count}` ед. (**{target}**)\n"
        f"💰 Затраты: `{total_gold}` золота\n"
        f"📦 Материалы: `{total_res}` {res_label}"
        f"{pop_bonus}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏰 Теперь у вас `{u_current_builds + count}` зданий этого типа.",
        parse_mode="Markdown"
    )

# --- ГЛАВНЫЙ ЦИКЛ ---
async def main():
    await init_db()
    print("🛡 Бот в сети!")
    while True:
        try:
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}. Рестарт...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Выключен.")
