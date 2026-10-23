import os, time
from datetime import datetime, date, time as dt_time
from telegram.ext import Updater, CommandHandler, CallbackContext
from iqoptionapi.stable_api import IQ_Option
import pandas as pd
import ta

# ============ CONFIG ============
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
IQ_EMAIL = os.getenv("IQ_EMAIL")
IQ_PASSWORD = os.getenv("IQ_PASSWORD")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

REAL_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY", "USDCHF", "GBPJPY"]
OTC_PAIRS = ["EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC", "AUDUSD-OTC", "EURJPY-OTC", "GBPJPY-OTC"]
MARTINGALE_RULE = [1, 2, 4]
USER_DATA = {}

print("👑 ROYAL AI Private Login Version Starting...")
IqMaster = IQ_Option(IQ_EMAIL, IQ_PASSWORD)
check, reason = IqMaster.connect()
print(f"Master Connected: {check}")
try: IqMaster.change_balance("PRACTICE")
except: pass

def is_real_market_open():
    return datetime.utcnow().weekday() < 5

def get_royal_signal(pair):
    try:
        candles = IqMaster.get_candles(pair, 60, 100, time.time())
        if not candles: return "WAIT", 0, 0, "No Data"
        df = pd.DataFrame(candles)
        df['close'] = df['close'].astype(float)
        df['ema_fast'] = ta.trend.ema_indicator(df['close'], 9)
        df['ema_slow'] = ta.trend.ema_indicator(df['close'], 21)
        df['rsi'] = ta.momentum.rsi(df['close'], 14)
        last, prev = df.iloc[-1], df.iloc[-2]
        if last['ema_fast'] > last['ema_slow'] and prev['ema_fast'] <= prev['ema_slow'] and 50 < last['rsi'] < 68:
            return "BUY 🟢", last['close'], last['rsi'], "EMA CROSS UP"
        elif last['ema_fast'] < last['ema_slow'] and prev['ema_fast'] >= prev['ema_slow'] and 32 < last['rsi'] < 50:
            return "SELL 🔴", last['close'], last['rsi'], "EMA CROSS DOWN"
        return "WAIT ⚪", last['close'], last['rsi'], "No Setup"
    except Exception as e:
        return "ERROR", 0, 0, str(e)

def get_user(user_id):
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {"martingale_step":0,"iq_conn":None,"email":None,"today":str(date.today()),"wins":0,"losses":0,"profit":0.0,"trades":[]}
    data = USER_DATA[user_id]
    if data["today"] != str(date.today()):
        data["today"]=str(date.today()); data["wins"]=0; data["losses"]=0; data["profit"]=0.0; data["trades"]=[]
    return data

def format_msg(pair, action, price, rsi, reason, step):
    amt = MARTINGALE_RULE[step] if step < len(MARTINGALE_RULE) else 1
    market_type = "REAL" if "-OTC" not in pair else "OTC"
    return f"👑 ROYAL AI SIGNAL 👑\nPair: {pair} ({market_type})\nSignal: {action}\nPrice: {price}\nStrategy: {reason}\nRSI: {round(rsi,1)}\n💰 MARTINGALE: Step {step+1}/3 = ${amt} ($1→$2→$4)\nExpiry: 1M | @royalfxtrdbot1"

# ============ COMMANDS ============
def start(update, context):
    if update.effective_chat.type != "private":
        return
    update.message.reply_text("👑 ROYAL AI @royalfxtrdbot1 👑\n\n🔐 PRIVATE LOGIN SYSTEM:\nYour login is 100% private - no one sees it.\n\n/royal - Scan REAL+OTC\n/login - Secure private login\n/balance - Your balance (private)\n/trade EURUSD-OTC - Trade\n/profit - Your daily stats\n/mystatus - Martingale step\n/leaderboard - Top traders\n/reset - Reset to $1\n/logout - Delete login\n\n⚠️ /login, /balance, /trade work ONLY in private chat with me for your security.")

def royal_scan(update, context):
    mode = "REAL" if is_real_market_open() else "OTC"
    pairs = REAL_PAIRS if mode == "REAL" else OTC_PAIRS
    update.message.reply_text(f"👑 Scanning {mode}...")
    found=0
    for pair in pairs:
        action, price, rsi, reason = get_royal_signal(pair)
        if "WAIT" not in action and "ERROR" not in action:
            step = get_user(update.effective_user.id)["martingale_step"]
            update.message.reply_text(format_msg(pair, action, price, rsi, reason, step))
            found+=1
        time.sleep(0.8)
    if found==0: update.message.reply_text("⚪ No strong signals now.")

