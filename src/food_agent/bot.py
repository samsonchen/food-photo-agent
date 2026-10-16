"""Discord 這一端：收訊息、過濾、加反應、回覆（docs/architecture.md 第 3、4 節）。"""

from __future__ import annotations

import asyncio
import logging
import time

import discord

from food_agent import config, replies
from food_agent.config import Settings
from food_agent.ledger import Ledger
from food_agent.logs import job_tag, tag_for
from food_agent.models import Job
from food_agent.pipeline import Outcome, process_job
from food_agent.queueing import Admit, JobQueue
from food_agent.schema import clean_text

log = logging.getLogger("food_agent.bot")

REACT_WAITING = "⏳"
REACT_OK = "✅"
REACT_FAIL = "❌"

CAPTION_LOG_CHARS = 50  # log 裡最多留備註的前幾個字

# 附件的 content type → 副檔名。不在清單裡的圖片格式（例如 HEIC）會回覆「格式不支援」
_EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class DiscordPhoto:
    """把 discord.Attachment 包成 pipeline 看得懂的 PhotoSource。"""

    def __init__(self, attachment: discord.Attachment, ext: str):
        self._attachment = attachment
        self.ext = ext
        self.size = attachment.size

    async def read(self) -> bytes:
        return await self._attachment.read()


def _content_type(attachment: discord.Attachment) -> str:
    return (attachment.content_type or "").split(";")[0].strip().lower()


