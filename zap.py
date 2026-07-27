import os
import sys
import io
import logging
import asyncio
from typing import Dict, Any, List, Optional

# --- Third-party Library Imports with Graceful Fallbacks ---
try:
    from telegram import (
        Update,
        ReplyKeyboardMarkup,
        KeyboardButton,
        InlineKeyboardButton,
        InlineKeyboardMarkup,
    )
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        ConversationHandler,
        filters,
    )
except ImportError:
    print("Error: 'python-telegram-bot' (v20+) is required.")
    print("Install it using: pip install python-telegram-bot")
    sys.exit(1)

try:
    import pymongo
except ImportError:
    pymongo = None

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
class Config:
    """Application configuration and constants."""
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8800707730:AAHm2hGRHU0tH8hEAm_3StnHep2qpD2NXUk")
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    ADMIN_IDS: List[int] = [
        int(x.strip())
        for x in os.getenv("ADMIN_IDS", "6325764594").split(",")
        if x.strip().isdigit()
    ]
    DEFAULT_FREE_SEARCHES: int = 3
    DEFAULT_CREDITS: int = 0
    MAX_TEXT_LIMIT: int = 3500  # Character threshold to split/convert to file
    BRANDING_FOOTER: str = "🔥 ZAP PAPA"


# ==============================================================================
# 2. DATABASE LAYER (MongoDB + In-Memory Fallback)
# ==============================================================================
class Database:
    """Database Handler with MongoDB connection & In-Memory fallback."""

    def __init__(self, uri: str):
        self.use_mongo = False
        self._in_memory_db: Dict[int, Dict[str, Any]] = {}

        if pymongo:
            try:
                self.client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
                self.client.admin.command("ping")
                self.db = self.client["zap_papa_db"]
                self.users = self.db["users"]
                self.use_mongo = True
                logger.info("Successfully connected to MongoDB database.")
            except Exception as e:
                logger.warning(f"MongoDB connection failed ({e}). Falling back to In-Memory storage.")
                self.use_mongo = False
        else:
            logger.warning("pymongo module not installed. Defaulting to In-Memory storage.")

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Retrieve user profile or create a default one if not exists."""
        default_user = {
            "user_id": user_id,
            "credits": Config.DEFAULT_CREDITS,
            "free_searches": Config.DEFAULT_FREE_SEARCHES,
            "total_searches": 0,
            "is_admin": user_id in Config.ADMIN_IDS,
        }

        if self.use_mongo:
            user = self.users.find_one({"user_id": user_id})
            if not user:
                self.users.insert_one(default_user)
                return default_user
            return user
        else:
            if user_id not in self._in_memory_db:
                self._in_memory_db[user_id] = default_user
            return self._in_memory_db[user_id]

    def update_user(self, user_id: int, data: Dict[str, Any]) -> None:
        """Update fields for a user profile."""
        if self.use_mongo:
            self.users.update_one({"user_id": user_id}, {"$set": data})
        else:
            if user_id in self._in_memory_db:
                self._in_memory_db[user_id].update(data)

    def consume_search(self, user_id: int) -> bool:
        """Deduct free search or credit. Returns True if successful, False if insufficient balance."""
        user = self.get_user(user_id)
        if user["free_searches"] > 0:
            user["free_searches"] -= 1
            user["total_searches"] += 1
            self.update_user(user_id, user)
            return True
        elif user["credits"] > 0:
            user["credits"] -= 1
            user["total_searches"] += 1
            self.update_user(user_id, user)
            return True
        return False

    def add_credits(self, user_id: int, amount: int) -> bool:
        """Add credits to a targeted user."""
        user = self.get_user(user_id)
        user["credits"] += amount
        self.update_user(user_id, user)
        return True

    def get_stats(self) -> Dict[str, int]:
        """Fetch general bot stats."""
        if self.use_mongo:
            total_users = self.users.count_documents({})
            pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_searches"}}}]
            res = list(self.users.aggregate(pipeline))
            total_searches = res[0]["total"] if res else 0
        else:
            total_users = len(self._in_memory_db)
            total_searches = sum(u["total_searches"] for u in self._in_memory_db.values())

        return {"total_users": total_users, "total_searches": total_searches}

    def get_all_users(self) -> List[int]:
        """Get all user IDs for broadcasting."""
        if self.use_mongo:
            return [doc["user_id"] for doc in self.users.find({}, {"user_id": 1})]
        return list(self._in_memory_db.keys())


# Global Database Instance
db = Database(Config.MONGO_URI)


# ==============================================================================
# 3. API CLIENT (Simulated OSINT / Search Interface)
# ==============================================================================
class APIClient:
    """Simulated API Client engine for information lookups."""

    @staticmethod
    async def perform_lookup(lookup_type: str, query: str) -> Dict[str, Any]:
        """Mock lookup processing async handler."""
        await asyncio.sleep(1.0)  # Simulate network latency

        # Abstract mock outputs (ensures zero disclosure of sensitive personal records)
        if "aadhaar" in lookup_type.lower():
            return {
                "Target Query": query,
                "Status": "Record Processed",
                "Verification Category": "Aadhaar System Identifier",
                "Reference ID": "REF-8839210-X",
                "Verification Result": "Valid Record Tagged",
                "Note": "Data provided for general verification purposes.",
            }

        return {
            "Query": query,
            "Module": lookup_type,
            "Status": "Active Match Found",
            "Data Field A": f"Result for {query}",
            "Data Field B": "Verified Record Entry",
            "Source System": "ZAP PAPA Indexer v2.1",
        }


# ==============================================================================
# 4. FORMATTER
# ==============================================================================
class Formatter:
    """Formats output strings and payloads to match the ZAP PAPA style guide."""

    @staticmethod
    def format_result(data: Dict[str, Any]) -> str:
        """Format key-value records into standard structured response box."""
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━",
            "SEARCH RESULT",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        for key, val in data.items():
            lines.append(f"{key} : {val}")

        lines.extend(["", "━━━━━━━━━━━━━━━━━━━━━━", Config.BRANDING_FOOTER])
        return "\n".join(lines)

    @staticmethod
    def format_profile(user: Dict[str, Any]) -> str:
        """Format user profile block."""
        return (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "👤 USER PROFILE\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"User ID          : `{user['user_id']}`\n"
            f"Credits          : {user['credits']}\n"
            f"Free Searches    : {user['free_searches']}\n"
            f"Total Searches   : {user['total_searches']}\n"
            f"Role             : {'Admin' if user['is_admin'] else 'Member'}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{Config.BRANDING_FOOTER}"
        )


# ==============================================================================
# 5. BOT HANDLERS & CONVERSATION MANAGEMENT
# ==============================================================================
# Conversation states
AWAIT_QUERY = 1


class BotHandlers:
    """Primary User Telegram Bot Handlers."""

    @staticmethod
    def get_main_keyboard() -> ReplyKeyboardMarkup:
        """Main UI Reply Keyboard Layout."""
        keyboard = [
            [KeyboardButton("🔍 Username Lookup"), KeyboardButton("📱 Number Lookup")],
            [KeyboardButton("🆔 Aadhaar Lookup"), KeyboardButton("📧 Email Lookup")],
            [KeyboardButton("👤 Name Lookup"), KeyboardButton("📍 Address Lookup")],
            [KeyboardButton("💎 Premium"), KeyboardButton("👤 My Profile")],
            [KeyboardButton("💳 Buy Credits"), KeyboardButton("⚙️ Admin Panel")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @classmethod
    async def start(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler."""
        user = update.effective_user
        db.get_user(user.id)
        welcome_text = (
            f"Welcome to *ZAP PAPA*, {user.mention_markdown_v2()}!\n\n"
            "Select an option from the menu keyboard below to perform a lookup."
        )
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=cls.get_main_keyboard(),
        )

    @classmethod
    async def my_profile(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Render user profile."""
        user_data = db.get_user(update.effective_user.id)
        msg = Formatter.format_profile(user_data)
        await update.message.reply_text(msg, parse_mode="Markdown")

    @classmethod
    async def buy_credits(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display credit purchasing instructions."""
        info = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💳 BUY CREDITS\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "To purchase additional credits or access Premium features, "
            "contact the platform administrator directly.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{Config.BRANDING_FOOTER}"
        )
        await update.message.reply_text(info)

    @classmethod
    async def handle_search_request(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Triggered when a user clicks any lookup button."""
        lookup_type = update.message.text
        context.user_data["active_lookup"] = lookup_type

        # Check search availability
        user_data = db.get_user(update.effective_user.id)
        if user_data["free_searches"] <= 0 and user_data["credits"] <= 0:
            await update.message.reply_text(
                "❌ You do not have sufficient free searches or credits remaining.\n"
                "Please purchase credits to continue using the service."
            )
            return ConversationHandler.END

        await update.message.reply_text(
            f"Please enter the query for *{lookup_type}*:",
            parse_mode="Markdown",
        )
        return AWAIT_QUERY

    @classmethod
    async def process_search_query(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process the user input query."""
        query = update.message.text
        lookup_type = context.user_data.get("active_lookup", "Search")
        user_id = update.effective_user.id

        # Consume search allowance
        if not db.consume_search(user_id):
            await update.message.reply_text("❌ Insufficient search allowance.")
            return ConversationHandler.END

        status_msg = await update.message.reply_text("⏳ Processing lookup query...")

        # Perform API lookup
        raw_result = await APIClient.perform_lookup(lookup_type, query)
        formatted_output = Formatter.format_result(raw_result)

        # Handle Copy / Utility Buttons
        inline_kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📋 Copy Query", copy_text=query)]]
        )

        # Output handling: Split or Send File if output exceeds threshold
        if len(formatted_output) > Config.MAX_TEXT_LIMIT:
            await status_msg.edit_text("📄 Output is too large. Generating downloadable document...")
            file_bytes = io.BytesIO(formatted_output.encode("utf-8"))
            file_bytes.name = f"result_{user_id}.txt"
            await update.message.reply_document(
                document=file_bytes,
                caption=f"Result for query: `{query}`\n\n{Config.BRANDING_FOOTER}",
                parse_mode="Markdown",
            )
        else:
            await status_msg.delete()
            await update.message.reply_text(
                formatted_output,
                reply_markup=inline_kb,
            )

        return ConversationHandler.END

    @classmethod
    async def cancel_search(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel ongoing search conversation."""
        await update.message.reply_text("Operation cancelled.", reply_markup=cls.get_main_keyboard())
        return ConversationHandler.END


# ==============================================================================
# 6. ADMIN HANDLERS
# ==============================================================================
class AdminHandlers:
    """Administrative Commands and Management Handlers."""

    @staticmethod
    def is_admin(user_id: int) -> bool:
        user = db.get_user(user_id)
        return user.get("is_admin", False)

    @classmethod
    async def admin_panel(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not cls.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Access Denied: Admin privileges required.")
            return

        menu = (
            "⚙️ **ADMIN PANEL**\n\n"
            "Available Admin Commands:\n"
            "• `/stats` — View bot global usage statistics\n"
            "• `/users` — Count registered platform accounts\n"
            "• `/addcredits <user_id> <amount>` — Grant credits to a user\n"
            "• `/broadcast <message>` — Send announcement to all users"
        )
        await update.message.reply_text(menu, parse_mode="Markdown")

    @classmethod
    async def stats(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not cls.is_admin(update.effective_user.id):
            return
        st = db.get_stats()
        text = (
            "📊 **SYSTEM STATISTICS**\n\n"
            f"Total Registered Users: {st['total_users']}\n"
            f"Total Searches Served: {st['total_searches']}\n"
            f"Database Mode: {'MongoDB' if db.use_mongo else 'In-Memory Engine'}\n\n"
            f"{Config.BRANDING_FOOTER}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    @classmethod
    async def users_count(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not cls.is_admin(update.effective_user.id):
            return
        users = db.get_all_users()
        await update.message.reply_text(f"👥 Total registered users: `{len(users)}`", parse_mode="Markdown")

    @classmethod
    async def add_credits(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not cls.is_admin(update.effective_user.id):
            return

        try:
            target_id = int(context.args[0])
            amount = int(context.args[1])
            db.add_credits(target_id, amount)
            await update.message.reply_text(
                f"✅ Successfully added `{amount}` credits to user `{target_id}`.",
                parse_mode="Markdown",
            )
        except (IndexError, ValueError):
            await update.message.reply_text("Usage: `/addcredits <user_id> <amount>`", parse_mode="Markdown")

    @classmethod
    async def broadcast(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not cls.is_admin(update.effective_user.id):
            return

        message = " ".join(context.args)
        if not message:
            await update.message.reply_text("Usage: `/broadcast <message>`")
            return

        all_users = db.get_all_users()
        count = 0
        for uid in all_users:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"📢 **BROADCAST ANNOUNCEMENT**\n\n{message}\n\n{Config.BRANDING_FOOTER}",
                    parse_mode="Markdown",
                )
                count += 1
                await asyncio.sleep(0.05)  # Avoid rate limits
            except Exception:
                pass

        await update.message.reply_text(f"✅ Broadcast complete. Delivered to {count}/{len(all_users)} users.")


# ==============================================================================
# 7. TERMUX CLI INTERFACE
# ==============================================================================
class TermuxCLI:
    """Interactive CLI engine designed for Termux environment execution."""

    @staticmethod
    def print_banner():
        banner = """
╔══════════════════════════════╗
║        🔥 ZAP PAPA 🔥        ║
║    Telegram Utility Tool     ║
╚══════════════════════════════╝
"""
        print(banner)

    @classmethod
    def start_cli(cls):
        cls.print_banner()
        while True:
            print("\nMenu:")
            print("1 Username Lookup")
            print("2 Number Lookup")
            print("3 Profile")
            print("4 Stats")
            print("0 Exit")

            choice = input("\nSelect Option > ").strip()

            if choice == "1":
                q = input("Enter Username: ")
                res = asyncio.run(APIClient.perform_lookup("Username Lookup", q))
                print("\n" + Formatter.format_result(res))
            elif choice == "2":
                q = input("Enter Number: ")
                res = asyncio.run(APIClient.perform_lookup("Number Lookup", q))
                print("\n" + Formatter.format_result(res))
            elif choice == "3":
                uid = input("Enter your User ID (default: 1000): ").strip()
                user_id = int(uid) if uid.isdigit() else 1000
                user = db.get_user(user_id)
                print("\n" + Formatter.format_profile(user))
            elif choice == "4":
                st = db.get_stats()
                print(f"\nTotal Users: {st['total_users']} | Total Searches: {st['total_searches']}")
            elif choice == "0":
                print("\nExiting ZAP PAPA CLI. Goodbye!\n")
                break
            else:
                print("Invalid selection. Try again.")


# ==============================================================================
# 8. APPLICATION ENTRYPOINT
# ==============================================================================
def main():
    """Main execution router (CLI vs Bot Mode)."""
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        TermuxCLI.start_cli()
        return

    if Config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Warning: BOT_TOKEN is not configured in Config / environment.")
        print("Launching Termux CLI Mode automatically...\n")
        TermuxCLI.start_cli()
        return

    # Build python-telegram-bot Application instance
    app = Application.builder().token(Config.BOT_TOKEN).build()

    # Define Search Conversation Handler
    search_conv = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^(🔍 Username Lookup|📱 Number Lookup|🆔 Aadhaar Lookup|📧 Email Lookup|👤 Name Lookup|📍 Address Lookup)$"),
                BotHandlers.handle_search_request,
            )
        ],
        states={
            AWAIT_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, BotHandlers.process_search_query)
            ]
        },
        fallbacks=[CommandHandler("cancel", BotHandlers.cancel_search)],
    )

    # Register Handlers
    app.add_handler(CommandHandler("start", BotHandlers.start))
    app.add_handler(MessageHandler(filters.Regex("^👤 My Profile$"), BotHandlers.my_profile))
    app.add_handler(MessageHandler(filters.Regex("^💎 Premium$"), BotHandlers.buy_credits))
    app.add_handler(MessageHandler(filters.Regex("^💳 Buy Credits$"), BotHandlers.buy_credits))
    app.add_handler(MessageHandler(filters.Regex("^⚙️ Admin Panel$"), AdminHandlers.admin_panel))
    app.add_handler(search_conv)

    # Admin Command Handlers
    app.add_handler(CommandHandler("stats", AdminHandlers.stats))
    app.add_handler(CommandHandler("users", AdminHandlers.users_count))
    app.add_handler(CommandHandler("addcredits", AdminHandlers.add_credits))
    app.add_handler(CommandHandler("broadcast", AdminHandlers.broadcast))

    print("🔥 Starting ZAP PAPA Bot Server...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()


# ==============================================================================
# REQUIREMENTS & INSTALLATION INSTRUCTIONS
# ==============================================================================
# To install the required dependencies on Linux/Termux/Windows, run:
#
# pip install python-telegram-bot pymongo
#
# Usage Instructions:
# 1. Run Telegram Bot mode:
#    export BOT_TOKEN="your_token_here"
#    export MONGO_URI="mongodb://localhost:27017"
#    python main.py
#
# 2. Run Termux CLI mode:
#    python main.py --cli
# ==============================================================================
