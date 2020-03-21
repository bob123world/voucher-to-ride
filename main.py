import logging
import os
import json

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

class VTR():
    def __init__(self, players):
        updater = Updater("TOKEN", use_context=True)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", self.start))
        dp.add_handler(CommandHandler("add", self.add))
        dp.add_handler(CommandHandler("deck", self.start))
        dp.add_handler(CommandHandler("help", self.start))

        # log all errors
        dp.add_error_handler(self.error)

        # Start the Bot
        updater.start_polling()

        updater.idle()

    def start(self, update, context):
        update.message.reply_text('Hello, \n\nWelcome to Bobbie\'s Venitian Hotel & Casino\nCome and play with us!\n\nWe are playing Ticket To Ride tonight...\nUse /add to add yourself to the game')

    def add(self, update, context):
        update.message.reply_text('Hello, \n\nWelcome to Bobbie\'s Venitian Hotel & Casino\nCome and play with us!\n\nWe are playing Ticket To Ride tonight...\nUse /add to add yourself to the game')


    def check_game(self, context):
        pass

    def error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def json_load(self):
        try:
            with open('data.json', 'r') as f:
                self.data = json.load(f)
        except Exception as e:
            logger.error(e)
    
    def json_save(self):
        try:
            with open('personal.json', 'w') as json_file:
                json.dumps(self.data, json_file, sort_keys=True, indent=4)
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    game = VTR(4)
