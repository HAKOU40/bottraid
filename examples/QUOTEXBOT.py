
import asyncio
import random
import sys
import logging
from colorama import init, Fore, Style
from quotexapi.stable_api import Quotex

# تعطيل التتبع
logging.getLogger().setLevel(logging.CRITICAL)
init(autoreset=True)


# ─────────────────────────────────────────────────────
# 🎯 واجهة المستخدم
# ─────────────────────────────────────────────────────
def banner():
    print(Fore.CYAN + Style.BRIGHT + r"""
  ____       _   _   _ _   _ _____ _____ 
 | __ ) _  _| |_| |_| | | | |_   _|_   _|
 |  _ \| || |  _|  _| | |_| | | |   | |  
 | |_) | |_| | |_| |_| |  _  | | |   | |  
 |____/ \__,_|\__|\__|_|_| |_| |_|   |_|  
      BADI QUOTEXAPI v1.0
    """)


def rule():
    print(Fore.CYAN + "─" * 50)


# ─────────────────────────────────────────────────────
# 📈 جلب أعلى 10 أصول
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
    except Exception:
        return [
            "EURUSD_otc", "GBPUSD_otc", "AUDUSD_otc", "NZDUSD_otc", "USDCAD_otc",
            "EURJPY_otc", "GBPJPY_otc", "AUDJPY_otc", "NZDJPY_otc", "USDJPY_otc"
        ]


# ─────────────────────────────────────────────────────
# 🎲 إشارة صفقة: 5 ثواني فقط (لا غير)
# ─────────────────────────────────────────────────────
def get_trade_signal(assets):
    asset = random.choice(assets)
    duration = 5  # ⚠ فقط 5 ثواني، لا غير
    direction = random.choice(["call", "put"])
    return asset, direction, duration


# ─────────────────────────────────────────────────────
# 🖨 طباعة تفاصيل الصفقة
# ─────────────────────────────────────────────────────
def print_signal(asset, direction, duration, trade_count):
    direction_arabic = "شراء" if direction == "call" else "بيع"
    print(Fore.CYAN + f"📊 الصفقة رقم: {trade_count}")
    print(Fore.GREEN + f"🎯 الإشارة: {asset} | {direction_arabic} | {duration} ثانية")


# ─────────────────────────────────────────────────────
# 📊 شريط التحميل (5 ثواني)
# ─────────────────────────────────────────────────────
async def loading_bar(seconds: int = 5):
    """عرض شريط تحميل لمدة محددة"""
    bar_length = 30
    for i in range(seconds + 1):
        progress = i / seconds
        block = int(round(bar_length * progress))
        percent = int(progress * 100)
        bar = "█" * block + "░" * (bar_length - block)
        print(Fore.CYAN + f"\r⏳ [{bar}] {percent}% (متبقي: {seconds - i}s)", end="")
        await asyncio.sleep(1)
    print()  # سطر جديد بعد الانتهاء


# ─────────────────────────────────────────────────────
# 📊 تحليل الجلسة بعد 10 صفقات
# ─────────────────────────────────────────────────────
def analyze_session(results):
    if not results:
        return

    wins = [r for r in results if r["status"] == "Win"]
    losses = [r for r in results if r["status"] == "Loss"]
    draws = [r for r in results if r["status"] == "Draw"]
    errors = [r for r in results if r["status"] == "ERROR"]

    total_trades = len(results)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0

    print(Fore.YELLOW + "📊 تحليل الجلسة الأخيرة (10 صفقات):")
    print(Fore.GREEN + f"   ✅ صفقات رابحة: {len(wins)}")
    print(Fore.RED + f"   ❌ صفقات خاسرة: {len(losses)}")
    if draws:
        print(Fore.YELLOW + f"   🟡 صفقات تعادل: {len(draws)}")
    if errors:
        print(Fore.MAGENTA + f"   ⚠  صفقات بها أخطاء: {len(errors)}")
    print(Fore.CYAN + f"   📈 نسبة النجاح: {win_rate:.2f}%")
    rule()


