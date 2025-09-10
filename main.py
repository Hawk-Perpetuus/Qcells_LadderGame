import os
import sys
import time
import logging
import random
import traceback
from collections import OrderedDict
from typing import Dict

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ─────────────────────────────────────────────────────────
# 로깅 설정 (Render 로그에 잘 찍히도록)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ladder-bot")

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

# ─────────────────────────────────────────────────────────
# 세션 헬퍼
def session(chat_id: int) -> Dict:
    if chat_id not in SESSIONS:
        SESSIONS[chat_id] = {"players": OrderedDict(), "items": []}
    return SESSIONS[chat_id]

# ─────────────────────────────────────────────────────────
# 커맨드 핸들러들
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
    await update.message.reply_text("\n".join(lines))

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    SESSIONS[cid] = {"players": OrderedDict(), "items": []}
    await update.message.reply_text("♻️ 초기화 완료. /newgame 으로 다시 시작하세요.")

# ─────────────────────────────────────────────────────────
def build_app(token: str) -> Application:
    return Application.builder().token(token).build()

def main():
    print(">>> entered main()")
    token = os.getenv("BOT_TOKEN")
    if not token:
        # Render가 즉시 죽는 원인 1순위: 토큰 미전달
        raise RuntimeError("BOT_TOKEN is missing! (Render → Environment Variables 확인)")

    # (웹훅이 과거에 걸려 있었다면 롱폴링과 충돌 가능성이 있어요.
    #  토큰을 새로 발급했거나, deleteWebhook를 호출했다면 문제없습니다.)
    logger.info("Starting ladder-bot with long polling")
    app = build_app(token)

    # 핸들러 등록
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("newgame", cmd_newgame))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CommandHandler("leave", cmd_leave))
    app.add_handler(CommandHandler("setitems", cmd_setitems))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("startgame", cmd_startgame))
    app.add_handler(CommandHandler("reset", cmd_reset))

    print(">>> run_polling() ...")
    app.run_polling()  # 여기서 계속 대기 상태가 되는 게 정상

# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        print(">>> booting ladder-bot")
        main()
    except Exception as e:
        # 왜 죽는지 Render 로그에서 바로 보이게 전체 예외를 출력
        print(">>> CRASHED:", e)
        traceback.print_exc()
        sys.stdout.flush()
        time.sleep(5)
        raise
