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
        builder = builder.get_updates_proxy(proxy_url).proxy(proxy_url)
    return builder.build()


class Response(app.BaseResponse):
    def __init__(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        self.chat_id = chat_id
        self.context = context
        self.tasks = list()

    def send(self, text: str):
        self.tasks.append(self.context.bot.send_message(chat_id=self.chat_id, text=text))

    def send_reply(self, chat_id: int, message_id: int, text: str):
        self.tasks.append(self.context.bot.send_message(chat_id=chat_id,
                                                        reply_to_message_id=message_id,
                                                        text=text))


def make_handler(func: Callable[[app.BaseRequest, app.BaseResponse], None]):
    def get_request(update: Update):
        reply_to_message = update.effective_message.reply_to_message
        return app.BaseRequest(chat_id=update.effective_chat.id,
                               message_id=update.effective_message.message_id,
                               reply_to_message_id=None if reply_to_message is None else reply_to_message.message_id,
                               text=update.effective_message.text)

    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        request = get_request(update)
        response = Response(update.effective_chat.id, context)
        func(request, response)
        for task in response.tasks:
            await task

    return handler


def make_schedule(func: Callable[[app.BaseResponse], None]):
    async def callback(context: ContextTypes.DEFAULT_TYPE):
        response = Response((2 ** 64) - 1, context)
        func(response)
        for task in response.tasks:
            await task

    return callback


if __name__ == "__main__":
    setting()
    db.setup()
    bot = get_bot(config["telegram"]["token"], config.get("network", dict()).get("proxy"))
    bot.add_handler(CommandHandler('start', make_handler(app.start)))
    bot.add_handler(CommandHandler('shut_up', make_handler(app.shut_up)))
    bot.add_handler(CommandHandler('reminder_monthly', make_handler(app.reminder_monthly)))
    bot.add_handler(CommandHandler('cancel', make_handler(app.cancel)))
    bot.job_queue.run_repeating(make_schedule(app.check_reminders), 30)
    bot.run_polling()
