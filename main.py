# main.py
import os
import logging
import random
from collections import OrderedDict
from typing import Dict

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 채팅방별 세션: chat_id -> {"players": OrderedDict[user_id->name], "items": []}
SESSIONS: Dict[int, Dict] = {}

HELP_TEXT = (
    "🪜 사다리타기 봇 사용법\n"
    "/newgame - 새 게임 시작(현재 채팅)\n"
    "/join [별명] - 참가 등록 (별명 생략 시 텔레그램 이름 사용)\n"
    "/leave - 참가 취소\n"
    "/setitems 항목1,항목2,... - 결과 항목 설정(쉼표 구분)\n"
    "/list - 참가자/항목 현황 보기\n"
    "/startgame - 사다리 결과 공개(참가자 수와 항목 수가 같아야 함)\n"
    "/reset - 게임 데이터 초기화\n"
)

def session(chat_id: int) -> Dict:
    if chat_id not in SESSIONS:
        SESSIONS[chat_id] = {"players": OrderedDict(), "items": []}
    return SESSIONS[chat_id]

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("안녕하세요! 사다리타기 봇입니다.\n" + HELP_TEXT)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

async def cmd_newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    SESSIONS[cid] = {"players": OrderedDict(), "items": []}
    await update.message.reply_text("🧩 새 게임 시작! /join 으로 참가하고, /setitems 로 항목을 등록하세요.")

async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    user = update.effective_user
    s = session(cid)

    alias = " ".join(context.args).strip() if context.args else None
    name = alias if alias else (user.first_name or user.username or str(user.id))

    s["players"][user.id] = name
    await update.message.reply_text(f"✅ 참가: {name} (총 {len(s['players'])}명)")

async def cmd_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    user = update.effective_user
    s = session(cid)

    if user.id in s["players"]:
        removed = s["players"].pop(user.id)
        await update.message.reply_text(f"❎ 취소: {removed} (이제 {len(s['players'])}명)")
    else:
        await update.message.reply_text("등록된 참가자가 아닙니다.")

async def cmd_setitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    s = session(cid)
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("사용법: /setitems 항목1,항목2,항목3")
        return
    items = [x.strip() for x in text.split(",") if x.strip()]
    if not items:
        await update.message.reply_text("유효한 항목이 없습니다.")
        return
    s["items"] = items
    await update.message.reply_text("📦 항목 설정:\n- " + "\n- ".join(items))

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    s = session(cid)
    players = list(s["players"].values())
    items = s["items"]
    msg = (
        f"📋 참가자({len(players)}): " + (", ".join(players) if players else "없음") + "\n" +
        f"📦 항목({len(items)}): " + (", ".join(items) if items else "없음")
    )
    await update.message.reply_text(msg)

async def cmd_startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    s = session(cid)
    players = list(s["players"].values())
    items = s["items"][:]

    if not players:
        await update.message.reply_text("참가자가 없습니다. /join 먼저.")
        return
    if not items:
        await update.message.reply_text("항목이 없습니다. /setitems 먼저.")
        return
    if len(players) != len(items):
        await update.message.reply_text(f"인원({len(players)})과 항목({len(items)}) 수가 같아야 합니다.")
        return

    random.shuffle(items)
    pairs = list(zip(players, items))
    lines = ["🪜 사다리 결과"]
    for p, it in pairs:
        lines.append(f"• {p} → {it}")
    await update.message.reply_text("\n".Join(lines))

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    SESSIONS[cid] = {"players": OrderedDict(), "items": []}
    await update.message.reply_text("♻️ 초기화 완료. /newgame 으로 다시 시작하세요.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("환경변수 BOT_TOKEN 이 없습니다. (Render 환경변수에 넣어주세요)")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("newgame", cmd_newgame))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CommandHandler("leave", cmd_leave))
    app.add_handler(CommandHandler("setitems", cmd_setitems))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("startgame", cmd_startgame))
    app.add_handler(CommandHandler("reset", cmd_reset))

    logger.info("🚀 Bot starting (long polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
