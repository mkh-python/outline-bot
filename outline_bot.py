import os
import logging
import coloredlogs
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import CallbackQueryHandler

import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    ConversationHandler,
    filters,
)
from dotenv import load_dotenv

# بارگذاری پیکربندی از فایل .env
load_dotenv('/root/outline-bot/config.env')

# تنظیمات سرور Outline
OUTLINE_API_URL = os.getenv("OUTLINE_API_URL")
OUTLINE_API_KEY = os.getenv("OUTLINE_API_KEY")
CERT_SHA256 = os.getenv("CERT_SHA256")
DATA_FILE = "users_data.json"

# تنظیم مسیر فایل‌ها
BASE_PATH = "/root/outline-bot"
DATA_FILE = f"{BASE_PATH}/users_data.json"
MONITORING_FILE = f"{BASE_PATH}/monitoring_list.json"
BLACKLIST_FILE = f"{BASE_PATH}/blacklist.json"
LOG_FILE = f"{BASE_PATH}/bot_logs.log"


# اطلاعات نسخه
CURRENT_VERSION = "1.37.3"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/irannetwork/outline-bot/main/version.txt"
GITHUB_REPO_URL = "https://github.com/irannetwork/outline-bot.git"

# متغیر برای ذخیره وضعیت اتصال کاربران
connection_status = {}

# تنظیمات اصلی لاگ
LOG_FILE = "/root/outline-bot/bot_logs.log"

# تنظیم لاگر
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# تنظیم لاگ فایل
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)  # ذخیره همه لاگ‌ها در فایل
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# تنظیم لاگ کنسول
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # نمایش لاگ‌های مهم‌تر در کنسول
coloredlogs.install(
    level='INFO',
    fmt="%(asctime)s - %(levelname)s - %(message)s",
    logger=logger
)
logger.addHandler(console_handler)



# مراحل گفتگو
GET_USER_NAME = 1
GET_SUBSCRIPTION_DURATION = 2
GET_USER_ID = 3

# دکمه‌های منوی اصلی
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🆕 ایجاد کاربر", "👥 مشاهده کاربران"],
        ["❌ حذف کاربر", "💬 چت با پشتیبانی"],
        ["🔄 آپدیت ربات", "🚫 مدیریت مسدودی‌ها"]  # دکمه جدید اضافه شد
    ],
    resize_keyboard=True,
)


# آیدی مدیران
ADMIN_IDS = [int(os.getenv("ADMIN_ID"))]

# تابع بررسی آپدیت
async def check_for_update(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = user.id
    await update.message.reply_text("در حال بررسی نسخه جدید... لطفاً صبر کنید.")

    try:
        # دریافت نسخه آخر از گیت‌هاب
        response = requests.get(GITHUB_VERSION_URL)
        response.raise_for_status()
        latest_version = response.text.strip()

        if latest_version == CURRENT_VERSION:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ شما از آخرین نسخه ربات ({CURRENT_VERSION}) استفاده می‌کنید."
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"نسخه جدید موجود است: {latest_version}\nدر حال آپدیت ربات..."
            )
            # اجرای فرآیند آپدیت
            update_success = update_bot()
            if update_success:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ آپدیت به نسخه {latest_version} با موفقیت انجام شد. ربات ری‌استارت شد!"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ خطا در فرآیند آپدیت. لطفاً مجدداً تلاش کنید."
                )
    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ خطا در بررسی نسخه جدید: {e}"
        )

# تابع آپدیت ربات
def update_bot():
    try:
        # کلون کردن مخزن جدید
        os.system(f"git clone {GITHUB_REPO_URL} /tmp/outline-bot")
        # جایگزینی فایل‌ها
        os.system("cp -r /tmp/outline-bot/* /root/")
        # حذف مخزن موقت
        os.system("rm -rf /tmp/outline-bot")
        # ری‌استارت کردن سرویس ربات
        os.system("systemctl restart telegram-bot.service")
        return True
    except Exception as e:
        logger.error(f"Error updating bot: {e}")
        return False

# هندلر برای "چت با پشتیبانی"
async def chat_with_support(update: Update, context: CallbackContext):
    # ایجاد لینک برای چت با شما
    support_link = "https://t.me/irannetwork_co"
    await update.message.reply_text(
        "برای ارتباط با پشتیبانی، روی لینک زیر کلیک کنید:",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📩 چت با پشتیبانی", url=support_link)]]
        ),
    )


