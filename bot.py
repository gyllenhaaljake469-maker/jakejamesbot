"""
bot.py — @jakejamesbot
Telegram bot: Fiverr gig image generator + free utility tools.

Run locally:
    export BOT_TOKEN=xxxx
    python bot.py

Deploy: Railway (see README.md)
"""

import os
import io
import logging
import urllib.parse
import urllib.request

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from gig_image import (
    generate_gig_image,
    generate_variations,
    CATEGORY_STYLES,
    STYLE_LAYOUTS,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Conversation states
CATEGORY, STYLE, TITLE, COLOR = range(4)


# ---------------------------------------------------------------------------
# /start and /help
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Welcome to *JakeJamesBot*!\n\n"
        "I can create Fiverr-ready gig images in seconds, plus a few handy "
        "free tools.\n\n"
        "🎨 /gigimage — Create a Fiverr gig image\n"
        "🔤 /count — Word & character counter\n"
        "🔗 /shorten — Shorten a URL\n"
        "❓ /help — Show this message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ---------------------------------------------------------------------------
# /gigimage conversation flow
# ---------------------------------------------------------------------------

def _category_keyboard():
    buttons = [
        InlineKeyboardButton(cat.capitalize(), callback_data=f"cat_{cat}")
        for cat in CATEGORY_STYLES.keys()
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def _style_keyboard():
    buttons = [
        InlineKeyboardButton(s.capitalize(), callback_data=f"style_{s}")
        for s in STYLE_LAYOUTS
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


async def gigimage_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Let's build your gig image! 🎨\n\nFirst — pick a category:",
        reply_markup=_category_keyboard(),
    )
    return CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.replace("cat_", "")
    context.user_data["category"] = category
    await query.edit_message_text(
        f"Category: *{category.capitalize()}* ✅\n\nNow pick a visual style:",
        parse_mode="Markdown",
        reply_markup=_style_keyboard(),
    )
    return STYLE


async def style_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    style = query.data.replace("style_", "")
    context.user_data["style"] = style
    await query.edit_message_text(
        f"Style: *{style.capitalize()}* ✅\n\n"
        "Now send me your gig title.\n"
        "_Example: \"I will design a modern minimalist logo\"_",
        parse_mode="Markdown",
    )
    return TITLE


async def title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    if len(title) < 5:
        await update.message.reply_text("That title's a bit short — try again:")
        return TITLE
    context.user_data["title"] = title
    await update.message.reply_text(
        "Got it! Want a custom accent color?\n\n"
        "Send a hex code like `#FF5733`, or type `skip` to use the default "
        "color for your category.",
        parse_mode="Markdown",
    )
    return COLOR


async def color_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    color_hex = None
    if text.lower() != "skip":
        if not (text.startswith("#") and len(text) == 7):
            await update.message.reply_text(
                "That doesn't look like a valid hex code (e.g. #FF5733). "
                "Try again, or type `skip`.",
                parse_mode="Markdown",
            )
            return COLOR
        color_hex = text

    context.user_data["color"] = color_hex
    await update.message.reply_text("Generating your gig images... 🎨⏳")
    await _send_variations(update, context)
    return ConversationHandler.END


async def _send_variations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    paths = generate_variations(
        data["title"], data["category"], data.get("color"), count=3
    )
    media = [InputMediaPhoto(open(p, "rb")) for p in paths]
    chat_id = update.effective_chat.id
    await context.bot.send_media_group(chat_id=chat_id, media=media)

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Regenerate", callback_data="regen")]]
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text="Here are 3 variations! Use /gigimage to start a new one, "
             "or tap below to regenerate with the same details.",
        reply_markup=keyboard,
    )


async def regenerate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not context.user_data.get("title"):
        await query.edit_message_text("Session expired — use /gigimage to start fresh.")
        return
    await query.edit_message_text("Regenerating... 🎨⏳")
    await _send_variations(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled. Use /gigimage to start again anytime.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Utility tools
# ---------------------------------------------------------------------------

async def count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/count your text here`", parse_mode="Markdown"
        )
        return
    text = " ".join(context.args)
    words = len(text.split())
    chars = len(text)
    chars_no_spaces = len(text.replace(" ", ""))
    await update.message.reply_text(
        f"📊 *Word Count*\n\nWords: {words}\nCharacters: {chars}\n"
        f"Characters (no spaces): {chars_no_spaces}",
        parse_mode="Markdown",
    )


async def shorten_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/shorten https://example.com/long-url`", parse_mode="Markdown"
        )
        return
    long_url = context.args[0]
    try:
        api = "https://tinyurl.com/api-create.php?url=" + urllib.parse.quote(long_url)
        with urllib.request.urlopen(api, timeout=10) as resp:
            short_url = resp.read().decode("utf-8")
        await update.message.reply_text(f"🔗 {short_url}")
    except Exception as e:
        logger.error(f"Shorten error: {e}")
        await update.message.reply_text(
            "Couldn't shorten that URL right now. Please try again later."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set. "
            "Set it locally or in your Railway project variables."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    gig_conv = ConversationHandler(
        entry_points=[CommandHandler("gigimage", gigimage_start)],
        states={
            CATEGORY: [CallbackQueryHandler(category_chosen, pattern="^cat_")],
            STYLE: [CallbackQueryHandler(style_chosen, pattern="^style_")],
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_received)],
            COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, color_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(gig_conv)
    app.add_handler(CallbackQueryHandler(regenerate, pattern="^regen$"))
    app.add_handler(CommandHandler("count", count_command))
    app.add_handler(CommandHandler("shorten", shorten_command))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
