import logging
import app
import db
from config import config
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from typing import Callable


def setting():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


def get_bot(token: str, proxy_url: str | None):
    builder = ApplicationBuilder().token(token)
    if proxy_url:
        builder = builder.proxy(proxy_url)
    return builder.build()


def get_arg(text: str):
    index = text.find(' ')
    return text[index + 1] if index != -1 else ''


def read_simple(func: Callable[[int, int, str | None], str | None]):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=func(update.effective_chat.id,
                                                 update.effective_message.message_id,
                                                 get_arg(update.effective_message.text)))

    return handler


def read_reply(func: Callable[[int, int, int, str | None], str | None]):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=func(update.effective_chat.id,
                                                 update.effective_message.message_id,
                                                 update.effective_message.reply_to_message.message_id,
                                                 get_arg(update.effective_message.text)))

    return handler


async def reminder_checker(context: ContextTypes.DEFAULT_TYPE):
    for chat_id, message_id, message in app.update_reminders():
        await context.bot.send_message(chat_id=chat_id, reply_to_message_id=message_id, text=message)


if __name__ == "__main__":
    setting()
    db.setup()
    bot = get_bot(config["telegram"]["token"], config.get("network", dict()).get("proxy"))
    bot.add_handler(CommandHandler('start', read_simple(app.start)))
    bot.add_handler(CommandHandler('shut_up', read_simple(app.shut_up)))
    bot.add_handler(CommandHandler('reminder_monthly', read_simple(app.reminder_monthly)))
    bot.add_handler(CommandHandler('cancel', read_reply(app.cancel)))
    bot.job_queue.run_repeating(reminder_checker, 30)
    bot.run_polling()
