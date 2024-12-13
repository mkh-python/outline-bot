#!/bin/bash

# رنگ‌های زیبا برای متن
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
RESET='\033[0m'  # Reset the color

VERSION_FILE="/root/version.txt"
LATEST_VERSION_URL="https://raw.githubusercontent.com/irannetwork/outline-bot/main/version.txt"
CURRENT_VERSION="1.37.3"

# ذخیره نسخه فعلی
if [ ! -f "$VERSION_FILE" ]; then
    echo "$CURRENT_VERSION" > "$VERSION_FILE"
fi

# بررسی به‌روزرسانی
check_for_update() {
    echo -e "${CYAN}Checking for updates...${RESET}"
    LATEST_VERSION=$(curl -s $LATEST_VERSION_URL)
    CURRENT_VERSION=$(cat $VERSION_FILE)

    if [ "$LATEST_VERSION" != "$CURRENT_VERSION" ]; then
        echo -e "${YELLOW}New version available: $LATEST_VERSION${RESET}"
        echo "$LATEST_VERSION" > "$VERSION_FILE"
        update_bot
    else
        echo -e "${GREEN}You already have the latest version: $CURRENT_VERSION${RESET}"
    fi
}

# تابع به‌روزرسانی ربات
update_bot() {
    echo -e "${CYAN}Updating the bot to the latest version...${RESET}"
    cd /root
    git clone https://github.com/irannetwork/outline-bot.git temp_repo
    cp -r temp_repo/* /root/
    rm -rf temp_repo
    echo -e "${GREEN}Update successful! Restarting the bot...${RESET}"
    systemctl restart telegram-bot.service
}

# ادامه نصب...
clear
cat << "EOF"
${CYAN}**********************************************
${YELLOW}                   MKH                  
${CYAN}**********************************************
${CYAN}**********************************************
${PURPLE}                   MKH                  ${RESET}
${CYAN}**********************************************
EOF

echo -e "${YELLOW}       Welcome to the Installation Script"
echo -e "${CYAN}**********************************************"
echo -e "${PURPLE}This bot was created by ${GREEN}mkh${RESET}."
echo -e "${CYAN}**********************************************"
echo -e "${YELLOW}This will help you set up Outline Server and the Telegram Bot.${RESET}"
echo -e "${CYAN}**********************************************"
echo -e "${CYAN}Please wait while we set everything up for you.${RESET}"

# یک تایمر برای نشان دادن بارگذاری
echo -e "${BLUE}Starting installation...${RESET}"
sleep 2

# 1. آپدیت سیستم
echo -e "${GREEN}Updating system...${RESET}"
echo -e "${YELLOW}در حال به‌روزرسانی سیستم...${RESET}"
sudo apt update && sudo apt upgrade -y

# 2. نصب پیش‌نیازهای سیستم
echo -e "${GREEN}Installing required packages...${RESET}"
echo -e "${YELLOW}در حال نصب پیش‌نیازهای سیستم...${RESET}"
sudo apt install -y docker.io docker-compose python3-pip python3-venv jq

# 3. ایجاد محیط مجازی
echo -e "${GREEN}Creating and activating virtual environment...${RESET}"
echo -e "${YELLOW}در حال ایجاد و فعال‌سازی محیط مجازی...${RESET}"
python3 -m venv /root/venv
source /root/venv/bin/activate

# 4. نصب وابستگی‌ها در محیط مجازی
echo -e "${GREEN}Installing Python packages...${RESET}"
echo -e "${YELLOW}در حال نصب پکیج‌های پایتون...${RESET}"
pip install python-telegram-bot requests python-dotenv

# 5. نصب و راه‌اندازی سرور Outline
echo -e "${GREEN}Installing Outline server...${RESET}"
echo -e "${YELLOW}در حال نصب سرور Outline...${RESET}"
sudo bash -c "$(wget -qO- https://raw.githubusercontent.com/Jigsaw-Code/outline-apps/master/server_manager/install_scripts/install_server.sh)"

# 6. دریافت API URL از کاربر
echo -e "${CYAN}Please provide your API URL from Outline Server (لطفاً API URL سرور Outline خود را وارد کنید):${RESET}"
read INPUT_API_URL

# استخراج مقادیر از API URL
OUTLINE_API_URL=$(echo $INPUT_API_URL | jq -r '.apiUrl')
CERT_SHA256=$(echo $INPUT_API_URL | jq -r '.certSha256')

# بررسی مقادیر
if [[ -z "$OUTLINE_API_URL" || -z "$CERT_SHA256" ]]; then
    echo -e "${RED}Invalid API URL provided. Please make sure it contains both 'apiUrl' and 'certSha256'.${RESET}"
    exit 1
fi

# دریافت توکن تلگرام از کاربر
echo -e "${CYAN}Please provide your Telegram bot Token (توکن ربات تلگرام خود را وارد کنید):${RESET}"
echo -e "${YELLOW}You can get your bot token by creating a bot through @BotFather on Telegram. (می‌توانید توکن ربات خود را از طریق ربات @BotFather در تلگرام دریافت کنید.)${RESET}"
read TELEGRAM_TOKEN

# دریافت آیدی عددی مدیر از کاربر
echo -e "${CYAN}Please provide your Telegram Admin ID (آیدی عددی مدیر خود را وارد کنید):${RESET}"
echo -e "${YELLOW}To get your Admin ID, message @ShowChatIdBot on Telegram and follow the instructions. (برای دریافت آیدی مدیر، به ربات @ShowChatIdBot در تلگرام پیام دهید و دستورالعمل‌ها را دنبال کنید.)${RESET}"
read ADMIN_ID

# ذخیره‌سازی اطلاعات در فایل پیکربندی ربات
echo -e "${GREEN}Saving configuration...${RESET}"
echo -e "${YELLOW}در حال ذخیره‌سازی پیکربندی...${RESET}"
echo "OUTLINE_API_URL=\"$OUTLINE_API_URL\"" > config.env
echo "OUTLINE_API_KEY=\"$(basename $OUTLINE_API_URL)\"" >> config.env
echo "CERT_SHA256=\"$CERT_SHA256\"" >> config.env
echo "TELEGRAM_TOKEN=\"$TELEGRAM_TOKEN\"" >> config.env
echo "ADMIN_ID=\"$ADMIN_ID\"" >> config.env

# 7. ایجاد فایل سرویس systemd برای ربات تلگرام
echo -e "${GREEN}Creating systemd service for Telegram Bot...${RESET}"
echo -e "${YELLOW}در حال ایجاد فایل سرویس systemd برای ربات تلگرام...${RESET}"
echo "[Unit]
Description=Telegram Bot for Outline Server
After=network.target

[Service]
Type=simple
ExecStart=/root/venv/bin/python3 /root/outline-bot/outline_bot.py
WorkingDirectory=/root/outline-bot
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/telegram-bot.service

# فعال‌سازی سرویس systemd
echo -e "${GREEN}Enabling and starting Telegram Bot service...${RESET}"
echo -e "${YELLOW}در حال فعال‌سازی و شروع سرویس ربات تلگرام...${RESET}"
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service

# ارسال پیام خوش‌آمدگویی به کاربر از طریق تلگرام
echo -e "${CYAN}Sending welcome message to the user...${RESET}"
curl -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
     -d "chat_id=$ADMIN_ID" \
     -d "text=🚀 نصب سرور با موفقیت انجام شد.
نسخه فعلی: $CURRENT_VERSION

با تشکر از نصب شما! لطفاً حمایت ما را فراموش نکنید.
آیدی پشتیبانی 24 ساعته ربات ما:
@irannetwork_co
********
API URL from Outline Server:
$INPUT_API_URL
**********
لینک دانلود ویندوز:
https://s3.amazonaws.com/outline-releases/manager/windows/stable/Outline-Manager.exe
*******
لینک دانلود مک:
https://s3.amazonaws.com/outline-releases/manager/macos/stable/Outline-Manager.dmg
*******
لینک دانلود لینوکس:
https://s3.amazonaws.com/outline-releases/manager/linux/stable/Outline-Manager.AppImage
*******
لطفاً این مقادیر را در Outline Manager وارد کنید تا به سرور متصل شوید."


# پیغام موفقیت
echo -e "${CYAN}Installation successful! Your bot is now ready to run.${RESET}"
echo -e "${CYAN}Your bot will automatically start after reboot. You can run it manually with the command: python3 outline_bot.py${RESET}"
echo -e "${GREEN}Created by mkh. For support and error reports, contact @irannetwork_co.${RESET}"
