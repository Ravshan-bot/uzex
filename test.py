import requests
from bs4 import BeautifulSoup
import logging
import asyncio
import re
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = '#########'  # 👈 Bot tokenni shu yerga yozing 
CHANNEL_ID = '########'  # 👈 Kanal username (masalan: @uzex_yangiliklar) 


CONTRACT_FILE_SULFAT = r'/root/uzex/sulfat.txt'
CONTRACT_FILE_KARBAMID = r'/root/uzex/karbamid.txt'
CONTRACT_FILE_AMMAFOS = r'/root/uzex/ammafos.txt'
CONTRACT_FILE_SUPREFOS = r'/root/uzex/suprefos.txt'


URLS = {
    
    'Сульфат': 'https://www.uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=сульфат',
    'Карбамид': 'https://www.uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=Карбамид',
    'Аммофос': 'https://uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=Аммофос',
    'Супрефос': 'https://uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=Супрефос',
    
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
    for attempt in range(3):
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}, timeout=120)
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

def extract_volume_and_price(cols):
    try:
        hajm = int(cols[3].replace(" ", "").replace(",", ""))
        soni = int(cols[6].replace(" ", "").replace(",", ""))
        narx = cols[5]  # 5-ustun
        if hajm > 1000000:
            hajm = hajm // 1000
        umumiy = hajm * soni
        birlik = f"({umumiy}) кг" if umumiy < 1000 else f"({round(umumiy / 1000, 2)}) т"
        return birlik, narx
    except:
        return "(hajm topilmadi)", "(narx topilmadi)"

async def fetch_and_send(file_path, product_name):
    contracts = load_contract_data(file_path)
    uzex_rows = fetch_uzex_data(product_name)
    messages = []
    for cols in uzex_rows:
        contract_number = cols[0].strip()
        if contract_number in contracts:
            full_info = contracts[contract_number]
            hajm_text, narx = extract_volume_and_price(cols)
            text = f"{contract_number} {full_info} {hajm_text} | {narx}"
            messages.append(text)
    if messages:
        final_message = f"#{product_name}\n\n" + "\n\n".join(messages)
        try:
            await bot.send_message(chat_id=CHANNEL_ID, text=final_message)
            logging.info("[Yuborildi] Xabarlar kanalda e’lon qilindi.")
        except Exception as e:
            logging.error(f"[Xatolik] Telegramga yuborishda: {e}")

async def daily_check():
    await fetch_and_send(CONTRACT_FILE_SULFAT, "Сульфат")
    await fetch_and_send(CONTRACT_FILE_KARBAMID, "Карбамид")
    await fetch_and_send(CONTRACT_FILE_AMMAFOS, "Аммофос")
    #await fetch_and_send(CONTRACT_FILE_SUPREFOS, "Супрефос")
    

def schedule_daily_job():
    scheduler = BackgroundScheduler(timezone='Asia/Tashkent')
    scheduler.add_job(lambda: asyncio.run(daily_check()), trigger='cron', hour=9, minute=51)
    scheduler.add_job(lambda: asyncio.run(daily_check()), trigger='cron', hour=14, minute=51)
    scheduler.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ishga tushdi.")

if __name__ == '__main__':
    schedule_daily_job()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    print("🤖 Bot ishga tushdi.")
    app.run_polling()
# Eng yahshi va mengga yoqqan maqbul variant










