import asyncio
import random
import logging
import os
import threading
import time
from colorama import init, Fore, Style
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from quotexapi.stable_api import Quotex
from keep_alive import keep_alive

keep_alive()

# تعطيل التتبع الزائد
logging.getLogger().setLevel(logging.CRITICAL)
init(autoreset=True)

# 🤖 إعدادات التلجرام
TELEGRAM_TOKEN = "7999683201:AAGVKH_OvP9IjkMsN7Tl4Cnkmqt22YeTKE4"

# 🔐 إعدادات التحكم الديناميكي
ADMIN_ID = 6340633158
active_users = {}  # {user_id: expire_time}
lock = threading.Lock()

# 🔄 حالات المحادثة
(WAITING_EMAIL, WAITING_PASSWORD, WAITING_ACCOUNT, WAITING_AMOUNT, WAITING_DURATION, WAITING_MARTINGALE) = range(6)

# 🧠 تخزين بيانات كل مستخدم
user_data = {}  # user_data[user_id] = {...}
clients = {}    # clients[user_id] = client
trading_results = {}  # trading_results[user_id] = []

# 🤖 إنشاء تطبيق التلجرام
application = Application.builder().token(TELEGRAM_TOKEN).build()


# ─────────────────────────────────────────────────────
# 🎯 /start - رسالة ترحيب فخمة
# ─────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with lock:
        if user_id not in active_users or time.time() > active_users[user_id]:
            await update.message.reply_text(
                f"❌ ليس لديك صلاحية استخدام هذا البوت.\n"
                f"🆔 هذا هو آيديك: <code>{user_id}</code>\n"
                f"📬 أرسله إلى المطور @tatin34 للتفعيل.",
                parse_mode='HTML'
            )
            return ConversationHandler.END
    if user_id not in user_data:
        user_data[user_id] = {}
        trading_results[user_id] = []
    welcome_msg = (
        "🦅 <b>مرحبا بك في BADI OTC v5.0</b> 🦅\n"
        "✨ <b>أقوى بوت تداول تلقائي على Quotex OTC</b>\n"
        "🎯 دقة في الأداء • ذكاء في التنفيذ • سرعة في التنفيذ\n"
        "🔐 بياناتك آمنة • تداولك تلقائي • نتائجك مضمونة\n"
        "🚀 ابدأ التداول الآن، أو تواصل مع المطور عبر:\n"
        "📬 <a href='https://t.me/tatin34'>@tatin34</a>"
    )
    keyboard = [[KeyboardButton("🚀 ابدأ التداول الآلي")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='HTML', disable_web_page_preview=True)
    return WAITING_EMAIL


# ─────────────────────────────────────────────────────
# 📧 التعامل مع زر "ابدأ التداول الآلي"
# ─────────────────────────────────────────────────────
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with lock:
        if user_id not in active_users or time.time() > active_users[user_id]:
            return
    if user_id not in user_data:
        user_data[user_id] = {}
        trading_results[user_id] = []
    text = update.message.text.strip()
    if text == "🚀 ابدأ التداول الآلي":
        await update.message.reply_text(
            "📧 من فضلك أدخل بريدك الإلكتروني لتسجيل الدخول إلى حساب Quotex:",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_EMAIL
    else:
        return WAITING_EMAIL


# ─────────────────────────────────────────────────────
# 📧 حفظ البريد الإلكتروني
# ─────────────────────────────────────────────────────
async def save_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    email = update.message.text.strip()
    if user_id not in user_data:
        user_data[user_id] = {}
    if "@" not in email or "." not in email:
        await update.message.reply_text("❌ <b>البريد الإلكتروني غير صالح.</b>\nمن فضلك أدخل بريدا صحيحا:", parse_mode='HTML')
        return WAITING_EMAIL
    user_data[user_id]['email'] = email
    await update.message.reply_text(f"✅ تم حفظ البريد: <code>{email}</code>\n🔐 الآن، أدخل كلمة المرور:", parse_mode='HTML')
    return WAITING_PASSWORD


# ─────────────────────────────────────────────────────
# 🔐 حفظ كلمة المرور
# ─────────────────────────────────────────────────────
async def save_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    if user_id not in user_data:
        user_data[user_id] = {}
    if len(password) < 4:
        await update.message.reply_text("❌ <b>كلمة المرور قصيرة جدا.</b>\nأدخل كلمة مرور أطول:", parse_mode='HTML')
        return WAITING_PASSWORD
    user_data[user_id]['password'] = password
    await update.message.reply_text("🔄 جاري الاتصال بـ Quotex...")
    client = Quotex(email=user_data[user_id]['email'], password=user_data[user_id]['password'], lang="ar")
    clients[user_id] = client
    if os.path.exists(f"session_{user_id}.json"):
        os.remove(f"session_{user_id}.json")
    connected = False
    for _ in range(3):
        try:
            check_connect, _ = await client.connect()
            if check_connect:
                connected = True
                break
        except:
            await asyncio.sleep(3)
    if not connected:
        await update.message.reply_text("❌ فشل الاتصال. تحقق من الإنترنت أو بيانات الدخول.")
        return ConversationHandler.END
    await update.message.reply_text("✅ تم تسجيل الدخول بنجاح إلى حساب Quotex!")
    keyboard = [[KeyboardButton("تجريبي"), KeyboardButton("حقيقي")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("🏦 اختر نوع الحساب:", reply_markup=reply_markup)
    return WAITING_ACCOUNT


# ─────────────────────────────────────────────────────
# 🏦 حفظ نوع الحساب
# ─────────────────────────────────────────────────────
async def save_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    choice = update.message.text.strip()
    if choice not in ["تجريبي", "حقيقي"]:
        await update.message.reply_text("❌ يرجى اختيار 'تجريبي' أو 'حقيقي'.")
        return WAITING_ACCOUNT
    user_data[user_id]['account_type'] = "PRACTICE" if choice == "تجريبي" else "REAL"
    client = clients[user_id]
    try:
        await client.change_account(user_data[user_id]['account_type'])
        await update.message.reply_text(f"✅ تم التبديل إلى الحساب: <b>{choice}</b>", parse_mode='HTML')
    except:
        await update.message.reply_text(f"⚠ لم يتم التبديل. الحساب الحالي: {choice}")
    await update.message.reply_text("💰 أدخل <b>مبلغ الصفقة الأساسية</b> (مثلا: 1000):", parse_mode='HTML')
    return WAITING_AMOUNT


# ─────────────────────────────────────────────────────
# 💰 حفظ المبلغ
# ─────────────────────────────────────────────────────
async def save_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = float(update.message.text.strip())
        if amount <= 0: raise ValueError
        user_data[user_id]['amount'] = amount
        await update.message.reply_text(f"✅ تم تحديد المبلغ: <b>${amount}</b>", parse_mode='HTML')
        keyboard = [[KeyboardButton("5"), KeyboardButton("10")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("⏱ اختر مدة الصفقة (بالثواني):", reply_markup=reply_markup)
        return WAITING_DURATION
    except:
        await update.message.reply_text("❌ أدخل رقما صحيحا.")
        return WAITING_AMOUNT


# ─────────────────────────────────────────────────────
# ⏱ حفظ المدة
# ─────────────────────────────────────────────────────
async def save_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    duration = update.message.text.strip()
    if duration not in ["5", "10"]:
        await update.message.reply_text("❌ اختر 5 أو 10 ثواني.")
        return WAITING_DURATION
    user_data[user_id]['duration'] = int(duration)
    await update.message.reply_text(f"✅ تم تحديد المدة: <b>{duration} ثانية</b>", parse_mode='HTML')
    keyboard = [[KeyboardButton("لا")], [KeyboardButton("نعم - 1 مرة")], [KeyboardButton("نعم - 2 مرة")], [KeyboardButton("نعم - 3 مرات")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("🔁 هل ترغب في تفعيل <b>استراتيجية المضاعفة</b>؟", reply_markup=reply_markup, parse_mode='HTML')
    return WAITING_MARTINGALE


# ─────────────────────────────────────────────────────
# 🔁 حفظ خيار المضاعفة
# ─────────────────────────────────────────────────────
async def save_martingale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    choice = update.message.text.strip()
    user_data[user_id]['martingale'] = 0
    if "1" in choice: user_data[user_id]['martingale'] = 1
    elif "2" in choice: user_data[user_id]['martingale'] = 2
    elif "3" in choice: user_data[user_id]['martingale'] = 3
    elif "لا" not in choice:
        await update.message.reply_text("❌ يرجى اختيار خيار من القائمة.")
        return WAITING_MARTINGALE
    summary = (
        "🎉 <b>تم إكمال الإعداد!</b>\n"
        f"📧 البريد: <code>{user_data[user_id]['email']}</code>\n"
        f"🏦 الحساب: <b>{'تجريبي' if user_data[user_id]['account_type'] == 'PRACTICE' else 'حقيقي'}</b>\n"
        f"💰 المبلغ: <b>${user_data[user_id]['amount']}</b>\n"
        f"⏱ المدة: <b>{user_data[user_id]['duration']} ثانية</b>\n"
        f"🔁 المضاعفة: <b>{user_data[user_id]['martingale']} مرة</b>\n"
        "🚀 <b>جاري بدء التداول الآلي...</b>"
    )
    await update.message.reply_text(summary, parse_mode='HTML')
    await run_trading(update, context)
    return ConversationHandler.END


# ─────────────────────────────────────────────────────
# 📈 جلب أفضل 10 أصول
# ─────────────────────────────────────────────────────
async def get_top_10_assets(client):
    try:
        assets = await client.get_all_assets()
        top = sorted(
            [(k, v if isinstance(v, int) else v.get('profit', 0))
             for k, v in assets.items() if isinstance(v, (int, dict))],
            key=lambda x: x[1], reverse=True
        )[:10]
        return [n for n, _ in top]
    except:
        return ["EURUSD_otc", "GBPUSD_otc", "AUDUSD_otc", "NZDUSD_otc", "USDCAD_otc"]


# ─────────────────────────────────────────────────────
# 🔁 تنفيذ الصفقة (مصلح - لا صفقات وهمية)
# ─────────────────────────────────────────────────────
async def martingale_apply(update: Update, amount, asset, direction):
    user_id = update.effective_user.id
    client = clients[user_id]
    current_amount = amount
    result = "خسارة"
    final_profit = 0.0

    for level in range(user_data[user_id]['martingale'] + 1):
        try:
            status, buy_info = await client.buy(
                current_amount,
                asset,
                direction,
                user_data[user_id]['duration'],
                time_mode="TIMER"
            )

            # ✅ التحقق من وجود buy_info (الصفقة نفذت فعلا)
            if not status or not buy_info:
                await update.message.reply_text("⚠ تم إرسال الصفقة، لكن لم يتم استلام تأكيد فوري.")
                await asyncio.sleep(user_data[user_id]['duration'])
                continue

            # ✅ إرسال إشارة الصفقة
            direction_emoji = "🔼" if direction == "call" else "🔽"
            tend = "شراء" if direction == "call" else "بيع"
            payout = client.get_payout_by_asset(asset) or 85.0
            signal_message = f"""💳 <b>{asset.replace('_otc', '').upper()}-OTC</b>
🔥 <b>{user_data[user_id]['duration']}S</b>
{direction_emoji} <b>{tend}</b>
💸 <b>Payout:</b> {payout:.1f}%"""
            await update.message.reply_text(signal_message, parse_mode='HTML')
            await asyncio.sleep(user_data[user_id]['duration'])

            # ✅ التحقق من النتيجة
            if await client.check_win(buy_info["id"]):
                profit = client.get_profit()
                await update.message.reply_text(f"✅ <b>ربح!</b> +${profit:.2f}", parse_mode='HTML')
                return "ربح", profit
            else:
                loss = client.get_profit()
                await update.message.reply_text(f"❌ <b>خسرت!</b> الخسارة: ${-loss:.2f}", parse_mode='HTML')
                if level < user_data[user_id]['martingale']:
                    current_amount *= 2
                    await update.message.reply_text(f"🔁 <b>المضاعفة {level+1}</b>: ${current_amount}", parse_mode='HTML')
                else:
                    return "خسارة", loss

        except Exception as e:
            await update.message.reply_text(f"⚠ خطأ تقني: {str(e)}")
            return "خطأ", 0.0

    return result, final_profit


# ─────────────────────────────────────────────────────
# 🔄 بدء التداول (10 صفقات)
# ─────────────────────────────────────────────────────
async def run_trading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with lock:
        if user_id not in active_users or time.time() > active_users[user_id]:
            await update.message.reply_text("❌ انتهت صلاحية الجلسة.")
            return
    if user_id not in trading_results:
        trading_results[user_id] = []
    trading_results[user_id] = []
    client = clients.get(user_id)
    if not client:
        await update.message.reply_text("❌ لم يتم العثور على عميل التداول.")
        return
    try:
        assets = await get_top_10_assets(client)
    except:
        assets = ["EURUSD_otc", "GBPUSD_otc", "AUDUSD_otc", "NZDUSD_otc", "USDCAD_otc"]
    if not assets:
        assets = ["EURUSD_otc", "GBPUSD_otc", "AUDUSD_otc"]
    for i in range(1, 11):
        try:
            asset = random.choice(assets)
            direction = random.choice(["call", "put"])
            res, profit = await martingale_apply(update, user_data[user_id]['amount'], asset, direction)
            trading_results[user_id].append({
                "asset": asset.replace("_otc", "").upper(),
                "direction": "شراء" if direction == "call" else "بيع",
                "result": res,
                "profit": profit
            })
            await asyncio.sleep(random.uniform(3, 5))
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {str(e)}")
            break
    # 📊 تقرير كامل يعرض الأزواج والنتائج
    report = "📊 <b>تقرير التداول - 10 صفقات</b>\n"
    total = 0.0
    wins = 0
    for trade in trading_results[user_id]:
        emoji = "✅" if trade["result"] == "ربح" else "❌"
        report += f"{emoji} <b>{trade['asset']}-OTC</b> | {trade['direction']} | {trade['result']} | ${trade['profit']:.2f}\n"
        if trade["result"] == "ربح":
            wins += 1
        total += trade["profit"]
    result_text = "ربح" if total > 0 else "خسارة"
    report += f"\n📈 <b>إجمالي الصفقات:</b> 10\n"
    report += f"✅ <b>الأرباح:</b> {wins}\n"
    report += f"❌ <b>الخسائر:</b> {10 - wins}\n"
    report += f"💰 <b>الصافي:</b> <b>{result_text}</b> (${total:.2f})"
    keyboard = [
        [InlineKeyboardButton("🟢 مواصلة الجلسة", callback_data="continue_session")],
        [InlineKeyboardButton("🔴 تسجيل الخروج", callback_data="logout")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(report, reply_markup=reply_markup, parse_mode='HTML')


# ─────────────────────────────────────────────────────
# 🔘 معالجة الأزرار (مواصلة أو تسجيل خروج)
# ─────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if query.data == "continue_session":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("🔄 جاري مواصلة الجلسة... تنفيذ 10 صفقات جديدة.")
        # ✅ التحقق من وجود بيانات المستخدم
        if user_id not in user_data or user_id not in clients:
            await query.message.reply_text("❌ لم يتم العثور على بيانات الجلسة. يرجى بدء جلسة جديدة.")
            return
        with lock:
            if user_id not in active_users or time.time() > active_users[user_id]:
                await query.message.reply_text("❌ انتهت صلاحية الجلسة.")
                return
        await run_trading(update, context)
    elif query.data == "logout":
        if user_id in clients:
            try:
                await clients[user_id].logout()
            except:
                pass
            del clients[user_id]
        with lock:
            if user_id in active_users:
                del active_users[user_id]
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ تم تسجيل الخروج بنجاح.")
        keyboard = [[KeyboardButton("🚀 ابدأ التداول الآلي")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await query.message.reply_text("هل ترغب في بدء جلسة جديدة؟", reply_markup=reply_markup)


# ─────────────────────────────────────────────────────
# 🕒 التحقق من انتهاء الصلاحية كل 10 ثواني
# ─────────────────────────────────────────────────────
def check_expiration():
    while True:
        time.sleep(10)
        now = time.time()
        expired = []
        with lock:
            for user_id, expire_time in active_users.items():
                if now > expire_time:
                    print(f"{Fore.YELLOW}⏰ انتهت صلاحية المستخدم: {user_id}{Style.RESET_ALL}")
                    if user_id in clients:
                        try:
                            asyncio.run(clients[user_id].logout())
                            del clients[user_id]
                        except:
                            pass
                    expired.append(user_id)
            for uid in expired:
                del active_users[uid]
                if uid in user_data: del user_data[uid]
                if uid in trading_results: del trading_results[uid]


# ─────────────────────────────────────────────────────
# 🖥 واجهة التحكم من الترمنال (3 خيارات)
# ─────────────────────────────────────────────────────
def terminal_control():
    while True:
        print(f"\n{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        print(f"{Fore.GREEN}1 ➕ أضف آيدي جديد{Style.RESET_ALL}")
        print(f"{Fore.BLUE}2 ⏱ أضف 5 دقائق لآيدي الحالي{Style.RESET_ALL}")
        print(f"{Fore.RED}3 ❌ أغلق البوت{Style.RESET_ALL}")
        print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        choice = input(f"{Fore.YELLOW}اختر رقم الخيار: {Style.RESET_ALL}").strip()
        if choice == "1":
            try:
                new_id = int(input("🔹 أدخل آيدي المستخدم الجديد: "))
                with lock:
                    active_users[new_id] = time.time() + 300  # 5 دقائق
                print(f"{Fore.GREEN}✅ تم تفعيل المستخدم: {new_id} لمدة 5 دقائق{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}❌ آيدي غير صحيح{Style.RESET_ALL}")
        elif choice == "2":
            current_active = None
            with lock:
                if active_users:
                    current_active = list(active_users.keys())[-1]
            if current_active:
                with lock:
                    active_users[current_active] += 300
                print(f"{Fore.BLUE}⏱ تم إضافة 5 دقائق إضافية للمستخدم: {current_active}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ لا يوجد مستخدم نشط{Style.RESET_ALL}")
        elif choice == "3":
            print(f"{Fore.RED}🛑 تم إيقاف البوت{Style.RESET_ALL}")
            os._exit(0)
        else:
            print(f"{Fore.RED}❌ اختر رقم 1 أو 2 أو 3{Style.RESET_ALL}")


# ─────────────────────────────────────────────────────
# 🚀 تشغيل البوت
# ─────────────────────────────────────────────────────
def main():
    threading.Thread(target=check_expiration, daemon=True).start()
    threading.Thread(target=terminal_control, daemon=True).start()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_email)],
            WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_password)],
            WAITING_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_account)],
            WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_amount)],
            WAITING_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_duration)],
            WAITING_MARTINGALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_martingale)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🚀 ابدأ التداول الآلي)$"), handle_menu_choice))
    application.add_handler(CallbackQueryHandler(button_handler))

    print(f"{Fore.GREEN}🚀 البوت يعمل... ابدأ بإضافة آيدي من الترمنال{Style.RESET_ALL}")
    application.run_polling()


if __name__ == "__main__":
    main()
