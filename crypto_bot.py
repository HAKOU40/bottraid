import tkinter as tk
from tkinter import font as tkfont
from binance.client import Client
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import time
import threading
import requests
from io import BytesIO
from PIL import Image, ImageTk

# -------------------------------
# 🔑 إدخال المفاتيح
# -------------------------------
api_key = 'RnQqAcKeNz8OHOVBHxFQP2EiQZDJjGFgC2njMKfugMbNQFDP0SvQsNr7mvXgjJM1'
api_secret = 'ضع هنا secret key'  # ⚠️ لا تشاركها

client = Client(api_key, api_secret)

# -------------------------------
# 🎨 الألوان والثيم
# -------------------------------
BG_COLOR = "#1E1E2F"
CARD_COLOR = "#2A2A40"
TEXT_COLOR = "#FFFFFF"
BUY_COLOR = "#4CAF50"     # أخضر
SELL_COLOR = "#F44336"    # أحمر
HOLD_COLOR = "#FFC107"    # أصفر
ACCENT_COLOR = "#BB86FC"
FONT_FAMILY = "Segoe UI"
FRAME_NAMES = ["15m", "1h", "4h", "1d"]
INTERVALS = ["15m", "1h", "4h", "1d"]

# -------------------------------
# 🖼️ تحميل الصورة
# -------------------------------
def load_image_from_url(url, size):
    try:
        response = requests.get(url, timeout=5)
        img = Image.open(BytesIO(response.content))
        img = img.resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except:
        img = Image.new("RGB", size, "gray")
        return ImageTk.PhotoImage(img)

# -------------------------------
# 🐍 تحليل العملة لكل فريم
# -------------------------------
def analyze_symbol(df):
    if df.empty or len(df) < 14:
        return 'HOLD', 50

    rsi = RSIIndicator(close=df['close'], window=14)
    df['rsi'] = rsi.rsi()
    rsi_val = df['rsi'].iloc[-1]

    macd = MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    macd_val = df['macd'].iloc[-1]
    macd_signal_val = df['macd_signal'].iloc[-1]

    if rsi_val < 30 and macd_val > macd_signal_val:
        return 'BUY', rsi_val
    elif rsi_val > 70 and macd_val < macd_signal_val:
        return 'SELL', rsi_val
    else:
        return 'HOLD', rsi_val

# -------------------------------
# 📊 جلب الكلاينز لكل فريم
# -------------------------------
def get_klines(symbol, interval='15m', limit=150):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        return df
    except:
        return pd.DataFrame()

def get_top_10_symbols():
    try:
        tickers = client.get_ticker_24hr()
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT') and not t['symbol'].endswith('BUSDUSDT')]
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
        return [t['symbol'] for t in sorted_pairs[:10]]
    except:
        return []

