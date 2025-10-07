import requests
import datetime
import pytz
import time
from colorama import Fore, Style

# ====================================
# CONFIG
# ====================================
TELEGRAM_BOT_TOKEN = "8275394714:AAFol1JyvRc8pVp_KVEQsMVzjE8CUhhpeCw"
TELEGRAM_CHAT_ID = "1850789024"
MYT = pytz.timezone("Asia/Kuala_Lumpur")

# ====================================
# HELPER FUNCTIONS
# ====================================

def fetch_with_retry(url, key_path=None, retries=3, delay=2):
    """Fetch JSON data from API with retry and optional key extraction"""
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            data = res.json()
            if key_path:
                for k in key_path:
                    data = data[k]
            return data
        except Exception as e:
            if attempt < retries:
                print(f"{Fore.YELLOW}Retry {attempt}/{retries} failed: {e}. Retrying...{Style.RESET_ALL}")
                time.sleep(delay)
            else:
                print(f"{Fore.RED}API failed after {retries} attempts: {url}{Style.RESET_ALL}")
    return None


def send_telegram_message(message: str):
    """Send formatted HTML message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"{Fore.RED}⚠️ Telegram send failed: {e}{Style.RESET_ALL}")


def fetch_fear_greed():
    data = fetch_with_retry("https://api.alternative.me/fng/?limit=1")
    try:
        return int(data["data"][0]["value"])
    except:
        return None


def fetch_altcoin_season():
    """Fetch Altcoin Season Index from BlockchainCenter with fallback handling"""
    url = "https://api.blockchaincenter.net/api/altcoin-season-index"
    data = fetch_with_retry(url)
    try:
        if isinstance(data, dict) and "seasonIndex" in data:
            return int(data["seasonIndex"])
        elif isinstance(data, (int, float)):
            return int(data)
        else:
            print(f"{Fore.YELLOW}⚠️ Altcoin Season Index data invalid — defaulting to N/A{Style.RESET_ALL}")
            return None
    except Exception as e:
        print(f"{Fore.RED}⚠️ Failed to parse Altcoin Season Index: {e}{Style.RESET_ALL}")
        return None


def fetch_market_data():
    """Fetch market cap, dominance, and stablecoin ratio from CoinGecko"""
    data = fetch_with_retry("https://api.coingecko.com/api/v3/global", key_path=["data"])
    if not data:
        return None, None, None, None
    try:
        total_mcap = data["total_market_cap"].get("usd")
        btc_dominance = data["market_cap_percentage"].get("btc")
        eth_dominance = data["market_cap_percentage"].get("eth")

        # Stablecoin ratio derived from market_cap_percentage
        usdt_percent = data["market_cap_percentage"].get("usdt", 0)
        usdc_percent = data["market_cap_percentage"].get("usdc", 0)
        stablecoin_ratio = usdt_percent + usdc_percent

        return total_mcap, btc_dominance, eth_dominance, stablecoin_ratio
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error parsing market data: {e}{Style.RESET_ALL}")
        return None, None, None, None


def compute_bubble_score(fear_greed, alt_index, stablecoin_ratio):
    """Weighted score combining sentiment, alt season, and stablecoin ratio"""
    score = 0
    if fear_greed is not None:
        score += fear_greed * 0.4
    if alt_index is not None:
        score += alt_index * 0.4
    if stablecoin_ratio is not None:
        score += (100 - stablecoin_ratio) * 0.2
    return round(score, 2)


def format_usd(value):
    """Format number in T, B, or M for readability"""
    if value is None:
        return "N/A"
    try:
        if value >= 1_000_000_000_000:
            return f"${value / 1_000_000_000_000:.2f}T"
        elif value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        else:
            return f"${value / 1_000_000:.2f}M"
    except:
        return "N/A"


def risk_bar(score, colored=True):
    """Generate bubble bar (color for console, plain for Telegram)"""
    if score is None:
        return "N/A"
    filled_blocks = int(min(max(score, 0), 100) / 5)
    bar = ""
    for i in range(20):
        if i < filled_blocks:
            if colored:
                if score >= 80:
                    bar += f"{Fore.RED}█"
                elif score >= 65:
                    bar += f"{Fore.LIGHTRED_EX}█"
                elif score >= 50:
                    bar += f"{Fore.YELLOW}█"
                else:
                    bar += f"{Fore.GREEN}█"
            else:
                bar += "█"
        else:
            bar += f"{Fore.WHITE + '░' if colored else '░'}"
    return bar + (Style.RESET_ALL if colored else "")


# ====================================
# MAIN
# ====================================

def main():
    now = datetime.datetime.now(MYT).strftime("%Y-%m-%d %H:%M")
    print(f"\n🧭 {Fore.CYAN}Crypto Market Sentiment ({now} MYT){Style.RESET_ALL}")

    fear_greed = fetch_fear_greed()
    alt_index = fetch_altcoin_season()
    total_mcap, btc_dom, eth_dom, stablecoin_ratio = fetch_market_data()
    bubble_score = compute_bubble_score(fear_greed, alt_index, stablecoin_ratio)
    if bubble_score is None:
        bubble_score = 0.0

    # =============================
    # ALERT LEVELS
    # =============================
    if bubble_score >= 80:
        level = "🚨 <b>EXTREME RISK</b> 🚨"
        action = (
            "🛑 <b>MARKET OVERHEATING!</b>\n"
            "🔥 TAKE PROFITS NOW.\n"
            "⚡ EXPECT HIGH VOLATILITY."
        )
        color = Fore.RED

    elif bubble_score >= 65:
        level = "🔴 <b>HIGH RISK</b>"
        action = (
            "⚠️ <b>MARKET RUNNING HOT.</b>\n"
            "📈 TAKE PARTIAL PROFITS OR SET STOP-LOSS.\n"
            "👀 WATCH FOR REVERSALS."
        )
        color = Fore.LIGHTRED_EX

    elif bubble_score >= 50:
        level = "🟠 <b>NEUTRAL / CAUTIOUS</b>"
        action = (
            "😐 <b>MIXED SENTIMENT.</b>\n"
            "⏳ WAIT FOR CLEARER DIRECTION.\n"
            "📊 MONITOR KEY SUPPORT LEVELS."
        )
        color = Fore.YELLOW

    else:
        level = "🟢 <b>STABLE / CALM</b>"
        action = (
            "💤 <b>LOW VOLATILITY.</b>\n"
            "🪙 IDEAL FOR ACCUMULATION ON DIPS.\n"
            "📉 RISK REMAINS LOW."
        )
        color = Fore.GREEN

    # =============================
    # DISPLAY DATA
    # =============================
    fear_greed_txt = fear_greed if fear_greed is not None else "N/A"
    alt_index_txt = alt_index if alt_index is not None else "N/A"
    stablecoin_txt = f"{stablecoin_ratio:.2f}%" if stablecoin_ratio is not None else "N/A"
    total_mcap_txt = format_usd(total_mcap)
    btc_dom_txt = f"{btc_dom:.2f}%" if btc_dom is not None else "N/A"
    eth_dom_txt = f"{eth_dom:.2f}%" if eth_dom is not None else "N/A"

    bar_colored = risk_bar(bubble_score, colored=True)
    bar_plain = risk_bar(bubble_score, colored=False)

    msg = f"""