# مدیریت اطلاعات کاربران
def load_user_data():
    try:
        with open(DATA_FILE, "r") as file:
            data = json.load(file)
            if "next_id" not in data:
                data["next_id"] = 1
            if "users" not in data:
                data["users"] = {}
            return data
    except FileNotFoundError:
        # ایجاد فایل با مقدار پیش‌فرض
        initial_data = {"next_id": 1, "users": {}}
        save_user_data(initial_data)
        return initial_data

def save_user_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# بررسی کاربران منقضی‌شده
def check_expired_users():
    user_data = load_user_data()["users"]
    today = datetime.now().date()
    expired_users = [
        user_id for user_id, details in user_data.items()
        if datetime.strptime(details["expiry_date"], "%Y-%m-%d").date() < today
    ]
    return expired_users

def remove_expired_users():
    expired_users = check_expired_users()
    if expired_users:
        user_data = load_user_data()
        for user_id in expired_users:
            response = requests.delete(
                f"{OUTLINE_API_URL}/access-keys/{user_id}",
                headers={"Authorization": f"Bearer {OUTLINE_API_KEY}"},
                verify=False,
            )
            if response.status_code == 204:
                user_data["users"].pop(user_id, None)
                save_user_data(user_data)
                logger.info(f"کاربر منقضی‌شده با شناسه {user_id} حذف شد.")

# تابع بررسی دسترسی
def is_admin(update: Update) -> bool:
    return update.effective_user.id in ADMIN_IDS

# شروع ربات
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if not is_admin(update):
        logger.warning(f"Unauthorized access attempt by {user.first_name} ({user.id})")
        await update.message.reply_text("شما مجاز به استفاده از این ربات نیستید.")
        return
    logger.info(f"User {user.first_name} ({user.id}) started the bot.")
    await update.message.reply_text(
        "سلام! برای مدیریت سرور Outline یکی از گزینه‌های زیر را انتخاب کنید.",
        reply_markup=MAIN_KEYBOARD,
    )

