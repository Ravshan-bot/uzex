import requests
from bs4 import BeautifulSoup
import logging
import asyncio
import re
import time
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- SOZLAMALAR ---
BOT_TOKEN = '8151910728:AAHNCqm4h2_ELW2TbsUGzPWrl218j8HKWQs'  
CHANNEL_ID = '@brok_on'  

CONTRACT_FILES = {
    'Карбамид': r'/root/uzex/uzex/uzex/karbamid.txt',
    'Сульфат': r'/root/uzex/uzex/uzex/sulfat.txt',
    'Аммофос': r'/root/uzex/uzex/uzex/ammafos.txt',
    'Супрефос': r'/root/uzex/uzex/uzex/suprefos.txt'
}

URLS = {
    'Карбамид': 'https://www.uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=Карбамид',
    'Сульфат': 'https://www.uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=сульфат',
    'Аммофос': 'https://uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=Аммофос',
    'Супрефос': 'https://uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=Супрефос',
}

bot = Bot(token=BOT_TOKEN)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_contract_data(file_path):
    """Fayldan kontraktlarni o'ta aniqlik bilan yuklash"""
    contracts = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Universal regex: har qanday formatdagi kontraktni ilib oladi
                match = re.search(r'\*+(\d+)\*+\s*-+(.*?)(?:-|$)', line)
                if match:
                    contract_number = match.group(1).strip()
                    full_info = match.group(2).strip().rstrip('-').strip()
                    contracts[contract_number] = full_info
        logging.info(f"💾 {file_path} dan {len(contracts)} ta kontrakt yuklandi.")
    except Exception as e:
        logging.error(f"❌ Fayl o'qishda xatolik ({file_path}): {e}")
    return contracts

def fetch_uzex_data(product_name):
    """Saytdan ma'lumotni majburiy (retry) olish"""
    url = URLS[product_name]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for attempt in range(3): # 3 marta urinish
        try:
            response = requests.get(url, headers=headers, timeout=120)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select('table tbody tr')
            
            # Agar jadvalda ma'lumot bo'lsa, qaytaramiz
            if rows and len(rows) > 0:
                logging.info(f"✅ {product_name}: {len(rows)} ta qator olindi.")
                return [[td.text.strip() for td in row.select('td')] for row in rows]
            
            logging.warning(f"⚠️ {product_name}: Jadval bo'sh (Urinish {attempt+1})")
        except Exception as e:
            logging.error(f"❌ {product_name} (Urinish {attempt+1}) xato: {e}")
            time.sleep(10) # 10 soniya kutib qayta urinish
            
    return []

def extract_volume_and_price(cols):
    """Hajm va narxni hisoblash"""
    try:
        hajm = int(cols[3].replace(" ", "").replace(",", ""))
        soni = int(cols[6].replace(" ", "").replace(",", ""))
        narx = cols[5]
        if hajm > 1000000: hajm = hajm // 1000
        umumiy = hajm * soni
        birlik = f"({umumiy}) кг" if umumiy < 1000 else f"({round(umumiy / 1000, 2)}) т"
        return birlik, narx
    except:
        return "(hajm topilmadi)", "(narx topilmadi)"

async def fetch_and_send(product_name):
    """Kontraktlarni majburiy tekshirish va yuborish"""
    file_path = CONTRACT_FILES[product_name]
    contracts = load_contract_data(file_path)
    
    if not contracts:
        return

    uzex_rows = fetch_uzex_data(product_name)
    
    # Agar 3 ta urinishda ham sayt bermasa, xabar beramiz
    if not uzex_rows:
        logging.error(f"‼️ {product_name} bo'yicha saytdan ma'lumot olib bo'lmadi.")
        return

    messages = []
    found_contracts = set()

    for cols in uzex_rows:
        if len(cols) < 7: continue
        
        contract_number = cols[0].strip()
        
        if contract_number in contracts:
            full_info = contracts[contract_number]
            hajm_text, narx = extract_volume_and_price(cols)
            text = f"🔹 **{contract_number}**\n📝 {full_info}\n📊 {hajm_text} | 💰 {narx}"
            messages.append(text)
            found_contracts.add(contract_number)

    # Natijani yuborish
    if messages:
        header = f"⚡️ #{product_name} bo'yicha yangi ma'lumotlar:\n\n"
        # Xabar uzunligini tekshirish (Telegram limiti 4096)
        chunk = header
        for msg in messages:
            if len(chunk) + len(msg) > 3900:
                await bot.send_message(chat_id=CHANNEL_ID, text=chunk, parse_mode='Markdown')
                chunk = ""
            chunk += msg + "\n\n"
        
        if chunk:
            await bot.send_message(chat_id=CHANNEL_ID, text=chunk, parse_mode='Markdown')
        
        logging.info(f"📢 {product_name} bo'yicha {len(found_contracts)} ta kontrakt e'lon qilindi.")

async def daily_check():
    """Barcha mahsulotlarni navbat bilan tekshirish"""
    for product in URLS.keys():
        await fetch_and_send(product)
        await asyncio.sleep(5) # Serverga bosimni kamaytirish uchun

def schedule_daily_job():
    scheduler = BackgroundScheduler(timezone='Asia/Tashkent')
    # Tekshiruv vaqtlari
    scheduler.add_job(lambda: asyncio.run(daily_check()), trigger='cron', hour=10, minute=0)
    scheduler.add_job(lambda: asyncio.run(daily_check()), trigger='cron', hour=14, minute=50)
    scheduler.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Uzex Monitoring Bot ishga tushdi.")

if __name__ == '__main__':
    schedule_daily_job()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    print("🤖 Bot Monitoring rejimida ishga tushdi...")
    app.run_polling()


# Eng yahshi va mengga yoqqan maqbul variant






