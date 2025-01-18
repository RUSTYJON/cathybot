import irc.bot
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

class SingleChannelBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667, nickserv_password=None):
        # Initialize the bot with NickServ password support
        self.channel = channel
        self.nickserv_password = nickserv_password
        logger.debug(f"Initializing bot for channel: {channel}")
        super().__init__([(server, port)], nickname, nickname)
        logger.debug(f"Bot initialized with nickname: {nickname} on server: {server}")

    def on_welcome(self, c, e):
        logger.debug("Connected to server, joining channel...")

        # Identify to NickServ if password is provided
        if self.nickserv_password:
            logger.debug("Identifying to NickServ...")
            c.send(f"PRIVMSG NickServ :IDENTIFY {self.nickserv_password}")
            logger.debug("Sent IDENTIFY command to NickServ")

        # Join the specified channel
        logger.debug(f"Attempting to join channel: {self.channel}")
        c.join(self.channel)
        logger.debug(f"Bot joined channel: {self.channel}")

    def on_pubmsg(self, c, e):
        message = e.arguments[0]
        channel = e.target
        logger.debug(f"Received message in {channel}: {message}")

        # Handle stock commands
        if message.startswith("!stock"):
            self.handle_stock_command(c, message, channel)

        # Handle URLs
        else:
            urls = self.extract_urls(message)
            for url in urls:
                if "youtube.com" in url or "youtu.be" in url:
                    video_id = self.get_youtube_video_id(url)
                    if video_id:
                        title = self.get_youtube_video_title(video_id)
                        if title:
                            logger.debug(f"Fetched YouTube title: {title}")
                            c.privmsg(channel, f"YouTube Title: {title}")
                else:
                    description = self.get_webpage_description(url)
                    if description:
                        logger.debug(f"Fetched webpage description: {description}")
                        c.privmsg(channel, f"Page Info: {description}")

    # Extract URLs from a message
    def extract_urls(self, text):
        urls = [word for word in text.split() if word.startswith("http")]
        logger.debug(f"Extracted URLs: {urls}")
        return urls

    # Fetch YouTube video ID
    def get_youtube_video_id(self, url):
        logger.debug(f"Extracting video ID from URL: {url}")
        if "watch?v=" in url:
            return url.split("watch?v=")[1].split("&")[0]
        elif "/shorts/" in url:
            return url.split("/shorts/")[1].split("?")[0]
        elif "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        return None

    # Fetch YouTube video title
    def get_youtube_video_title(self, video_id):
        logger.debug(f"Fetching YouTube title for video ID: {video_id}")
        try:
            response = requests.get(f"https://www.youtube.com/watch?v={video_id}")
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            title = soup.title.string if soup.title else "No Title Found"
            return title.replace("- YouTube", "").strip()
        except Exception as e:
            logger.error(f"Error fetching YouTube title: {e}")
            return None

    # Fetch webpage metadata
    def get_webpage_description(self, url):
        logger.debug(f"Fetching webpage description for URL: {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            title = soup.title.string.strip() if soup.title else "No Title"
            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag else "No Description"
            return f"Title: {title}, Description: {meta_desc}"
        except Exception as e:
            logger.error(f"Error fetching webpage description: {e}")
            return None

    # Handle stock commands
    def handle_stock_command(self, c, message, channel):
        logger.debug(f"Processing stock command: {message}")
        parts = message.split()
        if len(parts) == 2:
            ticker = parts[1].upper()
            stock_info = self.get_stock_price(ticker)
            if stock_info:
                c.privmsg(channel, stock_info)
            else:
                c.privmsg(channel, f"Could not retrieve data for ticker: {ticker}")
        else:
            c.privmsg(channel, "Usage: !stock TICKER")

    # Fetch stock price with fallback to previous close or after-hours/pre-market data
    def get_stock_price(self, ticker):
        logger.debug(f"Fetching stock price for ticker: {ticker}")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Log the entire info dictionary for debugging purposes
            logger.debug(f"Stock info: {info}")

            # Check if 'regularMarketPrice', 'preMarketPrice', or 'regularMarketPreviousClose' is available
            current_price = info.get("regularMarketPrice", None)
            previous_close = info.get("regularMarketPreviousClose", None)
            after_hours = info.get("postMarketPrice", None)
            pre_market = info.get("preMarketPrice", None)
            
            company_name = info.get("longName", ticker)
            currency = info.get("currency", "N/A")
            
            # If no real-time price, use pre-market, after-hours or previous close price
            if current_price is None:
                if pre_market is not None:
                    return f"{company_name} ({ticker}) is trading at {pre_market} {currency} in pre-market trading."
                elif after_hours is not None:
                    return f"{company_name} ({ticker}) is trading at {after_hours} {currency} in after-hours trading."
                elif previous_close is not None:
                    return f"{company_name} ({ticker}) closed at {previous_close} {currency} on the last trading day."
                else:
                    return f"No price data available for ticker: {ticker}"
            
            return f"{company_name} ({ticker}) is currently trading at {current_price} {currency}"

        except Exception as e:
            logger.error(f"Error fetching stock price for {ticker}: {e}")
            return f"Error fetching data for ticker: {ticker}. Please try again later."


if __name__ == "__main__":
    bot = SingleChannelBot(
        channel="#guns",            # Replace with your channel
        nickname="Cathy",              # Replace with your bot's nickname
        server="tx.usairc.org",           # Replace with your IRC server address
        port=6667,                         # Default port for IRC
        nickserv_password="XXXXXXXXXXX"   # Replace with your NickServ password
    )
    bot.start()