# ─────────────────────────────────────────────────────
# 🧠 التحقق من النتيجة باستخدام check_win (موثوق 100%)
# ─────────────────────────────────────────────────────
async def check_trade_result(client, buy_info, direction):
    """
    استخدام check_win للتحقق من النتيجة بعد شريط التحميل.
    """
    try:
        order_id = buy_info.get('id')
        open_price = buy_info.get('openPrice')

        if not order_id or open_price is None:
            return "ERROR"

        print(Fore.BLUE + f"💰 السعر الأولي: {open_price}")
        print(Fore.CYAN + "⏳ بدء شريط التحميل (5 ثواني)...")

        # عرض شريط التحميل لمدة 5 ثواني
        await loading_bar(5)

        # التحقق من النتيجة
        print(Fore.YELLOW + "🔍 جاري التحقق من النتيجة من السيرفر...")
        is_win = await client.check_win(order_id)

        if is_win:
            profit = client.get_profit()
            print(Fore.GREEN + f"🎉 ربحت! الربح: {profit}")
            return "Win"
        else:
            loss = client.get_profit()
            print(Fore.RED + f"💔 خسرت! الخسارة: {loss}")
            return "Loss"

    except Exception as e:
        print(Fore.RED + f"❌ خطأ في تحديد النتيجة: {str(e)}")
        return "ERROR"


# ─────────────────────────────────────────────────────
# 🔐 تسجيل الدخول
# ─────────────────────────────────────────────────────
async def login():
    print(Fore.YELLOW + "📧 تسجيل الدخول إلى الحساب")
    email = input("📧 البريد الإلكتروني: ").strip()
    password = input("🔑 كلمة المرور: ").strip()

    client = Quotex(email=email, password=password, lang="pt")

    print(Fore.BLUE + "🔄 جاري الاتصال...")
    check_connect, message = await client.connect()

    if check_connect:
        print(Fore.GREEN + "✅ تم الدخول بنجاح!")
        return client

    if "2fa" in str(message).lower():
        print(Fore.YELLOW + "🔐 مطلوب رمز التحقق")
        code = input("أدخل الرمز: ").strip()
        client.totp_code = code
        check_connect, message = await client.connect()
        if check_connect:
            print(Fore.GREEN + "✅ تم الدخول بنجاح!")
            return client

    print(Fore.RED + f"❌ فشل الدخول: {message}")
    return None


# ─────────────────────────────────────────────────────
# ⚙ إعدادات التداول
# ─────────────────────────────────────────────────────
def get_trading_settings():
    print(Fore.CYAN + "⚙  إعدادات التداول:")

    print("اختر نوع الحساب:")
    print("1- تجريبي (Practice)")
    print("2- حقيقي (Real)")
    while True:
        account_choice = input("اختيارك (1 أو 2): ").strip()
        if account_choice in ["1", "2"]:
            account_type = "PRACTICE" if account_choice == "1" else "REAL"
            break
        print(Fore.RED + "❌ اختيار غير صحيح، يرجى إدخال 1 أو 2")

    while True:
        try:
            amount = float(input("أدخل مبلغ الصفقة: ").strip())
            if amount > 0:
                break
            else:
                print(Fore.RED + "❌ المبلغ يجب أن يكون أكبر من صفر")
        except ValueError:
            print(Fore.RED + "❌ يرجى إدخال رقم صحيح")

    return account_type, amount


# ─────────────────────────────────────────────────────
# 🛠 التحقق من فتح الأصل
# ─────────────────────────────────────────────────────
async def is_asset_open(client, asset):
    try:
        _, data = await client.get_available_asset(asset)
        return data and len(data) > 2 and data[2]
    except:
        return False


