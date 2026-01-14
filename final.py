import requests
from bs4 import BeautifulSoup
import logging
import asyncio
import re
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = '8151910728:AAHNCqm4h2_ELW2TbsUGzPWrl218j8HKWQs'  # 👈 Bot tokenni shu yerga yozing 
CHANNEL_ID = '@brok_on'  # 👈 Kanal username (masalan: @uzex_yangiliklar) 

CONTRACT_FILE_KARBAMID = r'C:\Users\bot\final\karbamid.txt'
CONTRACT_FILE_SULFAT = r'C:\Users\bot\final\sulfat.txt'

URLS = {
    'Карбамид': 'https://www.uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=Карбамид',
    'Сульфат': 'https://www.uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=сульфат',
}

bot = Bot(token=BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

def clean_contract_number(text):
    match = re.search(r'\*{6}(\d+)\*{6}', text)
    return match.group(1) if match else text.strip()

def load_contract_data(file_path):
    contracts = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r'\*{6}(\d{6,})\*{6}\s*---(.*?)---', line)
            if match:
                contract_number = match.group(1).strip()
                full_info = match.group(2).strip()
                contracts[contract_number] = full_info
    return contracts

def fetch_uzex_data(product_name):
    url = URLS[product_name]
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table tbody tr')
        return [
            [td.text.strip() for td in row.select('td')]
            for row in rows
        ]
    except Exception as e:
        logging.error(f"[Xatolik] UZEX ma'lumotini olishda: {e}")
        return []

def extract_volume(cols):
    try:
        hajm = int(cols[3].replace(" ", "").replace(",", ""))
        soni = int(cols[6].replace(" ", "").replace(",", ""))
        if hajm > 1000000:
            hajm = hajm // 1000
        umumiy = hajm * soni
        return f"({umumiy}) кг" if umumiy < 1000 else f"({round(umumiy / 1000, 2)}) тонна"
    except:
        return "(hajm topilmadi)"

async def fetch_and_send(file_path, product_name):
    contracts = load_contract_data(file_path)
    uzex_rows = fetch_uzex_data(product_name)
    messages = []
    for cols in uzex_rows:
        contract_number = cols[0].strip()
        if contract_number in contracts:
            full_info = contracts[contract_number]
            hajm_text = extract_volume(cols)
            text = f"{contract_number} {full_info} {hajm_text}"
            messages.append(text)
    if messages:
        final_message = f"#{product_name}\n\n" + "\n\n".join(messages)
        try:
            await bot.send_message(chat_id=CHANNEL_ID, text=final_message)
            logging.info("[Yuborildi] Xabarlar kanalda e’lon qilindi.")
        except Exception as e:
            logging.error(f"[Xatolik] Telegramga yuborishda: {e}")

async def fetch_and_send_karbamid():
    await fetch_and_send(CONTRACT_FILE_KARBAMID, "Карбамид")

async def fetch_and_send_sulfat():
    await fetch_and_send(CONTRACT_FILE_SULFAT, "Сульфат")

def schedule_daily_job():
    scheduler = BackgroundScheduler(timezone='Asia/Tashkent')
    scheduler.add_job(lambda: asyncio.run(fetch_and_send_karbamid()), trigger='cron', hour=10, minute=50)
    scheduler.add_job(lambda: asyncio.run(fetch_and_send_sulfat()), trigger='cron', hour=15, minute=0)
    scheduler.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ishga tushdi.")

if __name__ == '__main__':
    schedule_daily_job()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    print("🤖 Bot ishga tushdi.")
    app.run_polling()
