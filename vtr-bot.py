import os
import json
import random
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
    def __init__(self, map_name):
        ### Get working directory
        self.path = os.path.dirname(os.path.realpath(__file__))

        ### Get configuration data
        config = {}
        try:
            config = json.load(open(os.path.join(self.path, "config.json")))
        except:
            logger.critical("File Not found: config.json")
            exit()

        ### Initialize database
        self.db = DatabaseSqlite3(config["database"]["url"])

        ### Initialize Game configuration
        # Check if all cards are present:
        cards = self.db.get_data_table("Card", self.db.card_columns, "id > 0")

        present = False
        train_cards = {}
        for train_card_config in os.listdir(os.path.join(self.path, "train_cards")):
            if map_name in train_card_config:
                try:
                    train_cards = json.load(open(os.path.join(self.path, "train_cards", train_card_config)))
                    present = True
                except Exception as e:
                    logger.error(e)

        if not present:
            logger.critical("No train_cards config file found for this map_name")
            exit()
        
        amount_cards = 0
        for color in train_cards:
            amount_cards += color["cards"]

        if len(cards) is not amount_cards:
            self.db.delete_table("Card")
            self.db.create_table("Card", self.db.card_columns)
            deck =  []
            for card in train_cards:
                for i in range(0,card["cards"]):
                    deck.append(card["color"])
            random.shuffle(deck)
            insert_data = []
            for card in deck:
                new_tuple = (card, 0)
                insert_data.append(new_tuple)

            self.db.insert_data_table("Card", [["color", "owner"]], insert_data)

        logger.info("Card Table OK")

        # Check if market cards are set
        market = self.db.get_data_table("Card", self.db.card_columns, "owner = 1")
        if len(market) is not 5:
            self.db.update_data_table("Card", {"owner":0}, "owner = 1")
            available_cards = self.db.get_data_table("Card", self.db.card_columns, "owner = 0")
            i = 0
            while i < 5:
                self.db.update_data_table("Card", {"owner":1}, "id = " + str(available_cards[i][0]))
                i += 1

        logger.info("Market OK")

        # Check if cities and routes are present:
        cities = self.db.get_data_table("City", self.db.city_columns, "id > 0")

        present = False
        map_data = {}
        for map_config in os.listdir(os.path.join(self.path, "maps")):
            if map_name in map_config:
                try:
                    map_data = json.load(open(os.path.join(self.path, "maps", map_config)))
                    present = True
                except Exception as e:
                    logger.error(e)

        if not present:
            logger.critical("No maps config file found for this map_name")
            exit()

        # Check if cities and connections cities are the same. 
        cities_check = map_data["cities"]
        check = []
        for route in map_data["connections"]:
            check.append(route["city1"])
            check.append(route["city2"])

        check = set(check)
        check = list(check)

        cities_check.sort()
        check.sort()
        if set(cities_check) == set(check):
            logger.info("Cities and cities in routes match")
        else:
            logger.critical("Cities and cities in routes don't match")
            exit()

        if len(cities) is not len(map_data["cities"]):
            self.db.delete_table("City")
            self.db.create_table("City", self.db.city_columns)
            insert_data = []
            for city in map_data["cities"]:
                insert_data.append((city, None))
            self.db.insert_data_table("City", [["name","station"]], insert_data)

        logger.info("City table OK")

        routes = self.db.get_data_table("Route", self.db.route_columns, "id > 0")
        if len(routes) is not len(map_data["connections"]):
            self.db.delete_table("Route")
            self.db.create_table("Route", self.db.route_columns)
            insert_data = []
            for route in map_data["connections"]:
                city1 = self.db.get_data_table("City", [["id"]], "name LIKE '" + str(route["city1"]) + "'")
                city2 = self.db.get_data_table("City", [["id"]], "name LIKE '" + str(route["city2"]) + "'")
                tunnel = 0
                if route["tunnel"]:
                    tunnel = 1
                insert_data.append((city1[0][0], city2[0][0], route["color"], route["distance"], route["locomotives"], tunnel, 0))
            self.db.insert_data_table("Route", [["city1","city2","color","distance","locomotives","tunnel","owner"]], insert_data)

        logger.info("Route table OK")

        # check if tickets are present

        tickets = self.db.get_data_table("Ticket", self.db.ticket_columns, "id > 0")

        present = False
        ticket_data = {}
        for ticket_config in os.listdir(os.path.join(self.path, "ticket_cards")):
            if map_name in ticket_config:
                try:
                    ticket_data = json.load(open(os.path.join(self.path, "ticket_cards", ticket_config)))
                    present = True
                except Exception as e:
                    logger.error(e)

        if not present:
            logger.critical("No tickets config file found for this map_name")
            exit()

        # check if ticket cities correspond to cities
        # check = []
        # for ticket in ticket_data["normal"]:
        #     check.append(ticket["city1"])
        #     check.append(ticket["city2"])

        # check = set(check)
        # check = list(check)

        # check.sort()
        # if set(cities_check) == set(check):
        #     logger.info("Cities and cities in tickets match")
        # else:
        #     logger.critical("Cities and cities in tickets don't match")
        #     exit()

        tickets = self.db.get_data_table("Ticket", self.db.ticket_columns, "id > 0")
        if len(tickets) is not (len(ticket_data["normal"]) + len(ticket_data["special"])):
            self.db.delete_table("Ticket")
            self.db.create_table("Ticket", self.db.ticket_columns)
            insert_data = []
            for ticket in ticket_data["normal"]:
                city1 = self.db.get_data_table("City", [["id"]], "name LIKE '" + str(ticket["city1"]) + "'")
                city2 = self.db.get_data_table("City", [["id"]], "name LIKE '" + str(ticket["city2"]) + "'")
                insert_data.append((city1[0][0], city2[0][0], ticket["value"], 0, None))
            for ticket in ticket_data["special"]:
                city1 = self.db.get_data_table("City", [["id"]], "name LIKE '" + str(ticket["city1"]) + "'")
                city2 = self.db.get_data_table("City", [["id"]], "name LIKE '" + str(ticket["city2"]) + "'")
                insert_data.append((city1[0][0], city2[0][0], ticket["value"], 1, None))
            self.db.insert_data_table("Ticket", [["city1","city2","value","special","owner"]], insert_data)
        
        logger.info("Ticket table OK")

        # Get game parameters
        present = False
        game = {}
        for game_config in os.listdir(os.path.join(self.path, "game")):
            if map_name in game_config:
                try:
                    game = json.load(open(os.path.join(self.path, "game", game_config)))
                    present = True
                except Exception as e:
                    logger.error(e)

        if not present:
            logger.critical("No game config file found for this map_name")
            exit()

        self.nbr_players_for_single_route = game["single_where_double"]
        self.longest_route_active = game["longest_route"]
        self.schips_active = game["schips"]
        self.scores = game["scores"]


        self.default_trains = ""

        
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

        # log all errors
        dp.add_error_handler(error)

        # Start the Bot
        updater.start_polling()

        updater.idle()


    def available_colors(self, update, context):
        """Check which colors are still available"""
        pass

    def start(self, update, context):
        """Start: add the chat_id to the player table"""
        players = self.db.get_data_table("Player", ["chat_id", "color", "color IS NOT NULL"])
        present = False
        for player in players:
            if update.message.chat_id == player["chat_id"]:
                response += "Welcome back to Bobbie's Venetian Hotel & Casino! \n\n We are still playing ticket to ride!!!\n\n"
                response += "Your color is: " + player["color"]
            
        if not present:
            self.db.insert_data_table("Players", self.db.player_columns, [(update.message.chat_id, update.message.from_user.first_name, 0, 0, None)])
        update.message.reply_text(response, reply_markup=markup)
        return SELECTION

    def add(self, update, context):
        """Add a player to the game"""
        choice = update.message.text.lower()
        result = self.db.get_data_table("Player", ["name","color"], "color = " + choice)
        if len(result) > 0:
            response = "Somebody else is already assigned to this color, please choose another one!"
            markup = ReplyKeyboardMarkup(available_colors, one_time_keyboard=True)
            update.message.reply_text(response, reply_markup=markup)
        else:
            self.db.update_data_table("Player", {"color": choice}, "chat_id = " + str(update.message.chat_id))
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            response = "You are assigned to player color: " + player["color"]
            update.message.reply_text(response, reply_markup=markup)
            return OPTIONS 


if __name__ == "__main__":
    bot = VTR_BOT("europe")