# مرحله 1: دریافت نام کاربر
async def ask_for_user_name(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("شما مجاز به استفاده از این ربات نیستید.")
        return ConversationHandler.END
    await update.message.reply_text("لطفاً نام کاربر جدید را وارد کنید:")
    return GET_USER_NAME

# مرحله 2: دریافت مدت زمان اشتراک
async def ask_for_subscription_duration(update: Update, context: CallbackContext):
    user_name = update.message.text
    context.user_data["user_name"] = user_name

    # بررسی نام تکراری
    user_data = load_user_data()
    for details in user_data["users"].values():
        if details["name"] == user_name:
            await update.message.reply_text("این نام کاربری قبلاً ثبت شده است. لطفاً نام دیگری انتخاب کنید.")
            return ConversationHandler.END

    await update.message.reply_text(
        "لطفاً مدت زمان اشتراک را انتخاب کنید:\n1️⃣ یک ماه\n2️⃣ دو ماه\n3️⃣ سه ماه",
        reply_markup=ReplyKeyboardMarkup([["1 ماه", "2 ماه", "3 ماه"], ["بازگشت"]], resize_keyboard=True),
    )
    return GET_SUBSCRIPTION_DURATION

# تابع ایجاد کاربر (با لاگ بیشتر)
async def create_user(update: Update, context: CallbackContext):
    user = update.effective_user
    if not is_admin(update):
        await update.message.reply_text("شما مجاز به استفاده از این ربات نیستید.")
        return ConversationHandler.END

    duration_text = update.message.text
    if duration_text == "بازگشت":
        await update.message.reply_text("عملیات لغو شد. به منوی اصلی بازگشتید.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    if duration_text not in ["1 ماه", "2 ماه", "3 ماه"]:
        await update.message.reply_text("لطفاً یک گزینه معتبر انتخاب کنید.")
        return GET_SUBSCRIPTION_DURATION

    # مدت زمان اشتراک
    duration_map = {"1 ماه": 1, "2 ماه": 2, "3 ماه": 3}
    months = duration_map[duration_text]
    expiry_date = datetime.now() + timedelta(days=30 * months)

    # نام کاربر
    user_name = context.user_data["user_name"]

    try:
        # لاگ درخواست
        logger.info(f"Creating user {user_name} with subscription duration: {months} months")
        logger.debug(f"Sending POST request to {OUTLINE_API_URL}/access-keys")

        # بررسی نام کاربری تکراری
        monitoring_data = load_monitoring_list()
        for monitored_user_id, monitored_details in monitoring_data.items():
            if monitored_details["name"] == user_name:
                await update.message.reply_text("❌ این نام کاربری قبلاً اضافه شده است.")
                return ConversationHandler.END

        # ارسال درخواست ایجاد کاربر
        response = requests.post(
            f"{OUTLINE_API_URL}/access-keys",
            headers={"Authorization": f"Bearer {OUTLINE_API_KEY}"},
            json={"name": user_name},
            verify=False,
        )
        logger.debug(f"Response Status: {response.status_code}")
        logger.debug(f"Response Body: {response.text}")

        if response.status_code in [200, 201]:
            data = response.json()
            user_id = data["id"]

            # ذخیره اطلاعات کاربر در فایل JSON
            user_data = load_user_data()
            user_data["users"][str(user_id)] = {
                "name": user_name,
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "accessUrl": data["accessUrl"],
            }
            save_user_data(user_data)

            # به‌روزرسانی لیست مانیتورینگ
            update_monitoring_list()
            logger.info(f"User {user_name} (ID: {user_id}) added to monitoring list.")

            # پیام نهایی
            message = (
                f"کاربر جدید ایجاد شد! 🎉\n\n"
                f"ID: {user_id}\n"
                f"Name: {user_name}\n"
                f"تاریخ انقضا: {expiry_date.strftime('%Y-%m-%d')}\n\n"
                f"لینک اتصال:\n"
                f"{data['accessUrl']}\n\n"
                f"لینک دانلود برنامه outline برای تمام سیستم عامل ها:\n"
                f"iOS: [App Store](https://apps.apple.com/us/app/outline-app/id1356177741)\n"
                f"Android: [Play Store](https://play.google.com/store/apps/details?id=org.outline.android.client&hl=en&pli=1)\n"
                f"Windows: [Download](https://s3.amazonaws.com/outline-releases/client/windows/stable/Outline-Client.exe)\n"
                f"Mac: [App Store](https://apps.apple.com/us/app/outline-secure-internet-access/id1356178125?mt=12)"
            )
            await update.message.reply_text(message, parse_mode="Markdown")
        else:
            if response.status_code == 401:
                await update.message.reply_text("❌ دسترسی غیرمجاز! لطفاً تنظیمات API را بررسی کنید.")
            elif response.status_code == 500:
                await update.message.reply_text("❌ خطای سرور Outline! لطفاً بعداً دوباره تلاش کنید.")
            else:
                await update.message.reply_text(f"خطا در ایجاد کاربر: {response.status_code}")
    except Exception as e:
        logger.error(f"Exception in create_user: {str(e)}")
        await update.message.reply_text("خطای غیرمنتظره در ایجاد کاربر!")

    await update.message.reply_text("به منوی اصلی بازگشتید.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


# مشاهده کاربران
async def list_users(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("شما مجاز به استفاده از این ربات نیستید.")
        return

    user_data = load_user_data()["users"]
    if user_data:
        message = "👥 کاربران موجود:\n\n"
        today = datetime.now().date()

        for user_id, details in user_data.items():
            if not isinstance(details, dict) or "expiry_date" not in details:
                logger.warning(f"Invalid data for user ID {user_id}: {details}")
                continue

            expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
            status = "✅ فعال" if expiry_date >= today else "❌ منقضی‌شده"
            message += (
                f"ID: {user_id}\n"
                f"Name: {details['name']}\n"
                f"تاریخ انقضا: {details['expiry_date']} ({status})\n\n"
            )

        await update.message.reply_text(message)
    else:
        await update.message.reply_text("هیچ کاربری یافت نشد.")

# تابع حذف کاربر
async def delete_user(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("شما مجاز به استفاده از این ربات نیستید.")
        return

    await update.message.reply_text("لطفاً ID کاربری را که می‌خواهید حذف کنید وارد کنید:")
    return GET_USER_ID

async def confirm_delete_user(update: Update, context: CallbackContext):
    user_id = update.message.text.strip()
    user_data = load_user_data()

    if user_id not in user_data["users"]:
        await update.message.reply_text(f"کاربر با شناسه {user_id} وجود ندارد.")
        return ConversationHandler.END

    try:
        # حذف کاربر از Outline
        response = requests.delete(
            f"{OUTLINE_API_URL}/access-keys/{user_id}",
            headers={"Authorization": f"Bearer {OUTLINE_API_KEY}"},
            verify=False,
        )

        if response.status_code == 204:
            # حذف از فایل JSON
            user_data["users"].pop(user_id, None)
            save_user_data(user_data)
            await update.message.reply_text(f"کاربر با ID {user_id} با موفقیت حذف شد.")
        elif response.status_code == 404:
            await update.message.reply_text(
                f"کاربر با شناسه {user_id} در سرور یافت نشد. فقط از فایل حذف می‌شود."
            )
            user_data["users"].pop(user_id, None)
            save_user_data(user_data)
        else:
            await update.message.reply_text(
                f"خطا در حذف کاربر از سرور!\nکد وضعیت: {response.status_code}\nپاسخ: {response.text}"
            )
    except Exception as e:
        logger.error(f"Exception in delete_user: {str(e)}")
        await update.message.reply_text("خطای غیرمنتظره در حذف کاربر!")

    return ConversationHandler.END

# تابع چت با پشتیبانی
async def contact_support(update: Update, context: CallbackContext):
    user = update.effective_user
    support_chat_id = "@irannetwork_co"  # آیدی پشتیبانی
    message_to_support = (
        f"کاربر {user.first_name} ({user.username if user.username else 'بدون آیدی کاربری'}) "
        f"درخواست پشتیبانی دارد.\n"
        f"ID: {user.id}"
    )

    # ارسال پیام به پشتیبانی
    try:
        BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": support_chat_id,
                "text": message_to_support,
            },
        )

        if response.status_code == 200:
            await update.message.reply_text(
                "پیام شما به پشتیبانی ارسال شد. به زودی با شما تماس خواهیم گرفت."
            )
        else:
            await update.message.reply_text(
                "خطا در ارسال پیام به پشتیبانی. لطفاً دوباره تلاش کنید."
            )
    except Exception as e:
        logging.error(f"Error sending support message: {str(e)}")
        await update.message.reply_text(
            "یک خطای غیرمنتظره رخ داده است. لطفاً دوباره تلاش کنید."
        )




# مدیریت فایل monitoring_list.json
def load_monitoring_list():
    try:
        with open(MONITORING_FILE, "r") as file:
            return json.load(file).get("monitoring", {})
    except FileNotFoundError:
        initial_data = {"monitoring": {}}
        save_monitoring_list(initial_data)
        return initial_data["monitoring"]

def save_monitoring_list(data):
    with open(MONITORING_FILE, "w") as file:
        json.dump({"monitoring": data}, file, indent=4)


# مدیریت فایل blacklist.json
def load_blacklist():
    try:
        with open(BLACKLIST_FILE, "r") as file:
            return json.load(file).get("blacklist", {})
    except FileNotFoundError:
        initial_data = {"blacklist": {}}
        save_blacklist(initial_data)
        return initial_data["blacklist"]

def save_blacklist(data):
    with open(BLACKLIST_FILE, "w") as file:
        json.dump({"blacklist": data}, file, indent=4)



def update_monitoring_list():
    users_data = load_user_data()["users"]
    monitoring_data = load_monitoring_list()

    for user_id, details in users_data.items():
        if user_id not in monitoring_data:
            monitoring_data[user_id] = {
                "name": details["name"],
                "monitored_at": datetime.now().strftime("%Y-%m-%d")
            }

    save_monitoring_list(monitoring_data)
    logger.info("Monitoring list updated successfully!")


# متغیر برای ذخیره وضعیت خالی بودن مانیتورینگ
no_users_logged = False

def monitor_connections():
    """
    بررسی اتصال کاربران و محدودسازی برای تک‌کاربره بودن
    """
    monitoring_data = load_monitoring_list()

    for user_id, details in monitoring_data.items():
        user_name = details["name"]

        # بررسی تعداد اتصالات فعال
        connection_info = check_user_connections(user_id)
        connection_count = connection_info["connection_count"]
        ip_list = connection_info["ip_list"]

        # اگر بیش از یک اتصال وجود داشت
        if connection_count > 1:
            logger.error(f"❌ کاربر {user_name} با ID {user_id} بیش از یک اتصال دارد. IPها: {', '.join(ip_list)}")
            # بلاک کردن IPها
            for ip in ip_list:
                block_ip(ip)
            # حذف کاربر یا مسدودسازی بیشتر
            add_to_blacklist(user_id, user_name, "اتصال مشکوک (چند کاربر همزمان)", ip_list)
        else:
            logger.info(f"✅ کاربر {user_name} با یک اتصال مجاز در حال استفاده است.")



def save_blocked_ip(ip):
    """
    ذخیره IP مسدود شده در فایل JSON
    Args:
        ip (str): آدرس IP مسدود شده
    """
    blocked_file = "/root/outline-bot/blocked_ips.json"
    try:
        if not os.path.exists(blocked_file):
            with open(blocked_file, "w") as file:
                json.dump([], file)

        # خواندن فایل
        with open(blocked_file, "r") as file:
            try:
                blocked_ips = json.load(file)
            except json.JSONDecodeError:
                blocked_ips = []  # فایل خراب باشد، لیست خالی ایجاد می‌شود

        # اضافه کردن IP به لیست
        if ip not in blocked_ips:
            blocked_ips.append(ip)
            with open(blocked_file, "w") as file:
                json.dump(blocked_ips, file, indent=4)
            logger.info(f"IP {ip} در لیست مسدودشده ذخیره شد.")
    except Exception as e:
        logger.error(f"خطا در ذخیره IP مسدود شده {ip}: {str(e)}")



def block_ip(ip):
    """
    مسدود کردن IP با استفاده از iptables
    Args:
        ip (str): آدرس IP برای مسدود کردن
    """
    try:
        os.system(f"iptables -A INPUT -s {ip} -j DROP")
        logger.warning(f"IP {ip} به دلیل اتصال مشکوک مسدود شد.")
        save_blocked_ip(ip)  # ذخیره IP مسدود شده
    except Exception as e:
        logger.error(f"خطا در مسدود کردن IP {ip}: {str(e)}")


def unblock_ip(ip):
    """
    رفع مسدودیت IP با استفاده از iptables
    Args:
        ip (str): آدرس IP برای رفع مسدودیت
    """
    try:
        os.system(f"iptables -D INPUT -s {ip} -j DROP")
        logger.info(f"IP {ip} رفع مسدودیت شد.")
        # حذف از فایل blocked_ips.json
        blocked_file = "/root/outline-bot/blocked_ips.json"
        if os.path.exists(blocked_file):
            with open(blocked_file, "r") as file:
                blocked_ips = json.load(file)
            if ip in blocked_ips:
                blocked_ips.remove(ip)
                with open(blocked_file, "w") as file:
                    json.dump(blocked_ips, file, indent=4)
    except Exception as e:
        logger.error(f"خطا در رفع مسدودیت IP {ip}: {str(e)}")






def add_to_blacklist(user_id, name, reason, ip_list):
    """
    اضافه کردن کاربر به لیست مسدودی
    Args:
        user_id (str): شناسه کاربر
        name (str): نام کاربر
        reason (str): دلیل مسدودیت
        ip_list (list): لیست IPهای متصل
    """
    blacklist_data = load_blacklist()

    # ذخیره اطلاعات کاربر و IPها
    blacklist_data[user_id] = {
        "name": name,
        "reason": reason,
        "blocked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "blocked_ips": ip_list
    }

    save_blacklist(blacklist_data)
    logger.info(f"کاربر {name} (ID: {user_id}) به دلیل '{reason}' مسدود شد. IPها: {', '.join(ip_list)}")





def check_user_connections(user_id):
    """
    بررسی تعداد اتصالات کاربر و ثبت وضعیت
    Args:
        user_id (str): شناسه کاربر
    Returns:
        dict: اطلاعات مربوط به اتصالات شامل IPها و تعداد
    """
    user_data = load_user_data()["users"]
    if user_id in user_data and "accessUrl" in user_data[user_id]:
        access_url = user_data[user_id]["accessUrl"]
        try:
            # استخراج پورت از accessUrl
            port = access_url.split("@")[1].split(":")[1].split("/")[0]
            # استفاده از netstat برای پیدا کردن اتصالات روی این پورت
            result = os.popen(f"netstat -an | grep :{port} | grep ESTABLISHED").read()

            # فیلتر کردن خطوط معتبر
            connections = [line for line in result.splitlines() if f":{port}" in line]
            if not connections:
                return {"connection_count": 0, "ip_list": [], "port": port}

            # استخراج آی‌پی‌ها از خطوط معتبر
            ip_list = list(set([line.split()[4].split(':')[0] for line in connections]))
            return {"connection_count": len(ip_list), "ip_list": ip_list, "port": port}

        except Exception as e:
            logger.error(f"خطا در بررسی اتصالات کاربر {user_id}: {str(e)}")
            return {"connection_count": 0, "ip_list": [], "port": None}

    logger.warning(f"اطلاعات AccessUrl برای کاربر {user_id} یافت نشد.")
    return {"connection_count": 0, "ip_list": [], "port": None}




def log_connection_status(user_id, ip_list, connection_count):
    """
    ثبت وضعیت اتصال کاربران
    Args:
        user_id (str): شناسه کاربر
        ip_list (list): لیست آی‌پی‌های متصل
        connection_count (int): تعداد اتصالات
    """
    if connection_count == 1:
        logger.info(f"✅ User {user_id} is connected with IP: {', '.join(ip_list)}.")
    elif connection_count > 1:
        logger.warning(f"❌ User {user_id} has multiple connections! IPs: {', '.join(ip_list)}")
    else:
        logger.debug(f"User {user_id} has no active connections.")



async def list_blacklist(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("شما مجاز به استفاده از این ربات نیستید.")
        return

    blacklist_data = load_blacklist()
    if not blacklist_data:
        await update.message.reply_text("🚫 لیست مسدودی خالی است.")
        return

    message = "🚫 **لیست کاربران مسدود شده**:\n\n"
    for user_id, details in blacklist_data.items():
        blocked_ips = ', '.join(details.get("blocked_ips", []))
        message += (
            f"👤 **نام:** {details['name']}\n"
            f"🆔 **ID:** {user_id}\n"
            f"🌐 **IPها:** {blocked_ips}\n"
            f"📅 **تاریخ:** {details['blocked_at']}\n"
            f"⚠️ **دلیل:** {details['reason']}\n\n"
        )

    await update.message.reply_text(message, parse_mode="Markdown")


def save_connection_status(status_data):
    """
    ذخیره وضعیت اتصالات کاربران در فایل JSON
    Args:
        status_data (dict): دیکشنری وضعیت اتصالات کاربران
    """
    try:
        status_file = "/root/outline-bot/connection_status.json"
        with open(status_file, "w") as file:
            json.dump(status_data, file, indent=4)
        logger.debug("وضعیت اتصالات کاربران ذخیره شد.")
    except Exception as e:
        logger.error(f"خطا در ذخیره وضعیت اتصالات: {str(e)}")



async def unblock_user(update: Update, context: CallbackContext):
    """
    رفع مسدودیت کاربر و حذف IPها از iptables و فایل‌ها
    """
    user_id = update.message.text.strip()
    blacklist_data = load_blacklist()

    if user_id in blacklist_data:
        user_details = blacklist_data[user_id]
        blocked_ips = user_details.get("blocked_ips", [])

        # حذف IPها از iptables و فایل
        for ip in blocked_ips:
            os.system(f"iptables -D INPUT -s {ip} -j DROP")
            remove_blocked_ip(ip)
            logger.info(f"IP {ip} رفع مسدودیت شد.")

        # حذف کاربر از لیست مسدودی
        del blacklist_data[user_id]
        save_blacklist(blacklist_data)
        await update.message.reply_text(
            f"✅ کاربر `{user_details['name']}` و IPهای {', '.join(blocked_ips)} رفع مسدودیت شد.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("کاربر در لیست مسدودی وجود ندارد.")

def remove_blocked_ip(ip):
    """
    حذف IP از فایل blocked_ips.json
    Args:
        ip (str): آدرس IP برای حذف
    """
    blocked_file = "/root/outline-bot/blocked_ips.json"
    try:
        if os.path.exists(blocked_file):
            with open(blocked_file, "r") as file:
                blocked_ips = json.load(file)

            if ip in blocked_ips:
                blocked_ips.remove(ip)
                with open(blocked_file, "w") as file:
                    json.dump(blocked_ips, file, indent=4)
                logger.info(f"IP {ip} از فایل blocked_ips.json حذف شد.")
    except Exception as e:
        logger.error(f"خطا در حذف IP {ip} از فایل blocked_ips.json: {str(e)}")


async def manage_blacklist(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("شما مجاز به استفاده از این ربات نیستید.")
        return

    blacklist_data = load_blacklist()
    if not blacklist_data:
        await update.message.reply_text("🚫 لیست مسدودی خالی است.")
        return

    for user_id, details in blacklist_data.items():
        blocked_ips = ', '.join(details.get("blocked_ips", []))
        message = (
            f"👤 **نام کاربر:** {details['name']}\n"
            f"🆔 **ID:** {user_id}\n"
            f"🌐 **IPهای مسدودشده:** {blocked_ips}\n"
            f"📅 **تاریخ مسدودی:** {details['blocked_at']}\n"
            f"⚠️ **دلیل:** {details['reason']}"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔓 رفع مسدودیت", callback_data=f"unblock_{user_id}")]
        ])

        await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")


async def handle_blacklist_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("_")

    if action == "unblock":
        blacklist_data = load_blacklist()
        if user_id in blacklist_data:
            blocked_ips = blacklist_data[user_id].get("blocked_ips", [])
            for ip in blocked_ips:
                os.system(f"iptables -D INPUT -s {ip} -j DROP")
                remove_blocked_ip(ip)
            del blacklist_data[user_id]
            save_blacklist(blacklist_data)
            await query.edit_message_text(f"✅ کاربر `{user_id}` رفع مسدودیت شد.")
        else:
            await query.edit_message_text("کاربر در لیست مسدودی یافت نشد.")



def get_user_ip(user_id):
    """
    دریافت آدرس IP کاربر با استفاده از پورت موجود در accessUrl
    """
    user_data = load_user_data()["users"]
    if user_id in user_data and "accessUrl" in user_data[user_id]:
        access_url = user_data[user_id]["accessUrl"]
        try:
            # استخراج پورت از accessUrl
            port = access_url.split("@")[1].split(":")[1].split("/")[0]
            # استفاده از netstat برای پیدا کردن IP
            result = os.popen(f"netstat -an | grep :{port} | grep ESTABLISHED").read()
            if result:
                ip = result.split()[4].split(':')[0]  # استخراج IP از نتیجه
                return ip
            else:
                logger.warning(f"No active connections found for user {user_id} on port {port}.")
                return None
        except Exception as e:
            logger.error(f"Error extracting IP for user {user_id}: {str(e)}")
            return None
    logger.warning(f"Access URL not found for user {user_id}.")
    return None

async def notify_admin(context: CallbackContext, user_id, details):
    await context.bot.send_message(
        chat_id=ADMIN_IDS[0],
        text=(
            f"⚠️ کاربر با نام `{details['name']}` و شناسه `{user_id}` به دلیل "
            f"`{details['reason']}` مسدود شد.\n"
            f"تاریخ مسدودی: {details['blocked_at']}"
        ),
        parse_mode="Markdown"
    )




# تابع زمان‌بندی برای اجرای مانیتورینگ
def schedule_monitoring():
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_connections, 'interval', seconds=1)  # اجرای هر 1 ثانیه یک‌بار
    scheduler.start()
    logger.info("User monitoring scheduled every 1 seconds.")


# راه‌اندازی ربات
def main():
    BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
    application = Application.builder().token(BOT_TOKEN).build()

    # هندلر ایجاد کاربر
    create_user_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🆕 ایجاد کاربر$"), ask_for_user_name)],
        states={
            GET_USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_subscription_duration)],
            GET_SUBSCRIPTION_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user)],
        },
        fallbacks=[],
    )

    # هندلر حذف کاربر
    delete_user_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❌ حذف کاربر$"), delete_user)],
        states={
            GET_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete_user)],
        },
        fallbacks=[],
    )

    # هندلرهای اصلی
    application.add_handler(CommandHandler("start", start))
    application.add_handler(create_user_handler)
    application.add_handler(delete_user_handler)
    application.add_handler(MessageHandler(filters.Regex("^👥 مشاهده کاربران$"), list_users))
    application.add_handler(MessageHandler(filters.Regex("^💬 چت با پشتیبانی$"), chat_with_support))

    # هندلر آپدیت ربات
    application.add_handler(MessageHandler(filters.Regex("^🔄 آپدیت ربات$"), check_for_update))
    application.add_handler(MessageHandler(filters.Regex("^🚫 مدیریت مسدودی‌ها$"), manage_blacklist))
    application.add_handler(CallbackQueryHandler(handle_blacklist_actions))


    # زمان‌بندی مانیتورینگ هر 2 دقیقه
    schedule_monitoring()




    # حذف کاربران منقضی‌شده
    remove_expired_users()

    logger.info("Bot is starting...")
    application.run_polling()



if __name__ == "__main__":
    main()
