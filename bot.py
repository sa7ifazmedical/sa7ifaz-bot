import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# -- إعدادات المدير --
ADMIN_USER_ID = 123456789  # غير هذا للآيدي تاعك في تيليغرام

# -- قاعدة بيانات الملفات (json) --
DB_FILE = "files_db.json"

# -- تحميل قاعدة البيانات أو انشائها إذا مش موجودة --
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # قاعدة مبدئية: تصنيفات مع قوائم ملفات (file_id واسم الملف)
        return {
            "أساسيات التمريض": [],
            "استعجالات طبية": [],
            "أدوية": [],
            "تشريح ووظائف الأعضاء": [],
            "علم الأمراض": [],
            "تقنيات الحقن والعناية": [],
            "نماذج امتحانات": [],
            "فيديوهات تعليمية": [],
            "أخرى": []
        }

# -- حفظ قاعدة البيانات --
def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# -- تحميل القاعدة عند بداية التشغيل --
files_db = load_db()

# -- الأمر /start --
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "مرحبًا بكم في *sa7ifazBOT* 🤖💬\n\n"
        "🌟 خدمات البوت:\n"
        "إرسال الدروس 📚 والمعلومات الطبية 💡\n"
        "مشاركة فيديوهات تعليمية حصرية 🎥\n"
        "إجابة على استفسارات في المجال الشبه طبي 🩺💉\n"
        "دعم دائم للطلاب والمختصين ✨\n\n"
        "اختر التصنيف للاطلاع على الملفات:"
    )
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"category|{cat}")]
        for cat in files_db.keys()
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# -- عرض ملفات التصنيف --
async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, category = query.data.split("|", 1)
    files = files_db.get(category, [])
    if not files:
        await query.message.reply_text(f"🚫 لا توجد ملفات في تصنيف *{category}* حاليا.", parse_mode="Markdown")
        return
    keyboard = [
        [InlineKeyboardButton(f["name"], callback_data=f"file|{category}|{f['file_id']}")]
        for f in files
    ]
    await query.message.reply_text(f"📂 ملفات تصنيف *{category}*:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# -- إرسال الملف المختار --
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, category, file_id = query.data.split("|", 2)
    # البحث عن اسم الملف للعرض
    file_name = next((f["name"] for f in files_db.get(category, []) if f["file_id"] == file_id), "ملف")
    await query.message.reply_document(document=file_id, caption=f"📎 الملف: {file_name}")

# -- الأمر /search نص البحث --
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("✏️ استعمل: /search كلمة_البحث\nمثال: /search قلب")
        return
    keyword = " ".join(context.args).strip().lower()
    results = []
    for cat, files in files_db.items():
        for f in files:
            if keyword in f["name"].lower():
                results.append(f"📂 *{cat}* - 📎 {f['name']}")
    if not results:
        await update.message.reply_text(f"🚫 ما لقيتش نتائج على '{keyword}'.", parse_mode="Markdown")
    else:
        await update.message.reply_text("نتائج البحث:\n" + "\n".join(results), parse_mode="Markdown")

# -- رفع الملفات للمدير فقط (يبدأ بوضع اسم وتصنيف) --
ASK_NAME, ASK_CATEGORY, ASK_FILE = range(3)

async def add_file_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 ماعندكش صلاحية باش ترفع ملفات.")
        return ConversationHandler.END
    await update.message.reply_text("📤 اكتب اسم الملف اللي تحب تضيفه:")
    return ASK_NAME

async def add_file_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_file_name"] = update.message.text.strip()
    categories = list(files_db.keys())
    keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in categories]
    await update.message.reply_text("📂 اختار التصنيف المناسب للملف:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_CATEGORY

async def add_file_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["new_file_category"] = query.data
    await query.answer()
    await query.message.reply_text("📎 أرسل لي ملف PDF الآن (ملف واحد فقط).")
    return ASK_FILE

async def add_file_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("🚫 من فضلك أرسل ملف PDF فقط.")
        return ASK_FILE
    file_id = update.message.document.file_id
    name = context.user_data["new_file_name"]
    category = context.user_data["new_file_category"]
    # أضف الملف للقاعدة
    files_db.setdefault(category, []).append({"name": name, "file_id": file_id})
    save_db(files_db)
    await update.message.reply_text(f"✅ تم إضافة الملف '{name}' في تصنيف '{category}'.")
    # إشعار عام (اختياري)
    # تقدر هنا ترسل رسالة لمجموعة أو شخص آخر على تيليغرام (مثلاً المدير)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

# -- تشغيل البوت --
if __name__ == "__main__":
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(category_handler, pattern=r"^category\|"))
    app.add_handler(CallbackQueryHandler(file_handler, pattern=r"^file\|"))
    app.add_handler(CommandHandler("search", search_command))

    add_file_conv = ConversationHandler(
        entry_points=[CommandHandler("addfile", add_file_start)],
        states={
            ASK_NAME: [CommandHandler("cancel", cancel), MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_name)],
            ASK_CATEGORY: [CallbackQueryHandler(add_file_category)],
            ASK_FILE: [MessageHandler(filters.Document.PDF, add_file_receive)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(add_file_conv)

    print("sa7ifazBOT running...")
    app.run_polling()
