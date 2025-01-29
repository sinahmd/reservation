import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
import datetime
from persiantools.jdatetime import JalaliDate

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)



reserved_times = {}  # Keeps track of reserved times
pending_reservations = {}  # Holds pending reservation requests for admin approval
def init_db():
    conn = sqlite3.connect('reservations.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS available_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            UNIQUE(date, time)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reserved_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Database helper functions
def add_available_time(date, time):
    conn = sqlite3.connect('reservations.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO available_times (date, time) VALUES (?, ?)', (date, time))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Ignore duplicate entries
    conn.close()

def delete_available_time(date, time):
    conn = sqlite3.connect('reservations.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM available_times WHERE date = ? AND time = ?', (date, time))
    conn.commit()
    conn.close()

def get_available_times(date=None):
    conn = sqlite3.connect('reservations.db')
    cursor = conn.cursor()
    if date:
        cursor.execute('SELECT time FROM available_times WHERE date = ?', (date,))
    else:
        cursor.execute('SELECT DISTINCT date FROM available_times')
    results = cursor.fetchall()
    conn.close()
    return [row[0] for row in results]

# Admin check
def admin_check(user_id):
    return str(user_id) == "288129387"  # Replace with your admin's ID

# Function to convert Gregorian date to Solar (Jalali) date
def gregorian_to_solar(gregorian_date):
    g_date = datetime.datetime.strptime(gregorian_date, "%Y-%m-%d")
    solar_date = JalaliDate(g_date.year, g_date.month, g_date.day)
    return solar_date.strftime("%Y/%m/%d")

# Start command - Show available dates as buttons (Solar dates for user)
async def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    message = f"سلام, {user.first_name}! برای رزرو وقت، تاریخ مورد نظر را انتخاب کنید.\n"
    today = datetime.date.today()
    keyboard = []

    for i in range(7):
        date = today + datetime.timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        solar_date = gregorian_to_solar(date_str)
        weekday = date.strftime("%A")
        weekday_fa = {
            "Monday": "دوشنبه", "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه",
            "Thursday": "پنج‌شنبه", "Friday": "جمعه", "Saturday": "شنبه", "Sunday": "یکشنبه"
        }.get(weekday, weekday)
        keyboard.append([InlineKeyboardButton(f"{solar_date} {weekday_fa}", callback_data=f"date_{date_str}")])

    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

# Handle date selection
async def select_date(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    selected_date = query.data.split('_')[1]
    await query.answer()

    available_times = get_available_times(selected_date)
    if available_times:
        keyboard = [
            [InlineKeyboardButton(time, callback_data=f"time_{selected_date}_{time}")]
            for time in available_times
        ]
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="back_to_days")])
        await query.edit_message_text(f"زمانی را انتخاب کنید {gregorian_to_solar(selected_date)}:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text(f"زمانی موجود نیست برای {gregorian_to_solar(selected_date)}.")

async def add_time(update: Update, context: CallbackContext):
    user = update.message.from_user
    if not admin_check(user.id):
        await update.message.reply_text("شما اجازه دسترسی به این فرمان را ندارید.")
        return

    try:
        date, time = context.args
        add_available_time(date, time)
        await update.message.reply_text(f"زمان {time} برای تاریخ {date} با موفقیت اضافه شد.")
    except ValueError:
        await update.message.reply_text("لطفاً تاریخ و زمان را به صورت صحیح وارد کنید. مثال: /add_time 2025-01-30 10:00")

async def delete_time(update: Update, context: CallbackContext):
    user = update.message.from_user
    if not admin_check(user.id):
        await update.message.reply_text("شما اجازه دسترسی به این فرمان را ندارید.")
        return

    try:
        date, time = context.args
        delete_available_time(date, time)
        await update.message.reply_text(f"زمان {time} برای تاریخ {date} با موفقیت حذف شد.")
    except ValueError:
        await update.message.reply_text("لطفاً تاریخ و زمان را به صورت صحیح وارد کنید. مثال: /delete_time 2025-01-30 10:00")

# Handle back button to return to days menu
async def back_to_days(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    today = datetime.date.today()
    keyboard = []

    for i in range(7):
        date = today + datetime.timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        solar_date = gregorian_to_solar(date_str)
        weekday = date.strftime("%A")

        weekday_fa = {
            "Monday": "دوشنبه", "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه",
            "Thursday": "پنج‌شنبه", "Friday": "جمعه", "Saturday": "شنبه", "Sunday": "یکشنبه"
        }.get(weekday, weekday)

        keyboard.append([InlineKeyboardButton(f"{solar_date} {weekday_fa}", callback_data=f"date_{date_str}")])

    await query.edit_message_text(
        "تاریخ‌های در دسترس را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Handle time selection
# Handle time selection and reservation
async def reserve_time(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    selected_data = query.data.split('_')
    selected_date = selected_data[1]  # Gregorian date
    selected_time = selected_data[2]

    # Get user details
    user_id = query.from_user.id
    first_name = query.from_user.first_name
    username = query.from_user.username or "بدون نام کاربری"

    conn = sqlite3.connect('reservations.db')
    cursor = conn.cursor()

    # Check if the selected time is available in the database
    cursor.execute(
        "SELECT id FROM available_times WHERE date = ? AND time = ?",
        (selected_date, selected_time)
    )
    available_time = cursor.fetchone()

    if available_time:
        # Store the pending reservation
        if selected_date not in pending_reservations:
            pending_reservations[selected_date] = []

        pending_reservations[selected_date].append({
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "time": selected_time
        })

        # Notify the admin about the new reservation
        admin_id = "288129387"  # Replace with your admin's ID
        keyboard = [
            [InlineKeyboardButton("پذیرش", callback_data=f"approve_{selected_date}_{selected_time}_{user_id}"),
             InlineKeyboardButton("رد", callback_data=f"reject_{selected_date}_{selected_time}_{user_id}")]
        ]
        await context.bot.send_message(
            admin_id,
            f"درخواست رزرو جدید:\n"
            f"👤 نام: {first_name}\n"
            f"🌐 نام کاربری: @{username if username != 'بدون نام کاربری' else 'N/A'}\n"
            f"📅 تاریخ: {gregorian_to_solar(selected_date)}\n"
            f"⏰ زمان: {selected_time}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Confirm to the user that their request is pending approval
        await query.edit_message_text(
            f"درخواست شما برای {gregorian_to_solar(selected_date)} در {selected_time} ثبت شد و در حال بررسی است."
        )
    else:
        await query.edit_message_text(f"متاسفم, {selected_time} در {gregorian_to_solar(selected_date)} موجود نیست.")

    conn.close()


# Admin approves a reservation
async def approve_reservation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    selected_data = query.data.split('_')
    selected_date = selected_data[1]
    selected_time = selected_data[2]
    user_id = int(selected_data[3])  # Extract user_id

    # Find the reservation in pending requests
    reservation = None
    if selected_date in pending_reservations:
        for res in pending_reservations[selected_date]:
            if res['time'] == selected_time and res['user_id'] == user_id:
                reservation = res
                break

    if reservation:
        first_name = reservation["first_name"]

        conn = sqlite3.connect('reservations.db')
        cursor = conn.cursor()

        try:
            # Approve reservation by adding it to reserved_times table
            cursor.execute(
                '''
                INSERT INTO reserved_times (user_id, username, first_name, date, time)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (user_id, reservation["username"], first_name, selected_date, selected_time)
            )
            conn.commit()

            # Remove from available_times and pending_reservations
            cursor.execute("DELETE FROM available_times WHERE date = ? AND time = ?", (selected_date, selected_time))
            conn.commit()

            pending_reservations[selected_date] = [
                res for res in pending_reservations[selected_date] if res['time'] != selected_time
            ]

            # Notify the user of approval
            await context.bot.send_message(
                user_id,
                f"سلام {first_name}!\n"
                f"رزرو شما برای {gregorian_to_solar(selected_date)} در {selected_time} تایید شد. به موقع تشریف بیارید!"
            )

            # Notify the admin of the approval
            await query.edit_message_text(f"رزرو {gregorian_to_solar(selected_date)} در {selected_time} برای {first_name} تایید شد.")
        except sqlite3.IntegrityError:
            await query.edit_message_text(f"خطا: رزرو از قبل در سیستم وجود دارد.")

        conn.close()
    else:
        await query.edit_message_text(f"درخواستی پیدا نشد {gregorian_to_solar(selected_date)} در {selected_time}.")

# Admin rejects a reservation
async def reject_reservation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    selected_data = query.data.split('_')
    selected_date = selected_data[1]
    selected_time = selected_data[2]
    user_id = int(selected_data[3])  # Extract user_id

    # Find the reservation in pending requests
    reservation = None
    if selected_date in pending_reservations:
        for res in pending_reservations[selected_date]:
            if res['time'] == selected_time and res['user_id'] == user_id:
                reservation = res
                break

    if reservation:
        first_name = reservation["first_name"]

        # Remove from pending requests
        pending_reservations[selected_date] = [
            res for res in pending_reservations[selected_date] if res['time'] != selected_time
        ]

        # Notify the user of rejection
        await context.bot.send_message(
            user_id,
            f"سلام {first_name}!\n"
            f"متاسفیم، رزرو شما برای {gregorian_to_solar(selected_date)} در {selected_time} رد شده است."
        )

        # Notify the admin of the rejection
        await query.edit_message_text(f"رزرو {gregorian_to_solar(selected_date)} در {selected_time} برای {first_name} رد شد.")
    else:
        await query.edit_message_text(f"درخواستی پیدا نشد {gregorian_to_solar(selected_date)} در {selected_time}.")

# Main function to set up the bot
def main() -> None:
    init_db()
    application = Application.builder().token("7421192528:AAHcvBaqdD_5S6-EQGlZ-TZrG_4WjOP6IWQ").build()

    # Add handlers for different commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(select_date, pattern='^date_'))
    application.add_handler(CallbackQueryHandler(back_to_days, pattern='^back_to_days$'))
    application.add_handler(CallbackQueryHandler(reserve_time, pattern='^time_'))
    application.add_handler(CallbackQueryHandler(approve_reservation, pattern='^approve_'))
    application.add_handler(CallbackQueryHandler(reject_reservation, pattern='^reject_'))
    application.add_handler(CommandHandler("add_time", add_time))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()