class FoodBot(discord.Client):
    def __init__(self, settings: Settings, ledger: Ledger):
        intents = discord.Intents.default()
        intents.message_content = True  # 要在 Developer Portal 打開 Message Content Intent，否則收不到附件
        super().__init__(intents=intents)
        self.settings = settings
        self.ledger = ledger
        self.queue = JobQueue()
        self._worker: asyncio.Task | None = None

    async def setup_hook(self) -> None:
        self._worker = asyncio.create_task(self.queue.run(self._handle_job))

    async def on_ready(self) -> None:
        log.info("已連線：%s，只處理頻道 %s", self.user, self.settings.channel_id)
        channel = self.get_channel(self.settings.channel_id)
        if channel is None:
            log.warning("看不到 CHANNEL_ID 指定的頻道。請確認 ID 正確，且 bot 在那個頻道有 View Channels 權限。")
            return
        perms = channel.permissions_for(channel.guild.me)
        needed = {
            "view_channel": "View Channels",
            "send_messages": "Send Messages",
            "read_message_history": "Read Message History",
            "add_reactions": "Add Reactions",
        }
        missing = [label for attr, label in needed.items() if not getattr(perms, attr)]
        if missing:
            log.warning("bot 在這個頻道缺少權限：%s", "、".join(missing))
        else:
            log.info("等待頻道 #%s 的照片…（Ctrl+C 結束）", channel.name)

    async def on_message(self, message: discord.Message) -> None:
        # 只聽指定的那一個頻道；bot 自己和其他 bot 的訊息不理
        if message.channel.id != self.settings.channel_id or message.author.bot:
            return
        images = [a for a in message.attachments if _content_type(a).startswith("image/")]
        if not images:  # 純文字、影片、PDF……完全不理
            log.debug("略過沒有圖片附件的訊息 %s", message.id)
            return

        job_tag.set(tag_for(message.id))  # 之後這則訊息的每一筆 log 都會帶著這個編號
        caption = message.content or ""
        log.info(
            "收到：上傳者 %s（%s），%d 張圖片，備註 %d 字：%r",
            message.author.display_name,
            message.author.id,
            len(images),
            len(caption),
            clean_text(caption, CAPTION_LOG_CHARS),
        )

        if any(_content_type(a) not in _EXT_BY_TYPE for a in images):
            types = sorted({_content_type(a) for a in images if _content_type(a) not in _EXT_BY_TYPE})
            log.warning("拒絕：圖片格式不支援（%s）", "、".join(types))
            await self._reject(message, replies.FAIL_FORMAT)
            return
        if any(a.size > config.MAX_FILE_BYTES for a in images):
            biggest = max(a.size for a in images)
            log.warning("拒絕：檔案太大（%.1f MB，上限 %d MB）", biggest / 1024 / 1024, config.MAX_FILE_BYTES // 1024 // 1024)
            await self._reject(message, replies.FAIL_TOO_BIG)
            return

        truncated = len(images) > config.MAX_PHOTOS_PER_MESSAGE
        if truncated:
            log.info("超過一則 %d 張的上限，只處理前 %d 張", config.MAX_PHOTOS_PER_MESSAGE, config.MAX_PHOTOS_PER_MESSAGE)
        images = images[: config.MAX_PHOTOS_PER_MESSAGE]
        job = Job(
            sources=[DiscordPhoto(a, _EXT_BY_TYPE[_content_type(a)]) for a in images],
            caption=caption,
            uploader_name=message.author.display_name,
            uploader_id=message.author.id,
            when=message.created_at.astimezone(),
            truncated=truncated,
            ref=message,
            message_id=message.id,
            received_at=time.monotonic(),
        )
        result = self.queue.submit(job)
        if result is Admit.QUEUE_FULL:
            log.warning("拒絕：排隊已滿（等待中 %d 則）", self.queue.waiting)
            await self._reject(message, replies.REJECT_QUEUE_FULL)
        elif result is Admit.USER_LIMIT:
            log.warning("拒絕：這個人已經有 %d 則在處理中", config.PER_USER_MAX)
            await self._reject(message, replies.REJECT_USER_LIMIT)
        else:
            log.info("已排隊：處理中 %d 則，等待中 %d 則（含這一則）", self.queue.running, self.queue.waiting)
            await self._react(message, REACT_WAITING)

    async def _handle_job(self, job: Job) -> None:
        message: discord.Message = job.ref
        token = job_tag.set(tag_for(job.message_id))
        started = time.monotonic()
        try:
            log.info("開始處理（在佇列裡等了 %.1f 秒）", started - job.received_at)
            try:
                outcome = await process_job(job, self.settings, self.ledger)
            except Exception:
                log.exception("process_job 出錯")
                outcome = Outcome(False, replies.FAIL_ANALYSIS)
            await self._finish(message, outcome)
            now = time.monotonic()
            log.info(
                "%s：處理 %.1f 秒，從收到算起共 %.1f 秒",
                "完成" if outcome.ok else "失敗",
                now - started,
                now - job.received_at,
            )
        finally:
            job_tag.reset(token)

    async def _finish(self, message: discord.Message, outcome: Outcome) -> None:
        try:
            await message.remove_reaction(REACT_WAITING, self.user)
        except discord.HTTPException as exc:
            log.warning("拿掉 %s 反應失敗：%s", REACT_WAITING, exc)
        await self._react(message, REACT_OK if outcome.ok else REACT_FAIL)
        await self._reply(message, outcome.text)

    async def _reject(self, message: discord.Message, text: str) -> None:
        await self._react(message, REACT_FAIL)
        await self._reply(message, text)

    async def _react(self, message: discord.Message, emoji: str) -> None:
        try:
            await message.add_reaction(emoji)
            log.info("已加上 %s 反應", emoji)
        except discord.HTTPException as exc:
            log.warning("加反應 %s 失敗：%s", emoji, exc)

    async def _reply(self, message: discord.Message, text: str) -> None:
        """用「回覆該則訊息」的方式回在頻道裡（不用私訊），只允許通知上傳者本人。"""
        try:
            await message.reply(
                text,
                mention_author=True,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=[message.author], replied_user=True
                ),
            )
            log.info("已回覆（%d 字）", len(text))
        except discord.HTTPException as exc:
            log.error("回覆失敗：%s", exc)
