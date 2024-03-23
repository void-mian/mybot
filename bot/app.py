from db import *
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser
from zoneinfo import ZoneInfo
import pickle


def start(chat_id: int, message_id: int, text: str | None):
    chat, created = Chat.get_or_create(chat_id=str(chat_id))
    if not chat.enabled:
        chat.enabled = True
        chat.save()
        logging.info(f"[{chat_id}] chat enabled")
        return "我们已经是好友啦，一起来聊天吧😅！"
    else:
        return "直接聊天吧"


def shut_up(chat_id: int, message_id: int, text: str | None):
    chat, created = Chat.get_or_create(chat_id=str(chat_id))
    if chat.enabled:
        chat.enabled = False
        chat.save()
        logging.info(f"[{chat_id}] chat disabled")
        return "I can't breathe🤐!"
    else:
        return None


class ReminderInfo:
    def __init__(self, start_dt: datetime, step: relativedelta, count: int):
        self.start_dt = start_dt
        self.step = step
        self.count = count


def update_reminders():
    now = datetime.now(ZoneInfo("UTC"))
    logging.debug("update reminders:")
    reply = list()
    for reminder in Reminder.select():
        chat_id = int(reminder.chat.chat_id)
        message_id = int(reminder.message_id)
        info: ReminderInfo = pickle.loads(reminder.info)
        next_dt = info.start_dt + info.count * info.step
        logging.debug(f"now {now},start_dt {info.start_dt} , next_dt {next_dt}")
        if now >= next_dt:
            while now >= next_dt:
                info.count += 1
                next_dt = info.start_dt + info.count * info.step
            Reminder.update(info=pickle.dumps(info)).where(
                (Reminder.chat == str(chat_id)) & (Reminder.message_id == str(message_id))
            ).execute()
            reply.append((chat_id, message_id, " 到点了!"))
    return reply


def reminder_monthly(chat_id: int, message_id: int, dt: str | None) -> str | None:
    chat, created = Chat.get_or_create(chat_id=str(chat_id))
    if not chat.enabled:
        return None

    try:
        if dt:
            dtime = dateutil.parser.parse(timestr=dt, fuzzy=True)
            if dtime is None or dtime.tzinfo is None:
                return "日期格式错误"
        else:
            return "日期格式错误"
    except (dateutil.parser.ParserError, OverflowError) as error:
        return "日期格式错误"

    cancel(chat_id=chat_id, message_id=None, reply_to_message_id=message_id)

    Reminder.create(
        chat=str(chat_id), message_id=str(message_id),
        info=pickle.dumps(ReminderInfo(dtime, relativedelta(months=1), 0))
    )
    dtime_str = dtime.strftime('%Y-%m-%d %H:%M:%S %Z')
    logging.info(f"[{chat_id},{message_id}] reminder added: {dtime_str}")

    if cancel == "取消成功":
        return f"替换成功 {dtime_str}"
    else:
        return f"添加成功 {dtime_str}"


def cancel(chat_id: int, message_id: int | None, reply_to_message_id: int, text: str | None = None) -> str | None:
    chat, created = Chat.get_or_create(chat_id=str(chat_id))
    if not chat.enabled:
        return None

    deleted = Reminder.delete().where(
        (Reminder.chat == str(chat_id)) & (Reminder.message_id == str(reply_to_message_id))
    ).execute()
    if deleted > 0:
        return "取消成功"
    else:
        return "没有任务"
