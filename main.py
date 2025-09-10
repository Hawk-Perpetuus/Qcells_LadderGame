import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"안녕, {update.effective_user.first_name}!")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN 환경변수가 없습니다.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("hello", hello))
    app.run_polling()

if __name__ == "__main__":
    main()