def signal_one(update, context):
    pair = context.args[0] if context.args else "EURUSD-OTC"
    action, price, rsi, reason = get_royal_signal(pair)
    step = get_user(update.effective_user.id)["martingale_step"]
    update.message.reply_text(format_msg(pair, action, price, rsi, reason, step))

def market_cmd(update, context):
    s="OPEN → REAL" if is_real_market_open() else "CLOSED → OTC"
    update.message.reply_text(f"Market: {s}")

def login(update, context):
    # BLOCK GROUPS
    if update.effective_chat.type != "private":
        update.message.reply_text("🔐 For security, login ONLY in private chat with me\n\nGo to @royalfxtrdbot1 in private and type /login")
        return
    try:
        if len(context.args) >= 2:
            email=context.args[0]; password=context.args[1]
            # AUTO-DELETE PASSWORD MESSAGE
            try: context.bot.delete_message(update.effective_chat.id, update.message.message_id)
            except: pass
            msg = update.message.reply_text("🔐 Connecting securely... Your login message was deleted.")
            conn = IQ_Option(email, password)
            check, reason = conn.connect()
            if check:
                data=get_user(update.effective_user.id)
                data["iq_conn"]=conn; data["email"]=email
                msg.edit_text(f"✅ PRIVATE LOGIN SUCCESS\nEmail: {email}\nYour password message was DELETED and hidden.\nNo one can see it - only you.\n\nUse /balance and /trade")
            else:
                msg.edit_text(f"❌ Failed: {reason}")
        else:
            update.message.reply_text("🔐 SECURE PRIVATE LOGIN\n\nType in ONE message (it will auto-delete):\n/login youremail@gmail.com yourpassword\n\nExample:\n/login john@gmail.com MyPass123\n\n✅ Message auto-deletes in 1 sec\n✅ Only works here in private chat\n❌ Never works in groups")
    except: update.message.reply_text("Usage: /login email password - in private chat only")

def private_only_check(update):
    if update.effective_chat.type != "private":
        update.message.reply_text("🔐 This command works ONLY in private chat with @royalfxtrdbot1 for your security.\nClick @royalfxtrdbot1 and use it there.")
        return False
    return True

def balance_cmd(update, context):
    if not private_only_check(update): return
    data=get_user(update.effective_user.id)
    if not data["iq_conn"]: update.message.reply_text("❌ /login first"); return
    try:
        IqUser=data["iq_conn"]
        IqUser.change_balance("PRACTICE"); prac=IqUser.get_balance()
        IqUser.change_balance("REAL"); real=IqUser.get_balance()
        IqUser.change_balance("PRACTICE")
        step=data["martingale_step"]
        update.message.reply_text(f"👑 PRIVATE BALANCE\nEmail: {data['email']}\nPRACTICE: ${prac}\nREAL: ${real}\nNext: ${MARTINGALE_RULE[step]} Step {step+1}/3\n🔐 Only you can see this.")
    except Exception as e: update.message.reply_text(f"Error: {e}")

def switch_cmd(update, context):
    if not private_only_check(update): return
    data=get_user(update.effective_user.id)
    if not data["iq_conn"]: update.message.reply_text("❌ /login first"); return
    mode=context.args[0].upper() if context.args else "PRACTICE"
    if mode not in ["REAL","PRACTICE"]: mode="PRACTICE"
    data["iq_conn"].change_balance(mode)
    update.message.reply_text(f"✅ Switched to {mode} - PRIVATE")

def trade_cmd(update, context):
    if not private_only_check(update): return
    data=get_user(update.effective_user.id)
    if not data["iq_conn"]: update.message.reply_text("❌ /login first in private"); return
    pair=context.args[0] if context.args else "EURUSD-OTC"
    action, price, rsi, reason = get_royal_signal(pair)
    if "WAIT" in action or "ERROR" in action: update.message.reply_text(f"⚪ No signal for {pair} RSI {rsi}"); return
    step=data["martingale_step"]; amount=MARTINGALE_RULE[step]
    direction="call" if "BUY" in action else "put"
    check, order_id = data["iq_conn"].buy(amount, pair, direction, 1)
    if not check: update.message.reply_text("❌ Trade failed - check balance"); return
    update.message.reply_text(f"👑 PRIVATE TRADE: {action} {pair} ${amount} Step {step+1}/3\nWaiting 70s... Only you see this.")
    time.sleep(70)
    win=data["iq_conn"].check_win_v3(order_id)
    if win>0:
        data["wins"]+=1; data["profit"]+=round(win,2); data["martingale_step"]=0
        data["trades"].append(f"✅ {pair} +${round(win,2)}")
        update.message.reply_text(f"✅ WIN +${round(win,2)}\nToday: {data['wins']}W-{data['losses']}L Profit ${round(data['profit'],2)}\nRESET to $1 - Private result")
    else:
        data["losses"]+=1; data["profit"]+=-amount; data["trades"].append(f"❌ {pair} -${amount}")
        data["martingale_step"]+=1
        if data["martingale_step"]>=len(MARTINGALE_RULE):
            data["martingale_step"]=0
            update.message.reply_text(f"❌ LOSS ${amount}\nToday: {data['wins']}W-{data['losses']}L Profit ${round(data['profit'],2)}\nSafety RESET to $1")
        else:
            update.message.reply_text(f"❌ LOSS ${amount}\nToday: {data['wins']}W-{data['losses']}L Profit ${round(data['profit'],2)}\nNext ${MARTINGALE_RULE[data['martingale_step']]}")

