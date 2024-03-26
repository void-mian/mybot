from db import *
import abc
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser
from zoneinfo import ZoneInfo
import pickle
import re
import requests
from typing import Optional


class BaseRequest:
    def __init__(self, chat_id: int, message_id: int | None, reply_to_message_id: int | None, text: str | None, reply_to_message_text: Optional[str] = None):
        self.chat_id = chat_id
        self.message_id = message_id
        self.reply_to_message_id = reply_to_message_id
        self.text = text
        self.reply_to_message_text = reply_to_message_text


class BaseResponse(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def send(self, text: str) -> None:
        pass

    @abc.abstractmethod
    def send_reply(self, chat_id: int, message_id: int, text: str) -> None:
        pass

    @abc.abstractmethod
    def send_markdown_reply(self, chat_id: int, message_id: int, text: str) -> None:
        pass


def has_enabled(chat_id: int):
    chat, created = Chat.get_or_create(chat_id=str(chat_id))
    return chat.enabled


def start(req: BaseRequest, res: BaseResponse):
    chat_id = req.chat_id
    chat, created = Chat.get_or_create(chat_id=str(chat_id))
    if not chat.enabled:
        chat.enabled = True
        chat.save()
        logging.info(f"[{chat_id}] chat enabled")
        res.send("我们已经是好友啦，一起来聊天吧😅！")
    else:
        res.send("直接聊天吧")


def shut_up(req: BaseRequest, res: BaseResponse):
    chat_id = req.chat_id
    chat, created = Chat.get_or_create(chat_id=str(chat_id))
    if chat.enabled:
        chat.enabled = False
        chat.save()
        logging.info(f"[{chat_id}] chat disabled")
        res.send("I can't breathe🤐!")


class ReminderInfo:
    def __init__(self, start_dt: datetime, step: relativedelta, count: int):
        self.start_dt = start_dt
        self.step = step
        self.count = count


def check_reminders(res: BaseResponse):
    now = datetime.now(ZoneInfo("UTC"))
    logging.debug("update reminders:")
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
            res.send_reply(chat_id, message_id, " 到点了!")


def reminder_monthly(req: BaseRequest, res: BaseResponse):
    chat_id = req.chat_id
    message_id = req.message_id
    dt = req.text
    if not has_enabled(chat_id):
        return

    try:
        if dt:
            dtime = dateutil.parser.parse(timestr=dt, fuzzy=True)
            if dtime is None or dtime.tzinfo is None:
                return res.send("日期格式错误")
        else:
            return res.send("日期格式错误")
    except (dateutil.parser.ParserError, OverflowError) as error:
        return res.send("日期格式错误")

    canceled = cancel0(chat_id=chat_id, message_id=message_id)

    Reminder.create(
        chat=str(chat_id), message_id=str(message_id),
        info=pickle.dumps(ReminderInfo(dtime, relativedelta(months=1), 0))
    )
    dtime_str = dtime.strftime('%Y-%m-%d %H:%M:%S %Z')
    logging.info(f"[{chat_id},{message_id}] reminder added: {dtime_str}")

    if canceled == "取消成功":
        res.send_reply(chat_id, message_id, f"替换成功 {dtime_str}")
    else:
        res.send_reply(chat_id, message_id, f"添加成功 {dtime_str}")


def cancel0(chat_id: int, message_id: int) -> str:
    deleted = Reminder.delete().where(
        (Reminder.chat == str(chat_id)) & (Reminder.message_id == str(message_id))
    ).execute()
    if deleted > 0:
        return "取消成功"
    else:
        return "没有任务"


def cancel(req: BaseRequest, res: BaseResponse):
    chat_id = req.chat_id
    reply_to_message_id = req.reply_to_message_id
    if not has_enabled(chat_id):
        return
    res.send(cancel0(chat_id, reply_to_message_id))


def nbnhhsh0(msg: str) -> list[str]:
    try:
        results: list[dict[str, list[str]]]
        results = requests.post('https://lab.magiconch.com/api/nbnhhsh/guess', {'text': msg}).json()
        return results[0]['trans']
    except (KeyError, IndexError) as error:
        return []


def nbnhhsh(req: BaseRequest, res: BaseResponse):
    chat_id = req.chat_id
    message_id = req.message_id
    message = req.text
    if not has_enabled(chat_id):
        return

    # slice for ignoring the command it self
    bhhsh_list = re.findall(r'[A-Za-z0-9]+', message)[1:]
    
    if len(bhhsh_list) == 0:
        message = req.reply_to_message_text
        logging.info(f"no bhhsh found, refering to replying message {message}")
        bhhsh_list = re.findall(r'[A-Za-z0-9]+', message)
    
    if len(bhhsh_list) > 0:
        res_message = ""
        for bhhsh in bhhsh_list:
            logging.info(f"bhhsh: searching for {bhhsh}")
            readable_messages = (nbnhhsh0(bhhsh))
            if len(readable_messages) > 0:
                messages = '/'.join(map('`{0}`'.format, readable_messages))
                res_message += f'对于 {bhhsh}, ta 可能是想说:{messages}\n'
            else:
                res_message += f"对于 {bhhsh}…… 啊咧, 我好像也不明白 ta 想说什么\~\n"
        res.send_markdown_reply(chat_id, message_id, res_message)
        
    else:
        res.send("不管原文还是回复文本都没发现缩写欸，不知道你是哪里看不懂呢？")
