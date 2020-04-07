import os
import json
import logging
import requests
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, PicklePersistence)

from DatabaseSqlite3 import DatabaseSqlite3

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

SELECTION, OPTIONS, CITY, ROUTE, MARKET, TICKET, STATION, RESTART = range(8)

option_keyboard = [["Get Market Card", "Build Route"],
                  ["Build Station", "Get New Tickets"],
                  ["Deck", "Market", "Overview", "Map"],
                  ["Routes", "City", "Your Routes", "Player"],
                  ["Longest Route", "Points", "Help"]]

class VTR_BOT():
    def __init__(self):
        config = {}
        try:
            config = json.load(open("config.json"))
        except:
            logger.critical("File Not found: config.json")
            exit()
        self.db = DatabaseSqlite3(config["database"]["url"])
        
        # Initialize Telegram bot
        pp = PicklePersistence(filename="bobbieventianbot")
        updater = Updater(config["telegram"]["token"], persistence= pp, use_context=True)
        dp = updater.dispatcher

        option_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states = {
                SELECTION: [MessageHandler(Filters.regex("^(yellow|black|red|green|blue)$"), self.add),],
                OPTIONS: [MessageHandler(Filters.regex("^(Get Market Card)$"), choose_market), MessageHandler(Filters.regex("^(Build Route)$"), choose_city),
                MessageHandler(Filters.regex("^(Build Station)$"), build_station), MessageHandler(Filters.regex("^(Get New Tickets)$"), get_new_tickets),
                MessageHandler(Filters.regex("^(Deck)$"), deck), MessageHandler(Filters.regex("^(Market)$"), market),
                MessageHandler(Filters.regex("^(Overview)$"), overview), MessageHandler(Filters.regex("^(Map)$"), send_map),
                MessageHandler(Filters.regex("^(Routes)$"), routes), MessageHandler(Filters.regex("^(City)$"), choose_city),
                MessageHandler(Filters.regex("^(Your Routes)$"), yroutes), MessageHandler(Filters.regex("^(Player)$"), choose_player),
                MessageHandler(Filters.regex("^(Longest Route)$"), lroute), MessageHandler(Filters.regex("^(Points)$"), points), MessageHandler(Filters.regex("^(Help)$"), help)],
                CITY: [MessageHandler(Filters.text, city),],
                MARKET: [MessageHandler(Filters.text, pick_market),],
            },
            fallbacks = [MessageHandler(Filters.regex("^Done$"), start)],
            name = "ticket_to_ride",
            persistent= True
        )

        dp.add_handler(option_handler)

    def add(self, update, context):
        """Add a player to the game"""
        choice = update.message.text.lower()
        reply_text = ""
        result = self.db.get_data_table("Player", ["name","color"], "color = " + choice)
        if len(result) > 0:
            reply_text = "Somebody else is already assigned to this color, please choose another one!"
            markup = ReplyKeyboardMarkup(available_colors, one_time_keyboard=True)
            update.message.reply_text(reply_text, reply_markup=markup)
        else:
            self.db.update_data_table("Player", {"color": choice}, "chat_id = " + str(update.message.chat_id))
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            reply_text += "You are assigned to player color: " + player["color"]
            update.message.reply_text(reply_text, reply_markup=markup)
            return OPTIONS 