🧭 <b>Crypto Market Sentiment Alert</b>
📅 <b>{now} (MYT)</b>

💵 <b>Total Market Cap:</b> {total_mcap_txt}
🪙 <b>BTC Dominance:</b> {btc_dom_txt}
🔷 <b>ETH Dominance:</b> {eth_dom_txt}
💰 <b>Stablecoin Ratio:</b> {stablecoin_txt}
🌈 <b>Altcoin Season Index:</b> {alt_index_txt}
😨 <b>Fear & Greed Index:</b> {fear_greed_txt}
🧠 <b>Bubble Risk Score:</b> {bubble_score}/100
<pre>{bar_plain}</pre>

<b>{level}</b>
{action}
""".strip()

    # Console output (colored, with banner for EXTREME RISK)
    plain_msg = msg.replace("<b>", "").replace("</b>", "")
    if "EXTREME RISK" in level:
        print(f"{Fore.RED}{'='*60}")
        print(f"🔥🔥🔥  MARKET OVERHEATING ALERT  🔥🔥🔥")
        print(f"{'='*60}{Style.RESET_ALL}\n")
        print(color + plain_msg + Style.RESET_ALL)
        print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
    else:
        print(color + plain_msg + Style.RESET_ALL)
    print(bar_colored)

    # Telegram message
    send_telegram_message(msg)


if __name__ == "__main__":
    main()
