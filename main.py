import asyncio
import html
import time
from pathlib import Path
import aiohttp
import feedparser
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
RSS_URL = 'https://ria.ru/export/rss2/archive/index.xml'

IMG_DIR = Path(__file__).resolve().parent / 'images'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0'}

TABS = {
    'main': ('Главное', RSS_URL, ' '),
    'politics': ('Политика', 'https://ria.ru/politics/', ' '),
    'world': ('В мире', 'https://ria.ru/world/', ' '),
    'economy': ('Экономика', 'https://ria.ru/economy/', ' '),
}

cache: dict[str, tuple[float, list[dict]]] = {}
last_msg: dict[int, int] = {}

bot = Bot(token=BOT_TOKEN)


async def fetch(url: str) -> str:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as s:
        async with s.get(url) as r:
            r.raise_for_status()
            return await r.text()


async def get_news(tab: str) -> list[dict]:
    """Берёт новости из кеша (если ему < 5 минут) или скачивает с сайта."""
    if tab in cache and time.time() - cache[tab][0] < 300:
        return cache[tab][1]



    if url.endswith('.xml'):
        for e in feedparser.parse(data).entries[:10]:
            if e.get('title') and e.get('link'):
                items.append({'title': e.title.strip(), 'link': e.link.strip()})
    else:
        soup = BeautifulSoup(data, 'html.parser')
        seen = set()
        for a in soup.select('a.list-item__title'):
            title, link = a.get_text(strip=True), a.get('href', '').strip()
            if link.startswith('/'):
                link = 'https://ria.ru' + link
            if title and link and link not in seen:
                seen.add(link)
                items.append({'title': title, 'link': link})
                if len(items) == 10:
                    break




# ---------- ЭКРАНЫ И КНОПКИ ----------
async def send_screen(chat_id: int, text: str, kb: InlineKeyboardMarkup, img: str | None = None, del_id: int | None = None):
    """Удаляет прошлое сообщение и шлёт новое (с фото или текстом)."""
    for msg_id in {del_id, last_msg.get(chat_id)}:
        if msg_id:
            try:
                await bot.delete_message(chat_id, msg_id)
            except TelegramBadRequest:
                pass

    path = IMG_DIR / img if img else None
    sent = None
    if path and path.exists() and len(text) <= 1024:
        try:
            sent = await bot.send_photo(chat_id, FSInputFile(path), caption=text, parse_mode='HTML', reply_markup=kb)
        except Exception as e:
            print(f"Ошибка фото ({img}): {e}")





# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(msg: Message):
    try:
        await msg.delete()
    except TelegramBadRequest:
        pass
    await send_screen(msg.chat.id, "<b>Новости РИА</b>\n\nВыбери раздел:", 'musia.png')

@dp.message(Command("clear"))
async def cmd_clear(msg: Message):
    ids = list(range(max(1, msg.message_id - 99), msg.message_id + 1))
    try:
        await bot.delete_messages(msg.chat.id, ids)
    except TelegramBadRequest:
        pass


@dp.message(Command("admin"))
async def cmd_admin(msg: Message):
    try:
        await msg.delete()
    except TelegramBadRequest:
        pass
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать админу", url="https://t.me/kapustik33")],
        [InlineKeyboardButton(text="« К разделам", callback_data="menu")],
    ])
    await send_screen(msg.chat.id, "По всем вопросам пиши админу: @kapustik33", kb)



async def channel_poster():
    """Каждые 3 минуты проверяет RSS и шлёт новые новости в канал."""
    sent_links = set()
    first_run = True

    while True:
        try:
            feed = feedparser.parse(await fetch(RSS_URL))
            for e in feed.entries:
                title, link = e.get('title', '').strip(), e.get('link', '').strip()
                if not title or not link or link in sent_links:
                    continue

                sent_links.add(link)
                if first_run:
                    continue

                text = f'📰 <b>{html.escape(title)}</b>\n\n🔗 <a href="{link}">Читать на РИА</a>'
                await bot.send_message(CHANNEL_ID, text, parse_mode='HTML')
                await asyncio.sleep(1.5)

            first_run = False
        except Exception as e:
            print(f"Ошибка автопостинга в канал: {e}")

        await asyncio.sleep(180)  # пауза 3 минуты


# ---------- ЭКРАНЫ И КНОПКИ ----------
async def send_screen(chat_id: int, text: str, kb: InlineKeyboardMarkup, img: str | None = None, del_id: int | None = None):
    """Удаляет прошлое сообщение и шлёт новое (с фото или текстом)."""
    for msg_id in {del_id, last_msg.get(chat_id)}:
        if msg_id:
            try:
                await bot.delete_message(chat_id, msg_id)
            except TelegramBadRequest:
                pass

    path = IMG_DIR / img if img else None
    sent = None
    if path and path.exists() and len(text) <= 1024:
        try:
            sent = await bot.send_photo(chat_id, FSInputFile(path), caption=text, parse_mode='HTML', reply_markup=kb)
        except Exception as e:
            print(f"Ошибка фото ({img}): {e}")


def kb_tabs():
    btns = [InlineKeyboardButton(text=t[0], callback_data=f"tab_{k}") for k, t in TABS.items()]
    return InlineKeyboardMarkup(inline_keyboard=[btns[i:i + 2] for i in range(0, len(btns), 2)])


def kb_news(tab: str, n: int):
    btns = [InlineKeyboardButton(text=str(i + 1), callback_data=f"news_{tab}_{i}") for i in range(n)]
    rows = [btns[i:i + 5] for i in range(0, n, 5)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_article(tab: str, link: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть на сайте", url=link)],
    ])