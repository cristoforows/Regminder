import logging
import datetime
import pytz
import telegram
from telegram.ext import Updater, CommandHandler, JobQueue
from apscheduler.schedulers.background import BackgroundScheduler
import boto3

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Load bot token and AWS credentials from config.py
from config import TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME

# Create a new Telegram bot using the provided token
bot = telegram.Bot(token=TOKEN)

# Set up AWS SNS client
sns = boto3.client('sns',
                   aws_access_key_id=AWS_ACCESS_KEY_ID,
                   aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                   region_name=AWS_REGION_NAME)

# Define the start function, triggered by the /start command
def start(update, context):
    message = "Welcome to the reminder bot! To set a reminder, use one of the following commands:\n\n"
    message += "/hourly <reminder text> - Set a reminder to be sent every hour.\n"
    message += "/daily <reminder text> - Set a reminder to be sent every day.\n"
    message += "/weekly <reminder text> - Set a reminder to be sent every week.\n"
    message += "/monthly <reminder text> - Set a reminder to be sent every month.\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

# Define the hourly reminder function
def set_hourly_reminder(update, context):
    reminder_text = " ".join(context.args)
    job = context.job_queue.run_repeating(send_reminder,
                                           interval=3600,
                                           first=0,
                                           context=update.effective_chat.id,
                                           name=reminder_text)
    context.chat_data['jobs'].append(job)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Hourly reminder set to: " + reminder_text)

# Define the daily reminder function
def set_daily_reminder(update, context):
    reminder_text = " ".join(context.args)
    job = context.job_queue.run_daily(send_reminder,
                                       time=datetime.time(hour=8, minute=0),
                                       days=(0, 1, 2, 3, 4, 5, 6),
                                       context=update.effective_chat.id,
                                       name=reminder_text)
    context.chat_data['jobs'].append(job)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Daily reminder set to: " + reminder_text)

# Define the weekly reminder function
def set_weekly_reminder(update, context):
    reminder_text = " ".join(context.args)
    job = context.job_queue.run_weekly(send_reminder,
                                        day_of_week=3,
                                        time=datetime.time(hour=10, minute=0),
                                        context=update.effective_chat.id,
                                        name=reminder_text)
    context.chat_data['jobs'].append(job)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Weekly reminder set to: " + reminder_text)

# Define the monthly reminder function
def set_monthly_reminder(update, context):
    reminder_text = " ".join(context.args)
    job = context.job_queue.run_monthly(send_reminder,
                                         day=1,
                                         time=datetime.time(hour=9, minute=0
                                        ),
                                        context=update.effective_chat.id,
                                        name=reminder_text)
    context.chat_data['jobs'].append(job)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Monthly reminder set to: " + reminder_text)

# Define the function to send reminders
def send_reminder(context):
    job = context.job
    reminder_text = job.name
    chat_id = job.context
    now = datetime.datetime.now(pytz.timezone('Asia/Jakarta'))
    message = "Reminder:\n\n" + reminder_text + "\n\nSent at: " + str(now)
    context.bot.send_message(chat_id=chat_id, text=message)
    sns.publish(TopicArn='<YOUR_TOPIC_ARN>', Message=message)

# Define the error handler function
def error(update, context):
    logging.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    # Create a new job queue
    job_queue = JobQueue()

    # Set up the scheduler to run in the background
    scheduler = BackgroundScheduler()
    scheduler.start()

    # Set up the updater with the bot token and job queue
    updater = Updater(token=TOKEN, use_context=True, job_queue=job_queue)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Set up the start command handler
    dp.add_handler(CommandHandler("start", start))

    # Set up the hourly reminder command handler
    dp.add_handler(CommandHandler("hourly", set_hourly_reminder,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))

    # Set up the daily reminder command handler
    dp.add_handler(CommandHandler("daily", set_daily_reminder,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))

    # Set up the weekly reminder command handler
    dp.add_handler(CommandHandler("weekly", set_weekly_reminder,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))

    # Set up the monthly reminder command handler
    dp.add_handler(CommandHandler("monthly", set_monthly_reminder,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))

    # Set up the error handler
    dp.add_error_handler(error)

    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()
