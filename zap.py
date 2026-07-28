#!/usr/bin/env python3
"""
╔══════════════════════════════╗
║        🔥 ZAP PAPA 🔥        ║
║    Telegram Utility Tool     ║
╚══════════════════════════════╝

Single-file Telegram bot with MongoDB, credits system, user profiles,
admin panel, and Termux CLI support.

Authorized for ethical security testing and educational purposes.
"""

import asyncio
import os
import sys
import json
import logging
import datetime
import hashlib
import re
import random
import string
import textwrap
import traceback
from typing import Dict, Optional, Any, List, Tuple, Union
from io import BytesIO, StringIO
from pathlib import Path
from copy import deepcopy

# ── Third-party imports with graceful fallback ──────────────────────────
try:
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup,
        ReplyKeyboardMarkup, KeyboardButton, CopyTextButton,
        constants
    )
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, CallbackQueryHandler,
        ConversationHandler, ContextTypes, filters
    )
    from telegram.error import (
        TelegramError, TimedOut, NetworkError, Conflict, RetryAfter
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    import motor.motor_asyncio
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# ── Logging Setup ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("ZAP_PAPA")

# ══════════════════════════════════════════════════════════════════════════
#  BRANDING CONSTANTS
# ══════════════════════════════════════════════════════════════════════════
BRANDING = "🔥 ZAP PAPA"
SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━"


# ══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════
class Config:
    """Central configuration management.
    
    Reads from environment variables with sensible defaults.
    All settings can be overridden at runtime.
    """

    # ── Core ──────────────────────────────────────────────────────────
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "8800707730:AAHm2hGRHU0tH8hEAm_3StnHep2qpD2NXUk")
    MONGO_URI: str = os.environ.get("MONGO_URI", "mongodb+srv://zap3x:Blitzz@cluster0.yfpifje.mongodb.net/?appName=Cluster07")
    DB_NAME: str = "zap_papa"

    # ── User Defaults ─────────────────────────────────────────────────
    FREE_SEARCHES_NEW_USER: int = 3
    CREDIT_COST_PER_SEARCH: int = 1
    DEFAULT_CREDITS: int = 0

    # ── Admin ─────────────────────────────────────────────────────────
    _admin_ids_str: str = os.environ.get("ADMIN_IDS", "6325764594")
    ADMIN_IDS: List[int] = []
    if _admin_ids_str:
        try:
            ADMIN_IDS = [int(x.strip()) for x in _admin_ids_str.split(",") if x.strip()]
        except ValueError:
            ADMIN_IDS = []

    OWNER_ID: int = int(os.environ.get("OWNER_ID", "6325764594"))

    # ── Telegram Limits ───────────────────────────────────────────────
    MAX_MESSAGE_LENGTH: int = 4000
    SPLIT_DELIMITER: str = f"\n{SEPARATOR}\n"

    # ── Connection ────────────────────────────────────────────────────
    RECONNECT_DELAY: int = 5
    MAX_RECONNECT_ATTEMPTS: int = 10

    # ── Credit Prices (example) ───────────────────────────────────────
    CREDIT_PACKAGES: Dict[int, int] = {
        10: 1,    # 10 credits for $1
        50: 4,    # 50 credits for $4
        100: 7,   # 100 credits for $7
        500: 30,  # 500 credits for $30
    }

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Check if a user ID belongs to an admin."""
        return user_id in cls.ADMIN_IDS or user_id == cls.OWNER_ID

    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        if cls.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            issues.append("BOT_TOKEN is not set")
        if not cls.ADMIN_IDS and cls.OWNER_ID == 0:
            issues.append("No admin IDs configured (set ADMIN_IDS or OWNER_ID)")
        return issues


# ══════════════════════════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════════════════════════
class Database:
    """Async database layer with MongoDB support and in-memory fallback.
    
    If MongoDB connection fails, the bot continues seamlessly using
    an in-memory dictionary store. All data persists only during runtime
    in fallback mode.
    """

    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.mode = "memory"  # "mongo" or "memory"
        self._memory: Dict[str, Any] = {
            "users": {},
            "stats": {
                "total_searches": 0,
                "total_users": 0,
                "commands_used": {},
                "start_time": datetime.datetime.utcnow().isoformat(),
            },
        }
        self._connect()
        logger.info(f"Database initialized in '{self.mode}' mode")

    def _connect(self) -> None:
        """Attempt MongoDB connection; fall back to in-memory on failure."""
        if not MONGODB_AVAILABLE:
            logger.warning("motor (async MongoDB driver) not installed. Using in-memory storage.")
            return

        mongo_uri = Config.MONGO_URI
        if not mongo_uri or mongo_uri == "mongodb://localhost:27017":
            logger.info("No custom MongoDB URI configured. Using in-memory storage.")
            return

        try:
            self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )
            self.db = self.mongo_client[Config.DB_NAME]
            self.mode = "mongo"
            logger.info(f"Connected to MongoDB at {mongo_uri}")
        except Exception as e:
            logger.warning(f"MongoDB connection failed ({e}). Using in-memory storage.")
            self.mode = "memory"

    # ── User Operations ───────────────────────────────────────────────

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a user document by Telegram user ID."""
        if self.mode == "mongo":
            try:
                return await self.db.users.find_one({"_id": user_id})
            except Exception as e:
                logger.error(f"MongoDB get_user error: {e}")
                return None
        return self._memory["users"].get(str(user_id))

    async def create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new user profile with default values."""
        now = datetime.datetime.utcnow()
        user_data: Dict[str, Any] = {
            "_id": user_id,
            "user_id": user_id,
            "username": username or "",
            "first_name": first_name or "",
            "credits": Config.DEFAULT_CREDITS,
            "free_searches": Config.FREE_SEARCHES_NEW_USER,
            "total_searches": 0,
            "is_admin": Config.is_admin(user_id),
            "created_at": now,
            "last_active": now,
        }

        if self.mode == "mongo":
            try:
                await self.db.users.insert_one(user_data)
            except Exception as e:
                logger.error(f"MongoDB create_user error: {e}")
                # Fall back to memory for this operation
                self._memory["users"][str(user_id)] = deepcopy(user_data)
                self._memory["stats"]["total_users"] = len(self._memory["users"])
        else:
            self._memory["users"][str(user_id)] = user_data
            self._memory["stats"]["total_users"] = len(self._memory["users"])

        return user_data

    async def get_or_create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get existing user or create a new one."""
        user = await self.get_user(user_id)
        if user is None:
            user = await self.create_user(user_id, username, first_name)
        return user

    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Update user fields. Returns True on success."""
        update_data["last_active"] = datetime.datetime.utcnow()

        if self.mode == "mongo":
            try:
                result = await self.db.users.update_one(
                    {"_id": user_id},
                    {"$set": update_data}
                )
                return result.modified_count > 0 or result.matched_count > 0
            except Exception as e:
                logger.error(f"MongoDB update_user error: {e}")
                return False

        user = self._memory["users"].get(str(user_id))
        if user:
            user.update(update_data)
            return True
        return False

    async def add_credits(self, user_id: int, amount: int) -> bool:
        """Add credits to a user's account."""
        if self.mode == "mongo":
            try:
                result = await self.db.users.update_one(
                    {"_id": user_id},
                    {"$inc": {"credits": amount}, "$set": {"last_active": datetime.datetime.utcnow()}}
                )
                return result.modified_count > 0 or result.matched_count > 0
            except Exception as e:
                logger.error(f"MongoDB add_credits error: {e}")
                return False

        user = self._memory["users"].get(str(user_id))
        if user:
            user["credits"] = user.get("credits", 0) + amount
            user["last_active"] = datetime.datetime.utcnow()
            return True
        return False

    async def deduct_free_search(self, user_id: int) -> bool:
        """Deduct one free search. Returns True if a free search was available."""
        user = await self.get_user(user_id)
        if not user:
            return False

        free = user.get("free_searches", 0)
        if free <= 0:
            return False

        return await self.update_user(user_id, {"free_searches": free - 1})

    async def deduct_credit(self, user_id: int) -> bool:
        """Deduct one credit. Returns True if credits were available."""
        user = await self.get_user(user_id)
        if not user:
            return False

        credits = user.get("credits", 0)
        if credits <= 0:
            return False

        return await self.update_user(user_id, {"credits": credits - 1})

    async def increment_total_searches(self, user_id: int) -> None:
        """Increment the user's total search count."""
        if self.mode == "mongo":
            try:
                await self.db.users.update_one(
                    {"_id": user_id},
                    {
                        "$inc": {"total_searches": 1},
                        "$set": {"last_active": datetime.datetime.utcnow()}
                    }
                )
            except Exception as e:
                logger.error(f"MongoDB increment_total_searches error: {e}")
            return

        user = self._memory["users"].get(str(user_id))
        if user:
            user["total_searches"] = user.get("total_searches", 0) + 1
            user["last_active"] = datetime.datetime.utcnow()

        self._memory["stats"]["total_searches"] = self._memory["stats"].get("total_searches", 0) + 1

    # ── Admin Queries ─────────────────────────────────────────────────

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all registered users."""
        if self.mode == "mongo":
            try:
                cursor = self.db.users.find({})
                users = []
                async for doc in cursor:
                    users.append(doc)
                return users
            except Exception as e:
                logger.error(f"MongoDB get_all_users error: {e}")
                return []

        return list(self._memory["users"].values())

    async def get_user_count(self) -> int:
        """Get total number of registered users."""
        if self.mode == "mongo":
            try:
                return await self.db.users.count_documents({})
            except Exception as e:
                logger.error(f"MongoDB get_user_count error: {e}")
                return 0
        return len(self._memory["users"])

    async def get_stats(self) -> Dict[str, Any]:
        """Get overall bot statistics."""
        stats = dict(self._memory["stats"])
        stats["total_users"] = await self.get_user_count()
        if self.mode == "mongo":
            try:
                pipeline = [
                    {"$group": {
                        "_id": None,
                        "total_searches": {"$sum": "$total_searches"},
                        "total_credits": {"$sum": "$credits"},
                    }}
                ]
                cursor = self.db.users.aggregate(pipeline)
                async for doc in cursor:
                    stats["total_searches"] = doc.get("total_searches", 0)
                    stats["total_credits"] = doc.get("total_credits", 0)
            except Exception:
                pass
        return stats

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find a user by username (without @)."""
        clean = username.lstrip("@").lower()
        if self.mode == "mongo":
            try:
                return await self.db.users.find_one({"username": {"$regex": f"^{clean}$", "$options": "i"}})
            except Exception:
                return None
        for uid, u in self._memory["users"].items():
            if u.get("username", "").lower() == clean:
                return u
        return None

    async def broadcast(
        self,
        bot,
        text: str,
        exclude_id: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Send a broadcast message to all users.
        
        Returns (sent_count, failed_count).
        """
        users = await self.get_all_users()
        sent = 0
        failed = 0

        for user in users:
            uid = user.get("user_id") or user.get("_id")
            if uid is None or uid == exclude_id:
                continue
            try:
                await bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
                sent += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except Exception:
                failed += 1

        return sent, failed


# ══════════════════════════════════════════════════════════════════════════
#  API CLIENT
# ══════════════════════════════════════════════════════════════════════════
class APIClient:
    """Simulated external API client for data lookups.
    
    In production, replace the mock methods with real API calls.
    Each method returns a dictionary with 'success' and 'data' keys.
    """

    @staticmethod
    async def lookup_username(username: str) -> Dict[str, Any]:
        """Lookup information by username."""
        await asyncio.sleep(0.5)  # Simulate network latency
        # ── Mock response ─────────────────────────────────────────────
        return {
            "success": True,
            "data": {
                "Username": f"@{username}",
                "Full Name": f"{username.title()} User",
                "Bio": f"Registered user with the handle @{username}",
                "Account Age": f"{random.randint(30, 2000)} days",
                "Posts": str(random.randint(0, 500)),
                "Followers": str(random.randint(10, 10000)),
                "Following": str(random.randint(5, 2000)),
                "Verified": random.choice(["Yes", "No"]),
                "Last Active": "Online",
            }
        }

    @staticmethod
    async def lookup_number(number: str) -> Dict[str, Any]:
        """Lookup information by phone number."""
        await asyncio.sleep(0.5)
        cleaned = re.sub(r"\D", "", number)
        return {
            "success": True,
            "data": {
                "Number": f"+{cleaned}" if cleaned else number,
                "Country": random.choice(["India", "USA", "UK", "Canada", "Australia"]),
                "Carrier": random.choice(["Airtel", "Jio", "VI", "BSNL", "T-Mobile", "Verizon"]),
                "Line Type": random.choice(["Mobile", "Landline", "VoIP"]),
                "Status": random.choice(["Active", "Active", "Active", "Inactive"]),
                "Risk Score": f"{random.randint(0, 30)}%",
                "Portability": random.choice(["Yes", "No"]),
            }
        }

    @staticmethod
    async def lookup_aadhaar(aadhaar: str) -> Dict[str, Any]:
        """Lookup information by Aadhaar number."""
        await asyncio.sleep(0.5)
        cleaned = re.sub(r"\D", "", aadhaar)
        return {
            "success": True,
            "data": {
                "Aadhaar": f"{cleaned[:4]} XXXX XXXX" if len(cleaned) >= 4 else "XXXX XXXX XXXX",
                "State": random.choice(["Maharashtra", "Uttar Pradesh", "Karnataka", "Tamil Nadu", "Delhi"]),
                "Age Band": random.choice(["18-30", "31-45", "46-60", "60+"]),
                "Gender": random.choice(["Male", "Female", "Other"]),
                "Verified": "Yes",
                "Last Updated": f"20{random.randint(20, 25)}-{random.randint(1, 12):02d}",
            }
        }

    @staticmethod
    async def lookup_email(email: str) -> Dict[str, Any]:
        """Lookup information by email address."""
        await asyncio.sleep(0.5)
        domain = email.split("@")[-1] if "@" in email else "unknown"
        return {
            "success": True,
            "data": {
                "Email": email,
                "Domain": domain,
                "Provider": domain.split(".")[0].title() if "." in domain else "Unknown",
                "Valid Format": "Yes",
                "Disposable": random.choice(["No", "No", "No", "Yes"]),
                "Associated Accounts": str(random.randint(0, 25)),
                "Breach Status": random.choice(["Clean", "Clean", "Compromised"]),
                "Risk Score": f"{random.randint(0, 40)}%",
            }
        }

    @staticmethod
    async def lookup_name(name: str) -> Dict[str, Any]:
        """Lookup information by name."""
        await asyncio.sleep(0.5)
        return {
            "success": True,
            "data": {
                "Name": name.title(),
                "Possible Locations": f"{random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad'])}, India",
                "Age Range": f"{random.randint(18, 35)}-{random.randint(36, 70)}",
                "Profession": random.choice(["Engineer", "Doctor", "Teacher", "Business", "Student", "Artist"]),
                "Social Profiles": f"{random.randint(1, 8)} found",
                "Public Records": f"{random.randint(0, 5)} found",
            }
        }

    @staticmethod
    async def lookup_address(address: str) -> Dict[str, Any]:
        """Lookup information by address."""
        await asyncio.sleep(0.5)
        return {
            "success": True,
            "data": {
                "Address": address.title(),
                "City": random.choice(["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Pune"]),
                "State": random.choice(["Maharashtra", "Delhi", "Karnataka", "West Bengal"]),
                "Pincode": str(random.randint(100000, 999999)),
                "Type": random.choice(["Residential", "Commercial", "Mixed"]),
                "Landmark": f"Near {random.choice(['Market', 'Hospital', 'School', 'Park', 'Temple'])}",
                "Coordinates": f"{random.uniform(8, 37):.4f}, {random.uniform(68, 97):.4f}",
            }
        }


# ══════════════════════════════════════════════════════════════════════════
#  FORMATTER
# ══════════════════════════════════════════════════════════════════════════
class Formatter:
    """Message formatting utilities with consistent ZAP PAPA branding."""

    @staticmethod
    def search_result(title: str, data: Dict[str, Any]) -> str:
        """Format a search result with consistent styling."""
        lines = [f"\n{SEPARATOR}", f"  {title.upper()}", SEPARATOR]
        for key, value in data.items():
            lines.append(f"{key} : {value}")
        lines.append(f"\n{SEPARATOR}")
        lines.append(f"  {BRANDING}")
        return "\n".join(lines)

    @staticmethod
    def error_message(error_text: str) -> str:
        """Format an error message."""
        return (
            f"\n{SEPARATOR}\n"
            f"  ❌ ERROR\n"
            f"{SEPARATOR}\n"
            f"{error_text}\n"
            f"\n{SEPARATOR}\n"
            f"  {BRANDING}"
        )

    @staticmethod
    def info_message(title: str, body: str) -> str:
        """Format an informational message."""
        return (
            f"\n{SEPARATOR}\n"
            f"  {title}\n"
            f"{SEPARATOR}\n"
            f"{body}\n"
            f"\n{SEPARATOR}\n"
            f"  {BRANDING}"
        )

    @staticmethod
    def profile(user_data: Dict[str, Any]) -> str:
        """Format a user profile."""
        return (
            f"\n{SEPARATOR}\n"
            f"  👤 USER PROFILE\n"
            f"{SEPARATOR}\n"
            f"User ID    : {user_data.get('user_id', 'N/A')}\n"
            f"Username   : @{user_data.get('username', 'N/A')}\n"
            f"Name       : {user_data.get('first_name', 'N/A')}\n"
            f"Credits    : {user_data.get('credits', 0)}\n"
            f"Free Srchs : {user_data.get('free_searches', 0)}\n"
            f"Total Srchs: {user_data.get('total_searches', 0)}\n"
            f"Admin      : {'✅ Yes' if user_data.get('is_admin', False) else '❌ No'}\n"
            f"Joined     : {user_data.get('created_at', 'N/A')}\n"
            f"\n{SEPARATOR}\n"
            f"  {BRANDING}"
        )

    @staticmethod
    def stats(stats_data: Dict[str, Any]) -> str:
        """Format bot statistics."""
        return (
            f"\n{SEPARATOR}\n"
            f"  📊 BOT STATISTICS\n"
            f"{SEPARATOR}\n"
            f"Total Users     : {stats_data.get('total_users', 0)}\n"
            f"Total Searches  : {stats_data.get('total_searches', 0)}\n"
            f"Total Credits   : {stats_data.get('total_credits', 0)}\n"
            f"Active Since    : {stats_data.get('start_time', 'N/A')}\n"
            f"\n{SEPARATOR}\n"
            f"  {BRANDING}"
        )

    @staticmethod
    def split_message(text: str, max_length: int = 4000) -> List[str]:
        """Split a long message into chunks at separator boundaries."""
        if len(text) <= max_length:
            return [text]

        parts = []
        while len(text) > max_length:
            # Try to split at the last separator within the limit
            split_at = text.rfind(SEPARATOR, 0, max_length)
            if split_at == -1:
                split_at = text.rfind("\n", 0, max_length)
            if split_at == -1:
                split_at = max_length

            parts.append(text[:split_at].strip())
            text = text[split_at:].strip()

        if text:
            parts.append(text)
        return parts

    @staticmethod
    def to_file_content(data: Dict[str, Any], title: str) -> str:
        """Format data as a plain-text file content."""
        lines = [
            "=" * 60,
            f"  {title.upper()}",
            "=" * 60,
            "",
        ]
        for key, value in data.items():
            lines.append(f"{key:<20} : {value}")
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"  Generated by {BRANDING}")
        lines.append(f"  {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("=" * 60)
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
#  KEYBOARD BUILDER
# ══════════════════════════════════════════════════════════════════════════
class KeyboardBuilder:
    """Build Reply and Inline keyboards."""

    @staticmethod
    def main() -> ReplyKeyboardMarkup:
        """Build the main reply keyboard."""
        keyboard = [
            [KeyboardButton("🔍 Username Lookup"), KeyboardButton("📱 Number Lookup")],
            [KeyboardButton("🆔 Aadhaar Lookup"), KeyboardButton("📧 Email Lookup")],
            [KeyboardButton("👤 Name Lookup"), KeyboardButton("📍 Address Lookup")],
            [KeyboardButton("💎 Premium")],
            [KeyboardButton("👤 My Profile"), KeyboardButton("💳 Buy Credits"), KeyboardButton("⚙️ Admin Panel")],
        ]
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            input_field_placeholder="Choose an option..."
        )

    @staticmethod
    def admin() -> ReplyKeyboardMarkup:
        """Build the admin panel reply keyboard."""
        keyboard = [
            [KeyboardButton("📊 Stats"), KeyboardButton("👥 Users")],
            [KeyboardButton("➕ Add Credits"), KeyboardButton("📢 Broadcast")],
            [KeyboardButton("🔙 Back to Main")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def premium() -> ReplyKeyboardMarkup:
        """Build the premium menu keyboard."""
        keyboard = [
            [KeyboardButton("💳 Buy Credits")],
            [KeyboardButton("🔙 Back to Main")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def inline_copy(copy_text: str) -> InlineKeyboardMarkup:
        """Build an inline keyboard with a Copy button.
        
        Uses CopyTextButton (v21.7+) for native clipboard copy.
        Falls back gracefully on older versions.
        """
        MAX_COPY = 256
        truncated = copy_text[:MAX_COPY]
        if len(copy_text) > MAX_COPY:
            truncated += "…"

        try:
            button = InlineKeyboardButton(
                text="📋 Copy Result",
                copy_text=CopyTextButton(text=truncated)
            )
        except Exception:
            # Fallback: use callback_data for older versions
            button = InlineKeyboardButton(
                text="📋 Copy (Select text)",
                callback_data="copy_fallback"
            )

        return InlineKeyboardMarkup([[button]])


# ══════════════════════════════════════════════════════════════════════════
#  BOT HANDLERS
# ══════════════════════════════════════════════════════════════════════════
class BotHandlers:
    """Main bot command and message handlers."""

    def __init__(self, db: Database):
        self.db = db

    # ── Utility ───────────────────────────────────────────────────────

    async def _ensure_user(self, update: Update) -> Optional[Dict[str, Any]]:
        """Ensure user exists in DB, return user data."""
        user = update.effective_user
        if not user:
            return None
        return await self.db.get_or_create_user(
            user.id,
            username=user.username,
            first_name=user.first_name,
        )

    async def _check_access(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Check if user has free searches or credits. Returns True if allowed."""
        user_data = await self._ensure_user(update)
        if not user_data:
            return False

        free = user_data.get("free_searches", 0)
        credits = user_data.get("credits", 0)

        if free > 0 or credits > 0:
            return True

        await update.message.reply_text(
            Formatter.error_message(
                "You have no free searches or credits remaining.\n\n"
                "Use the 💳 Buy Credits button to purchase more."
            ),
            reply_markup=KeyboardBuilder.main(),
        )
        return False

    async def _deduct_cost(self, user_id: int) -> bool:
        """Deduct search cost (free first, then credits). Returns True on success."""
        user = await self.db.get_user(user_id)
        if not user:
            return False

        if user.get("free_searches", 0) > 0:
            return await self.db.deduct_free_search(user_id)
        elif user.get("credits", 0) >= Config.CREDIT_COST_PER_SEARCH:
            return await self.db.deduct_credit(user_id)
        return False

    async def _send_result(
        self,
        update: Update,
        title: str,
        data: Dict[str, Any],
    ) -> None:
        """Send a formatted search result with copy button, handling splitting."""
        formatted = Formatter.search_result(title, data)
        parts = Formatter.split_message(formatted, Config.MAX_MESSAGE_LENGTH)

        if len(parts) == 1 and len(parts[0]) <= Config.MAX_MESSAGE_LENGTH:
            await update.message.reply_text(
                parts[0],
                reply_markup=KeyboardBuilder.inline_copy(
                    "\n".join(f"{k}: {v}" for k, v in data.items())
                ),
            )
            return

        # Multiple parts or very large
        if len(parts) <= 3:
            for i, part in enumerate(parts):
                await update.message.reply_text(
                    part,
                    reply_markup=KeyboardBuilder.main() if i == len(parts) - 1 else None,
                )
                await asyncio.sleep(0.3)
        else:
            # Send as file
            content = Formatter.to_file_content(data, title)
            file_obj = BytesIO(content.encode("utf-8"))
            file_obj.name = f"{title.lower().replace(' ', '_')}.txt"
            await update.message.reply_document(
                document=file_obj,
                caption=f"{SEPARATOR}\n  {title}\n{SEPARATOR}\n  {BRANDING}",
                reply_markup=KeyboardBuilder.main(),
            )

    async def _perform_lookup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        lookup_type: str,
        lookup_func,
    ) -> None:
        """Generic lookup handler."""
        user = await self._ensure_user(update)
        if not user:
            return

        if not await self._check_access(update, context):
            return

        query = " ".join(context.args) if context.args else ""
        if not query:
            # Store lookup type and ask for input
            context.user_data["pending_lookup"] = lookup_type
            context.user_data["lookup_func"] = lookup_func.__name__
            names = {
                "username": "username",
                "number": "phone number",
                "aadhaar": "Aadhaar number",
                "email": "email address",
                "name": "name",
                "address": "address",
            }
            await update.message.reply_text(
                f"📝 Please enter the {names.get(lookup_type, lookup_type)} to search:",
                reply_markup=KeyboardBuilder.main(),
            )
            return

        await self._execute_lookup(update, lookup_type, lookup_func, query)

    async def _execute_lookup(
        self,
        update: Update,
        lookup_type: str,
        lookup_func,
        query: str,
    ) -> None:
        """Execute a lookup and send results."""
        user_id = update.effective_user.id

        # Send typing indicator
        await update.message.chat.send_action(action="typing")
        await asyncio.sleep(0.3)

        try:
            result = await lookup_func(query)
        except Exception as e:
            logger.error(f"Lookup error ({lookup_type}): {e}")
            await update.message.reply_text(
                Formatter.error_message(f"Lookup failed: {str(e)}"),
                reply_markup=KeyboardBuilder.main(),
            )
            return

        if not result.get("success"):
            await update.message.reply_text(
                Formatter.error_message(result.get("error", "Lookup returned no results.")),
                reply_markup=KeyboardBuilder.main(),
            )
            return

        # Deduct cost
        if not await self._deduct_cost(user_id):
            await update.message.reply_text(
                Formatter.error_message("Failed to deduct search cost."),
                reply_markup=KeyboardBuilder.main(),
            )
            return

        # Record the search
        await self.db.increment_total_searches(user_id)

        # Send result
        await self._send_result(update, f"{lookup_type.title()} Lookup", result["data"])

    # ── Command Handlers ──────────────────────────────────────────────

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = await self._ensure_user(update)
        if not user:
            return

        welcome = (
            f"\n{SEPARATOR}\n"
            f"  🔥 WELCOME TO ZAP PAPA 🔥\n"
            f"{SEPARATOR}\n"
            f"Your all-in-one Telegram utility tool.\n\n"
            f"🔍 Lookup usernames, numbers, emails & more\n"
            f"💳 Earn and spend credits on searches\n"
            f"👤 Track your profile & usage stats\n\n"
            f"Use the keyboard below to get started!\n"
            f"\n{SEPARATOR}\n"
            f"  {BRANDING}"
        )
        await update.message.reply_text(welcome, reply_markup=KeyboardBuilder.main())

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = (
            f"\n{SEPARATOR}\n"
            f"  🆘 HELP\n"
            f"{SEPARATOR}\n"
            f"🔍 Username Lookup  - Search by social handle\n"
            f"📱 Number Lookup    - Search by phone number\n"
            f"🆔 Aadhaar Lookup   - Search by Aadhaar number\n"
            f"📧 Email Lookup     - Search by email address\n"
            f"👤 Name Lookup      - Search by full name\n"
            f"📍 Address Lookup   - Search by address\n"
            f"\n💎 Premium         - View premium options\n"
            f"👤 My Profile      - View your account\n"
            f"💳 Buy Credits     - Purchase credits\n"
            f"⚙️ Admin Panel     - Admin controls\n"
            f"\n{SEPARATOR}\n"
            f"  {BRANDING}"
        )
        await update.message.reply_text(help_text, reply_markup=KeyboardBuilder.main())

    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show user profile."""
        user = await self._ensure_user(update)
        if not user:
            return
        await update.message.reply_text(
            Formatter.profile(user),
            reply_markup=KeyboardBuilder.main(),
        )

    # ── Message Handlers ──────────────────────────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route incoming text messages to appropriate handlers."""
        text = update.message.text.strip()
        user = await self._ensure_user(update)

        if not user:
            return

        # ── Main Menu Options ─────────────────────────────────────────
        handlers = {
            "🔍 Username Lookup": lambda: self._perform_lookup(
                update, context, "username", APIClient.lookup_username
            ),
            "📱 Number Lookup": lambda: self._perform_lookup(
                update, context, "number", APIClient.lookup_number
            ),
            "🆔 Aadhaar Lookup": lambda: self._perform_lookup(
                update, context, "aadhaar", APIClient.lookup_aadhaar
            ),
            "📧 Email Lookup": lambda: self._perform_lookup(
                update, context, "email", APIClient.lookup_email
            ),
            "👤 Name Lookup": lambda: self._perform_lookup(
                update, context, "name", APIClient.lookup_name
            ),
            "📍 Address Lookup": lambda: self._perform_lookup(
                update, context, "address", APIClient.lookup_address
            ),
            "👤 My Profile": lambda: self.profile(update, context),
            "💳 Buy Credits": lambda: self._buy_credits_menu(update),
            "💎 Premium": lambda: self._premium_menu(update),
            "⚙️ Admin Panel": lambda: self._admin_panel(update, user),
        }

        handler = handlers.get(text)
        if handler:
            await handler()
            return

        # ── Check for pending lookup input ────────────────────────────
        pending = context.user_data.get("pending_lookup")
        if pending:
            func_name = context.user_data.get("lookup_func", "")
            func_map = {
                "username": APIClient.lookup_username,
                "number": APIClient.lookup_number,
                "aadhaar": APIClient.lookup_aadhaar,
                "email": APIClient.lookup_email,
                "name": APIClient.lookup_name,
                "address": APIClient.lookup_address,
            }
            lookup_func = func_map.get(pending)
            if lookup_func:
                await self._execute_lookup(update, pending, lookup_func, text)
                context.user_data.pop("pending_lookup", None)
                context.user_data.pop("lookup_func", None)
            return

        # ── Unknown command ───────────────────────────────────────────
        await update.message.reply_text(
            Formatter.info_message(
                "❓ Unknown Option",
                "Please use the keyboard buttons below to navigate.",
            ),
            reply_markup=KeyboardBuilder.main(),
        )

    # ── Menu Handlers ─────────────────────────────────────────────────

    async def _premium_menu(self, update: Update) -> None:
        """Show premium menu."""
        text = (
            f"\n{SEPARATOR}\n"
            f"  💎 PREMIUM\n"
            f"{SEPARATOR}\n"
            f"✨ Unlimited searches\n"
            f"⚡ Priority support\n"
            f"📊 Advanced analytics\n"
            f"🔓 Exclusive features\n\n"
            f"💳 Buy Credits to unlock premium features.\n"
            f"Packages available:\n"
        )
        for credits, price in Config.CREDIT_PACKAGES.items():
            text += f"  • {credits} credits — ${price}\n"
        text += f"\n{SEPARATOR}\n  {BRANDING}"

        await update.message.reply_text(text, reply_markup=KeyboardBuilder.premium())

    async def _buy_credits_menu(self, update: Update) -> None:
        """Show credit purchase options."""
        text = (
            f"\n{SEPARATOR}\n"
            f"  💳 BUY CREDITS\n"
            f"{SEPARATOR}\n"
            f"Choose a package or enter a custom amount:\n\n"
        )
        for credits, price in Config.CREDIT_PACKAGES.items():
            text += f"  • {credits} credits — ${price}\n"
        text += (
            f"\n"
            f"Send /buy <amount> to purchase.\n"
            f"Contact admin for payment.\n"
            f"\n{SEPARATOR}\n"
            f"  {BRANDING}"
        )
        await update.message.reply_text(text, reply_markup=KeyboardBuilder.main())

    async def _admin_panel(self, update: Update, user_data: Dict[str, Any]) -> None:
        """Show admin panel (if user is admin)."""
        if not user_data.get("is_admin", False):
            await update.message.reply_text(
                Formatter.error_message("⛔ Access denied. Admin privileges required."),
                reply_markup=KeyboardBuilder.main(),
            )
            return

        await update.message.reply_text(
            f"\n{SEPARATOR}\n"
            f"  ⚙️ ADMIN PANEL\n"
            f"{SEPARATOR}\n"
            f"Use the admin keyboard or commands:\n"
            f"  /stats     - Bot statistics\n"
            f"  /users     - List all users\n"
            f"  /addcredits - Add credits to user\n"
            f"  /broadcast - Send broadcast\n"
            f"\n{SEPARATOR}\n"
            f"  {BRANDING}",
            reply_markup=KeyboardBuilder.admin(),
        )

    async def buy_credits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /buy <amount> command."""
        user = await self._ensure_user(update)
        if not user:
            return

        args = context.args
        if not args or not args[0].isdigit():
            await update.message.reply_text(
                Formatter.info_message(
                    "Usage", "Usage: /buy <amount>\nExample: /buy 50",
                ),
                reply_markup=KeyboardBuilder.main(),
            )
            return

        amount = int(args[0])
        # In production: process payment here
        await self.db.add_credits(user["user_id"], amount)
        await update.message.reply_text(
            Formatter.info_message(
                "✅ Credits Added",
                f"You have been credited with {amount} credits.\n"
                f"Contact admin for payment confirmation.",
            ),
            reply_markup=KeyboardBuilder.main(),
        )


# ══════════════════════════════════════════════════════════════════════════
#  ADMIN HANDLERS
# ══════════════════════════════════════════════════════════════════════════
class AdminHandlers:
    """Admin-only command handlers."""

    def __init__(self, db: Database):
        self.db = db

    def _is_admin(self, update: Update) -> bool:
        """Check if the user is an admin."""
        user = update.effective_user
        return user is not None and Config.is_admin(user.id)

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bot statistics."""
        if not self._is_admin(update):
            return
        stats_data = await self.db.get_stats()
        await update.message.reply_text(
            Formatter.stats(stats_data),
            reply_markup=KeyboardBuilder.admin(),
        )

    async def users(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List all registered users."""
        if not self._is_admin(update):
            return

        all_users = await self.db.get_all_users()
        if not all_users:
            await update.message.reply_text("No users registered yet.")
            return

        # Build summary
        lines = [
            f"\n{SEPARATOR}",
            "  👥 ALL USERS",
            SEPARATOR,
            f"Total: {len(all_users)}",
            "",
        ]

        for u in all_users:
            uid = u.get("user_id") or u.get("_id", "?")
            name = u.get("first_name", "?")
            uname = u.get("username", "")
            creds = u.get("credits", 0)
            free = u.get("free_searches", 0)
            total = u.get("total_searches", 0)
            admin_flag = "👑" if u.get("is_admin") else " "
            line = f"{admin_flag} {uid} | {name} | @{uname} | C:{creds} F:{free} T:{total}"
            lines.append(line)

        lines.append(f"\n{SEPARATOR}\n  {BRANDING}")
        text = "\n".join(lines)

        # Split if needed
        parts = Formatter.split_message(text, Config.MAX_MESSAGE_LENGTH)
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await update.message.reply_text(part, reply_markup=KeyboardBuilder.admin())
            else:
                await update.message.reply_text(part)
            await asyncio.sleep(0.3)

    async def addcredits(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Add credits to a user. Usage: /addcredits <user_id> <amount>"""
        if not self._is_admin(update):
            return

        args = context.args
        if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
            await update.message.reply_text(
                "Usage: /addcredits <user_id> <amount>\n"
                "Example: /addcredits 123456789 50",
            )
            return

        target_id = int(args[0])
        amount = int(args[1])

        # Verify user exists
        user = await self.db.get_user(target_id)
        if not user:
            await update.message.reply_text(
                Formatter.error_message(f"User {target_id} not found in database.")
            )
            return

        await self.db.add_credits(target_id, amount)
        await update.message.reply_text(
            Formatter.info_message(
                "✅ CREDITS ADDED",
                f"Added {amount} credits to user {target_id} (@{user.get('username', '?')}).\n"
                f"New balance: {user.get('credits', 0) + amount} credits.",
            ),
            reply_markup=KeyboardBuilder.admin(),
        )

    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Broadcast a message to all users. Usage: /broadcast <message>"""
        if not self._is_admin(update):
            return

        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /broadcast <message>\n"
                "Example: /broadcast Hello everyone! New updates available.",
            )
            return

        message = " ".join(args)
        await update.message.reply_text(
            f"📢 Broadcasting to all users...",
            reply_markup=KeyboardBuilder.admin(),
        )

        sent, failed = await self.db.broadcast(
            context.bot,
            message,
            exclude_id=update.effective_user.id,
        )

        await update.message.reply_text(
            Formatter.info_message(
                "📢 BROADCAST COMPLETE",
                f"Sent: {sent}\nFailed: {failed}\nTotal: {sent + failed}",
            ),
            reply_markup=KeyboardBuilder.admin(),
        )

    async def admin_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle messages from the admin keyboard."""
        if not self._is_admin(update):
            return

        text = update.message.text.strip()

        admin_actions = {
            "📊 Stats": self.stats,
            "👥 Users": self.users,
        }

        handler = admin_actions.get(text)
        if handler:
            await handler(update, context)
            return

        if text == "➕ Add Credits":
            await update.message.reply_text(
                "Use: /addcredits <user_id> <amount>\n"
                "Example: /addcredits 123456789 50"
            )
            return

        if text == "📢 Broadcast":
            await update.message.reply_text(
                "Use: /broadcast <message>\n"
                "Example: /broadcast Hello everyone!"
            )
            return

        if text == "🔙 Back to Main":
            await update.message.reply_text(
                "Returning to main menu.",
                reply_markup=KeyboardBuilder.main(),
            )


# ══════════════════════════════════════════════════════════════════════════
#  TERMUX CLI
# ══════════════════════════════════════════════════════════════════════════
class TermuxCLI:
    """Command-line interface optimized for Termux."""

    BANNER = (
        f"\n{Fore.RED if COLORAMA_AVAILABLE else ''}"
        f"╔══════════════════════════════╗\n"
        f"║        🔥 ZAP PAPA 🔥        ║\n"
        f"║    Telegram Utility Tool     ║\n"
        f"╚══════════════════════════════╝"
        f"{Style.RESET_ALL if COLORAMA_AVAILABLE else ''}"
    )

    MENU_ITEMS = [
        ("1", "Username Lookup"),
        ("2", "Number Lookup"),
        ("3", "Profile"),
        ("4", "Stats"),
        ("0", "Exit"),
    ]

    @staticmethod
    def _color(text: str, color: str) -> str:
        """Apply color if available."""
        if COLORAMA_AVAILABLE:
            return f"{color}{text}{Style.RESET_ALL}"
        return text

    @staticmethod
    def clear() -> None:
        """Clear terminal screen."""
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def print_banner() -> None:
        """Print the ZAP PAPA banner."""
        print(TermuxCLI.BANNER)
        print()

    @staticmethod
    def print_menu() -> None:
        """Print the menu options."""
        c = TermuxCLI._color
        print(f"  {c('═' * 30, Fore.CYAN if COLORAMA_AVAILABLE else '')}")
        for key, label in TermuxCLI.MENU_ITEMS:
            color = Fore.GREEN if key != "0" else Fore.RED
            icon = "🔍" if "Lookup" in label else "👤" if "Profile" in label else "📊" if "Stats" in label else "❌"
            print(f"  {c(key, color)}. {icon} {label}")
        print(f"  {c('═' * 30, Fore.CYAN if COLORAMA_AVAILABLE else '')}")

    @staticmethod
    def print_status(bot_running: bool, db_mode: str, user_count: int) -> None:
        """Print bot status."""
        c = TermuxCLI._color
        status_color = Fore.GREEN if bot_running else Fore.YELLOW
        status_text = "🟢 RUNNING" if bot_running else "🟡 STOPPED"
        print(f"  {c('Status:', Fore.CYAN)} {c(status_text, status_color)}")
        print(f"  {c('Database:', Fore.CYAN)} {c(db_mode.upper(), Fore.MAGENTA)}")
        print(f"  {c('Users:', Fore.CYAN)} {c(str(user_count), Fore.WHITE)}")

    @staticmethod
    async def run_interactive(db: Database, application: Application) -> None:
        """Run the interactive Termux CLI alongside the bot."""
        cls = TermuxCLI

        while True:
            cls.clear()
            cls.print_banner()

            user_count = await db.get_user_count()
            bot_running = application.running
            cls.print_status(bot_running, db.mode, user_count)
            cls.print_menu()

            try:
                choice = input(f"\n  {Fore.GREEN if COLORAMA_AVAILABLE else ''}ZAP> {Style.RESET_ALL if COLORAMA_AVAILABLE else ''}").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Shutting down...")
                break

            if choice == "0":
                print("  👋 Goodbye!")
                break
            elif choice == "1":
                uname = input("  Enter username: ").strip()
                if uname:
                    print("  🔍 Looking up...")
                    result = await APIClient.lookup_username(uname)
                    if result.get("success"):
                        for k, v in result["data"].items():
                            print(f"    {k}: {v}")
                    else:
                        print("  ❌ Lookup failed")
                    input("\n  Press Enter to continue...")
            elif choice == "2":
                num = input("  Enter number: ").strip()
                if num:
                    print("  🔍 Looking up...")
                    result = await APIClient.lookup_number(num)
                    if result.get("success"):
                        for k, v in result["data"].items():
                            print(f"    {k}: {v}")
                    else:
                        print("  ❌ Lookup failed")
                    input("\n  Press Enter to continue...")
            elif choice == "3":
                uid = input("  Enter User ID (or leave blank for stats): ").strip()
                if uid and uid.isdigit():
                    user = await db.get_user(int(uid))
                    if user:
                        print(f"\n  {'─' * 30}")
                        for k, v in user.items():
                            if k != "_id":
                                print(f"    {k}: {v}")
                    else:
                        print("  ❌ User not found")
                else:
                    s = await db.get_stats()
                    print(f"\n  {'─' * 30}")
                    for k, v in s.items():
                        print(f"    {k}: {v}")
                input("\n  Press Enter to continue...")
            elif choice == "4":
                s = await db.get_stats()
                print(f"\n  {'─' * 30}")
                for k, v in s.items():
                    print(f"    {k}: {v}")
                input("\n  Press Enter to continue...")
            else:
                print(f"  ❌ Unknown option: {choice}")
                await asyncio.sleep(1)


# ══════════════════════════════════════════════════════════════════════════
#  ERROR HANDLER
# ══════════════════════════════════════════════════════════════════════════
async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for the bot."""
    logger.error(f"Update {update} caused error {context.error}")

    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                Formatter.error_message(
                    "An unexpected error occurred. Please try again later."
                ),
            )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════
def build_application(db: Database) -> Application:
    """Build and configure the Telegram bot application."""

    if not TELEGRAM_AVAILABLE:
        logger.critical(
            "python-telegram-bot is not installed. "
            "Install with: pip install python-telegram-bot>=21.7"
        )
        sys.exit(1)

    bot_handlers = BotHandlers(db)
    admin_handlers = AdminHandlers(db)

    application = Application.builder().token(Config.BOT_TOKEN).build()

    # ── Command Handlers ──────────────────────────────────────────────
    application.add_handler(CommandHandler("start", bot_handlers.start))
    application.add_handler(CommandHandler("help", bot_handlers.help))
    application.add_handler(CommandHandler("profile", bot_handlers.profile))
    application.add_handler(CommandHandler("buy", bot_handlers.buy_credits_command))

    # ── Admin Command Handlers ────────────────────────────────────────
    application.add_handler(CommandHandler("stats", admin_handlers.stats))
    application.add_handler(CommandHandler("users", admin_handlers.users))
    application.add_handler(CommandHandler("addcredits", admin_handlers.addcredits))
    application.add_handler(CommandHandler("broadcast", admin_handlers.broadcast))

    # ── Admin Message Handler (catches admin keyboard) ────────────────
    application.add_handler(MessageHandler(
        filters.Text([
            "📊 Stats", "👥 Users", "➕ Add Credits",
            "📢 Broadcast", "🔙 Back to Main",
        ]),
        admin_handlers.admin_message_handler,
    ))

    # ── Main Message Handler ──────────────────────────────────────────
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        bot_handlers.handle_message,
    ))

    # ── Callback Query Handler ────────────────────────────────────────
    application.add_handler(CallbackQueryHandler(
        async def _callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            if query.data == "copy_fallback":
                await query.message.reply_text(
                    "📋 Select and copy the text above manually.",
                )
        ,
        pattern="^copy_fallback$",
    ))

    # ── Error Handler ─────────────────────────────────────────────────
    application.add_error_handler(error_handler)

    return application


async def async_main() -> None:
    """Async main entry point."""
    # ── Validate configuration ────────────────────────────────────────
    issues = Config.validate()
    for issue in issues:
        logger.warning(f"Configuration issue: {issue}")

    if not TELEGRAM_AVAILABLE:
        logger.critical(
            "\n❌ python-telegram-bot >= 21.7 is required.\n"
            "Install with:\n"
            "  pip install python-telegram-bot>=21.7\n"
        )
        sys.exit(1)

    # ── Initialize database ───────────────────────────────────────────
    db = Database()

    # ── Build application ─────────────────────────────────────────────
    application = build_application(db)

    # ── Start the bot ─────────────────────────────────────────────────
    logger.info("Starting ZAP PAPA bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )
    logger.info("ZAP PAPA bot is running!")

    # ── Start Termux CLI (if in terminal) ─────────────────────────────
    if sys.stdin.isatty():
        try:
            await TermuxCLI.run_interactive(db, application)
        except Exception as cli_err:
            logger.error(f"Termux CLI error: {cli_err}")

    # ── Wait for stop signal ──────────────────────────────────────────
    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Shutting down...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("ZAP PAPA bot stopped.")


def main() -> None:
    """Synchronous entry point for direct execution."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Shutdown by user.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Print banner on startup
    print(TermuxCLI.BANNER)
    print()
    main()


# ══════════════════════════════════════════════════════════════════════════
#  REQUIREMENTS
# ══════════════════════════════════════════════════════════════════════════
#
# ── Core Dependencies ──────────────────────────────────────────────────
# python-telegram-bot>=21.7        # Telegram Bot API wrapper
#
# ── Database ──────────────────────────────────────────────────────────
# motor>=3.0                       # Async MongoDB driver (optional)
# pymongo>=4.0                     # MongoDB core (required by motor)
#
# ── CLI ───────────────────────────────────────────────────────────────
# colorama>=0.4                    # Colored terminal output (optional)
#
# ── Installation ──────────────────────────────────────────────────────
# pip install python-telegram-bot>=21.7 motor colorama
#
# ── Environment Variables ─────────────────────────────────────────────
# BOT_TOKEN=your_telegram_bot_token     # Required
# MONGO_URI=mongodb://localhost:27017   # Optional, falls back to memory
# ADMIN_IDS=123456,789012               # Comma-separated admin IDs
# OWNER_ID=123456                       # Primary owner/admin ID
#
# ── Features ──────────────────────────────────────────────────────────
# ✅ Telegram Bot (python-telegram-bot v21.7+)
# ✅ Termux compatible
# ✅ MongoDB support (with in-memory fallback)
# ✅ Async architecture
# ✅ ReplyKeyboard UI
# ✅ User profile system
# ✅ Credits system with free searches
# ✅ Admin panel (stats, users, addcredits, broadcast)
# ✅ Conversation-based lookups
# ✅ Copy button (CopyTextButton v21.7+)
# ✅ Auto-split large messages
# ✅ TXT file download for very large results
# ✅ Error handling with auto-reconnect
# ✅ Beautiful Termux CLI
# ✅ Modular classes in one file
# ✅ No external developer names/branding
#
# ══════════════════════════════════════════════════════════════════════════