# ─────────────────────────────────────────────────────
# 🔄 الحلقة الرئيسية
# ─────────────────────────────────────────────────────
async def main():
    banner()

    client = await login()
    if not client:
        return

    account_type, trade_amount = get_trading_settings()

    try:
        await client.change_account(account_type)
        status_msg = "التجريبي" if account_type == "PRACTICE" else "الحقيقي"
        print(Fore.GREEN + f"✅ تم التبديل إلى الحساب {status_msg}")
    except Exception as e:
        print(Fore.RED + f"⚠  لم يتم تغيير نوع الحساب: {e}")

    print(Fore.GREEN + "🚀 بدأت الجلسة...")
    await asyncio.sleep(2)

    assets = await get_top_10_assets(client)
    if not assets:
        print(Fore.RED + "❌ لم يتم جلب الأصول")
        return

    print(Fore.CYAN + f"🎯 العملات التي سيتم التداول عليها:")
    for i, asset in enumerate(assets, 1):
        print(Fore.WHITE + f"   {i}. {asset}")

    session_results = []
    trade_count = 0
    print(Fore.CYAN + "🔄 بدء تنفيذ الصفقات تلقائيا...")

    while True:
        trade_count += 1
        rule()

        asset, direction, duration = get_trade_signal(assets)
        print_signal(asset, direction, duration, trade_count)

        if not await is_asset_open(client, asset):
            print(Fore.RED + f"❌ الأصل {asset} مغلق حاليا")
            session_results.append({
                "status": "ERROR",
                "asset": asset,
                "direction": direction,
                "duration": duration
            })
            if trade_count % 10 == 0:
                analyze_session(session_results)
                session_results.clear()
            await asyncio.sleep(2)
            continue

        max_attempts = 10
        success = False
        buy_info = None

        for attempt in range(1, max_attempts + 1):
            print(Fore.CYAN + f"🔁 المحاولة {attempt}/{max_attempts}...")
            try:
                status, buy_info = await client.buy(
                    trade_amount,
                    asset,
                    direction,
                    duration,
                    time_mode="TIMER"
                )
                if status:
                    print(Fore.GREEN + f"✅ تم تنفيذ الصفقة بنجاح (المبلغ: ${trade_amount})")
                    success = True
                    break
                else:
                    print(Fore.YELLOW + f"⚠  فشل التنفيذ (المحاولة {attempt})")
                    await asyncio.sleep(1.5)
            except Exception as e:
                print(Fore.RED + f"❌ خطأ تقني (المحاولة {attempt}): {str(e)}")
                await asyncio.sleep(1.5)

        if not success:
            print(Fore.MAGENTA + "🚫 لم يتم تنفيذ الصفقة بعد 10 محاولات")
            print(Fore.RED + "🔴 تقرير: لم يتم تنفيذ أي صفقات في هذه الدورة")
            session_results.append({
                "status": "ERROR",
                "asset": asset,
                "direction": direction,
                "duration": duration
            })
            if trade_count % 10 == 0:
                analyze_session(session_results)
                session_results.clear()
            await asyncio.sleep(2)
            continue

        print(Fore.YELLOW + f"⏳ جاري تحليل النتيجة تلقائيا...")
        result_status = await check_trade_result(client, buy_info, direction)
        session_results.append({
            "status": result_status,
            "asset": asset,
            "direction": direction,
            "duration": duration
        })

        if result_status == "Win":
            print(Fore.GREEN + "✅ النتيجة: ربح")
        elif result_status == "Loss":
            print(Fore.RED + "❌ النتيجة: خسارة")
        elif result_status == "Draw":
            print(Fore.YELLOW + "🟡 النتيجة: تعادل")
        else:
            print(Fore.MAGENTA + "❌ خطأ في تحديد النتيجة")

        if trade_count % 10 == 0:
            analyze_session(session_results)
            session_results.clear()
            print(Fore.CYAN + "اختر:")
            print("1- بدء جلسة جديدة")
            print("2- الخروج")
            choice = input("اختيارك: ").strip()
            if choice == "2":
                print(Fore.MAGENTA + "🛑 تم الإنهاء")
                break

        await asyncio.sleep(random.uniform(1.5, 2.5))


# ─────────────────────────────────────────────────────
# 🚀 تشغيل البرنامج
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print(Fore.MAGENTA + "\n🛑 تم الإيقاف يدويا")
    except Exception as e:
        print(Fore.RED + f"\n❌ خطأ عام: {str(e)}")
