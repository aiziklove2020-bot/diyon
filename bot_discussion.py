import logging
import asyncio
import random
import google.generativeai as genai
from datetime import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

from discussion_config import BOT_TOKEN, ADMIN_IDS, GROUP_ID, GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

USED_TOPICS = []

TOPICS_POOL = [
    "גבולות ותקשורת בעולם BDSM",
    "Safe Word - למה זה כל כך חשוב?",
    "ההבדל בין Dom ל-Sub",
    "Aftercare - מה קורה אחרי הסצנה?",
    "איך מתחילים לחקור BDSM בבטחה?",
    "SSC vs RACK - איזה פילוסופיה אתם מאמינים בה?",
    "Trust - איך בונים אמון בין שותפים?",
    "Collaring - מה המשמעות של קולר?",
    "Sub Drop ו-Dom Drop - איך מתמודדים?",
    "Soft Limits vs Hard Limits",
    "Online BDSM - האם זה עובד?",
    "Rope Bondage - אמנות או נשק?",
    "הסכמה - הבסיס של הכל",
    "Public Play - כן או לא?",
    "Switch - להיות גם Dom וגם Sub",
    "Punishment vs Funishment",
    "BDSM ובריאות נפשית",
    "קינקים נפוצים - מה אתם אוהבים?",
    "איך מוצאים שותף BDSM?",
    "Scene Planning - איך מתכננים סצנה?",
    "Power Exchange - מה זה אומר לכם?",
    "Humiliation vs Degradation",
    "Sadomasochism - כאב כעונג",
    "BDSM ויחסים רומנטיים",
    "Fetish - מה ההבדל בין פטיש לקינק?",
]

def generate_discussion_sync(topic=None):
    global USED_TOPICS
    if not topic:
        available = [t for t in TOPICS_POOL if t not in USED_TOPICS]
        if not available:
            USED_TOPICS = []
            available = TOPICS_POOL
        topic = random.choice(available)
        USED_TOPICS.append(topic)

    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = (
        "אתה מנחה קהילת BDSM בישראל. "
        "צור דיון יומי מעניין בעברית על הנושא: " + topic + "\n\n"
        "הפורמט חייב להיות בדיוק:\n"
        "🔥 נושא הדיון: [נושא]\n\n"
        "[2-3 משפטים על הנושא בעברית]\n\n"
        "💬 שאלה לקהילה: [שאלה פתוחה מעניינת]\n\n"
        "השתמש בשפה מכבדת ופתוחה. אל תוסיף מוסר."
    )
    response = model.generate_content(prompt)
    return response.text

async def send_daily_discussion(context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("Generating daily discussion with Gemini...")
        loop = asyncio.get_event_loop()
        discussion = await loop.run_in_executor(None, generate_discussion_sync)
        await context.bot.send_message(GROUP_ID, discussion)
        logger.info("Daily discussion sent!")
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, "✅ הדיון היומי נשלח לקבוצה!")
            except:
                pass
    except Exception as e:
        logger.error("Error: " + str(e))
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, "❌ שגיאה בשליחת הדיון: " + str(e))
            except:
                pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("👋 הבוט שולח דיון יומי לקהילה בשעה 20:00 🔥")
        return
    keyboard = [
        [InlineKeyboardButton("🔥 שלח דיון עכשיו", callback_data="send_now")],
        [InlineKeyboardButton("📋 נושאים אפשריים", callback_data="show_topics")],
    ]
    await update.message.reply_text(
        "🛠 פאנל אדמין - בוט דיונים יומיים\n\nדיון נשלח כל יום בשעה 20:00 אוטומטית 🤖",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return

    if query.data == "send_now":
        await query.edit_message_text("⏳ מייצר דיון עם AI...")
        try:
            loop = asyncio.get_event_loop()
            discussion = await loop.run_in_executor(None, generate_discussion_sync)
            await context.bot.send_message(GROUP_ID, discussion)
            await query.edit_message_text(
                "✅ הדיון נשלח לקבוצה!\n\n" + discussion[:200] + "...",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזור", callback_data="back")]])
            )
        except Exception as e:
            await query.edit_message_text("❌ שגיאה: " + str(e))

    elif query.data == "show_topics":
        topics_text = "\n".join(["• " + t for t in TOPICS_POOL[:12]])
        await query.edit_message_text(
            "📋 חלק מהנושאים:\n\n" + topics_text + "\n\n...ועוד שה-AI ייצר!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזור", callback_data="back")]])
        )

    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🔥 שלח דיון עכשיו", callback_data="send_now")],
            [InlineKeyboardButton("📋 נושאים אפשריים", callback_data="show_topics")],
        ]
        await query.edit_message_text(
            "🛠 פאנל אדמין - בוט דיונים יומיים",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.job_queue.run_daily(
        send_daily_discussion,
        time=time(hour=20, minute=0),
        name="daily_discussion"
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("בוט דיונים פועל! שולח כל יום בשעה 20:00")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