def profit_cmd(update, context):
    if not private_only_check(update): return
    d=get_user(update.effective_user.id)
    winrate=round((d["wins"]/(d["wins"]+d["losses"])*100) if d["wins"]+d["losses"]>0 else 0,1)
    last="\n".join(d["trades"][-5:]) if d["trades"] else "No trades"
    update.message.reply_text(f"👑 PRIVATE STATS\nDate: {d['today']}\nEmail: {d['email']}\nWins: {d['wins']} Losses: {d['losses']}\nWinRate: {winrate}%\nProfit: ${round(d['profit'],2)}\nNext: ${MARTINGALE_RULE[d['martingale_step']]}\nLast:\n{last}\n🔐 Only you see this.")

def mystatus(update, context):
    d=get_user(update.effective_user.id)
    update.message.reply_text(f"Step {d['martingale_step']+1}/3 Next ${MARTINGALE_RULE[d['martingale_step']]} Rule $1→$2→$4")

def reset_cmd(update, context):
    get_user(update.effective_user.id)["martingale_step"]=0
    update.message.reply_text("✅ Reset to $1")

def logout_cmd(update, context):
    if not private_only_check(update): return
    if update.effective_user.id in USER_DATA: del USER_DATA[update.effective_user.id]
    update.message.reply_text("✅ Private data deleted. Logged out.")

def leaderboard_cmd(update, context):
    if not USER_DATA: update.message.reply_text("No trades today"); return
    sorted_u=sorted(USER_DATA.items(), key=lambda x: x[1]["profit"], reverse=True)[:5]
    txt="🏆 LEADERBOARD TODAY\n"
    for i,(uid,d) in enumerate(sorted_u,1): txt+=f"{i}. User {uid} → ${round(d['profit'],2)} ({d['wins']}W)\n"
    update.message.reply_text(txt)

def auto_channel(context: CallbackContext):
    if not CHANNEL_ID or "@" not in CHANNEL_ID: return
    for pair in (REAL_PAIRS if is_real_market_open() else OTC_PAIRS):
        action, price, rsi, reason = get_royal_signal(pair)
        if "BUY" in action or "SELL" in action:
            try: context.bot.send_message(CHANNEL_ID, format_msg(pair, action, price, rsi, reason, 0))
            except: pass

def daily_report_job(context: CallbackContext):
    if not CHANNEL_ID or not USER_DATA: return
    today_str=str(date.today())
    wins=sum(d["wins"] for d in USER_DATA.values() if d["today"]==today_str)
    losses=sum(d["losses"] for d in USER_DATA.values() if d["today"]==today_str)
    profit=sum(d["profit"] for d in USER_DATA.values() if d["today"]==today_str)
    users=len([d for d in USER_DATA.values() if d["wins"]+d["losses"]>0])
    if wins+losses==0: return
    winrate=round((wins/(wins+losses)*100) if wins+losses>0 else 0,1)
    report=f"📊 ROYAL DAILY REPORT\nDate: {today_str}\nActive: {users}\nWins: {wins} Losses: {losses}\nWinRate: {winrate}%\nProfit: ${round(profit,2)}\nBot: @royalfxtrdbot1"
    try: context.bot.send_message(CHANNEL_ID, report)
    except: pass

updater = Updater(TELEGRAM_TOKEN, use_context=True)
dp = updater.dispatcher
handlers=[("start",start),("royal",royal_scan),("signal",signal_one),("market",market_cmd),("login",login),("trade",trade_cmd),("balance",balance_cmd),("switch",switch_cmd),("profit",profit_cmd),("mystatus",mystatus),("reset",reset_cmd),("logout",logout_cmd),("leaderboard",leaderboard_cmd)]
for cmd,func in handlers: dp.add_handler(CommandHandler(cmd, func))
updater.job_queue.run_repeating(auto_channel, interval=180, first=30)
updater.job_queue.run_daily(daily_report_job, time=dt_time(hour=22, minute=59))
print("👑 ROYAL AI PRIVATE LOGIN @royalfxtrdbot1 RUNNING")
updater.start_polling()
updater.idle()