# -------------------------------
# 🖥️ واجهة المستخدم المطورة
# -------------------------------
class CryptoScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎯 كاشف التداول الفخم - 10 عملات × 4 فريمات")
        self.root.geometry("1300x850")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        self.title_font = tkfont.Font(family=FONT_FAMILY, size=20, weight="bold")
        self.card_font = tkfont.Font(family=FONT_FAMILY, size=11)
        self.signal_font = tkfont.Font(family=FONT_FAMILY, size=13, weight="bold")
        self.header_font = tkfont.Font(family=FONT_FAMILY, size=10, weight="bold")

        # تحميل شعار Binance
        self.binance_logo = load_image_from_url(
            "https://upload.wikimedia.org/wikipedia/commons/5/57/Binance_Logo.svg",
            (220, 70)
        )

        # العنوان
        top_frame = tk.Frame(root, bg=BG_COLOR, pady=15)
        top_frame.pack()

        logo_label = tk.Label(top_frame, image=self.binance_logo, bg=BG_COLOR)
        logo_label.pack()

        title_label = tk.Label(
            top_frame,
            text="🎯 كاشف إشارات التداول - متعدد الفريمات",
            font=self.title_font,
            fg=ACCENT_COLOR,
            bg=BG_COLOR
        )
        title_label.pack()

        subtitle = tk.Label(
            top_frame,
            text="تحليل 10 أعلى عملات على Binance عبر 4 فريمات زمنية",
            font=("Segoe UI", 10), fg="#BBBBBB", bg=BG_COLOR
        )
        subtitle.pack()

        # بطاقات
        self.cards_frame = tk.Frame(root, bg=BG_COLOR, padx=20, pady=20)
        self.cards_frame.pack(expand=True, fill="both")

        # إنشاء 10 بطاقات
        self.cards = {}
        for i in range(10):
            card = self.create_card(self.cards_frame)
            row = i // 2
            col = i % 2
            card.grid(row=row, column=col, padx=18, pady=12, sticky="nsew")

        # توزيع المساحة
        for i in range(5):
            self.cards_frame.rowconfigure(i, weight=1)
        for i in range(2):
            self.cards_frame.columnconfigure(i, weight=1)

        self.update_data()

    def create_card(self, parent):
        frame = tk.Frame(parent, bg=CARD_COLOR, relief="raised", bd=2, padx=15, pady=15)
        
        # اسم العملة
        name_label = tk.Label(
            frame, text="جاري التحميل...", font=self.card_font, bg=CARD_COLOR, fg=TEXT_COLOR, anchor="w"
        )
        name_label.pack(fill="x")

        # السعر
        price_label = tk.Label(
            frame, text="السعر: --", font=self.card_font, bg=CARD_COLOR, fg="#B0B0B0"
        )
        price_label.pack(fill="x", pady=2)

        # رأس الجدول
        header_frame = tk.Frame(frame, bg=CARD_COLOR)
        header_frame.pack(fill="x", pady=5)

        for name in FRAME_NAMES:
            lbl = tk.Label(
                header_frame, text=name, width=8, font=self.header_font, fg=ACCENT_COLOR, bg=CARD_COLOR
            )
            lbl.pack(side="left", padx=2)

        # صف الإشارات
        signal_frame = tk.Frame(frame, bg=CARD_COLOR)
        signal_frame.pack(fill="x", pady=2)

        signals = {}
        for name in FRAME_NAMES:
            sig_label = tk.Label(
                signal_frame, text="–", width=8, font=self.signal_font, bg=CARD_COLOR, fg="#888"
            )
            sig_label.pack(side="left", padx=2)
            signals[name] = sig_label

        # حفظ العناصر
        frame.name_label = name_label
        frame.price_label = price_label
        frame.signals = signals

        self.cards[len(self.cards)] = frame
        return frame

    def update_data(self):
        def fetch_and_update():
            symbols = get_top_10_symbols()
            for i, symbol in enumerate(symbols):
                try:
                    card = self.cards.get(i)
                    if not card:
                        continue

                    # جلب السعر من آخر كلاينز
                    df_15m = get_klines(symbol, '15m', 50)
                    price = df_15m['close'].iloc[-1] if not df_15m.empty else "--"
                    if price != "--":
                        card.price_label.config(text=f"💰 السعر: ${price:,.4f}")
                    card.name_label.config(text=f"🪙 {symbol}")

                    # تحليل كل فريم
                    for interval, frame_name in zip(INTERVALS, FRAME_NAMES):
                        df = get_klines(symbol, interval, 150)
                        if df.empty:
                            signal_text = "ERR"
                            color = "#888"
                        else:
                            signal, rsi = analyze_symbol(df)
                            signal_text = f"{signal}"
                            if signal == "BUY":
                                color = BUY_COLOR
                            elif signal == "SELL":
                                color = SELL_COLOR
                            else:
                                color = HOLD_COLOR

                        # تحديث التسمية
                        card.signals[frame_name].config(text=signal_text, fg=color)

                except Exception as e:
                    print(f"Error analyzing {symbol}: {e}")
                    for frame_name in FRAME_NAMES:
                        if i in self.cards:
                            self.cards[i].signals[frame_name].config(text="–", fg="#888")

            # تعبئة الفراغات
            for j in range(len(symbols), 10):
                card = self.cards.get(j)
                if card:
                    card.name_label.config(text="غير متوفر")
                    card.price_label.config(text="السعر: --")
                    for frame_name in FRAME_NAMES:
                        card.signals[frame_name].config(text="–", fg="#888")

            # التحديث التالي بعد 5 دقائق
            self.root.after(300000, fetch_and_update)

        threading.Thread(target=fetch_and_update, daemon=True).start()

# -------------------------------
# 🚀 تشغيل التطبيق
# -------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoScannerApp(root)
    root.mainloop()
