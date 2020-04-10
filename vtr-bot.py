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

SELECTION, OPTIONS, CITY, ROUTE, MARKET, TICKET, STATION, CARDS = range(8)

option_keyboard = [["Get Market Card", "Build Route"],
                  ["Build Station", "Get New Tickets"],
                  ["Deck", "Market", "Overview", "Map"],
                  ["Routes", "City", "Your Routes"],
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
        self.url = config["database"]["url"]
        self.db = DatabaseSqlite3(self.url, True)

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

        # check turn table for all players
        ### TO DO

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
        self.stations_active = game["stations"]["enabled"]
        self.scores = game["scores"]
        self.trains_last_turns = game["last_turns_trains"]
        self.turns_left = game["turns_left"]

        # Set game pieces
        present = False
        pieces = {}
        for pieces_config in os.listdir(os.path.join(self.path, "pieces")):
            if map_name in pieces_config:
                try:
                    pieces = json.load(open(os.path.join(self.path, "pieces", pieces_config)))
                    present = True
                except Exception as e:
                    logger.error(e)

        if not present:
            logger.critical("No pieces config file found for this map_name")
            exit()
        self.colors_players = []
        self.amount_trains = pieces[0]["trains"]

        for piece in pieces:
            self.colors_players.append(piece["color"])
        if self.stations_active:
            self.amount_stations = game["stations"]["amount"]
        
        # Initialize Telegram bot
        pp = PicklePersistence(filename="bobbieventianbot")
        updater = Updater(config["telegram"]["token"], persistence= pp, use_context=True)
        dp = updater.dispatcher

        option_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states = {
                SELECTION: [MessageHandler(Filters.regex("^(yellow|black|red|green|blue)$"), self.add),],
                OPTIONS: [MessageHandler(Filters.regex("^(Get Market Card)$"), self.choose_market), MessageHandler(Filters.regex("^(Build Route)$"), self.build_route),
                MessageHandler(Filters.regex("^(Build Station)$"), self.build_station), MessageHandler(Filters.regex("^(Get New Tickets)$"), self.choose_tickets),
                MessageHandler(Filters.regex("^(Deck)$"), self.deck), MessageHandler(Filters.regex("^(Market)$"), self.market),
                MessageHandler(Filters.regex("^(Overview)$"), self.overview), MessageHandler(Filters.regex("^(Map)$"), self.map),
                MessageHandler(Filters.regex("^(Routes)$"), self.all_routes), MessageHandler(Filters.regex("^(City)$"), self.city_information),
                MessageHandler(Filters.regex("^(Your Routes)$"), self.your_routes), MessageHandler(Filters.regex("^(Longest Route)$"), self.longest_route),
                MessageHandler(Filters.regex("^(Points)$"), self.points), MessageHandler(Filters.regex("^(Help)$"), help)],
                CITY: [MessageHandler(Filters.text, self.pick_city),],
                MARKET: [MessageHandler(Filters.text, self.pick_market),],
                TICKET : [MessageHandler(Filters.text, self.pick_ticket),],
                ROUTE : [MessageHandler(Filters.text, self.pick_route),],
                CARDS : [MessageHandler(Filters.text, self.pick_cards),],
            },
            fallbacks = [MessageHandler(Filters.regex("^Done$"), self.start)],
            name = "ticket_to_ride",
            persistent= True
        )

        dp.add_handler(option_handler)
        dp.add_handler(CommandHandler('gogogo', self.start_game))

        # log all errors
        dp.add_error_handler(self.error)

        # Start the Bot
        updater.start_polling()

        updater.idle()


    def available_colors(self, db):
        """Check which colors are still available"""
        available_colors = []
        p_colors = self.colors_players
        players = db.get_data_table("Player", [["chat_id", "color"]], "color IS NOT NULL")
        for player in players:
            p_colors.remove(player[1][0])
        for c in p_colors:
            available_colors.append([c])
        #available_colors.append(["spectator"])
        return available_colors

    def assign_cards(self, db, id, color=None, amount=1):
        """assigns an amount of cards to a player or market"""
        assigned_cards = []
        if color is None:
            available_cards = db.get_data_table("Card", [["id"]], "owner = 0")
            if len(available_cards) < amount:
                db.update_data_table("Card", {"owner": 0}, "id = 2")
                logger.info("Card deck gets reshuffled!")
                # Broadcast
                available_cards = db.get_data_table("Card", [["id"]], "owner = 0")
            i = 0
            while i < amount:
                assigned_cards.append(available_cards[0][0])
                i += 1
            for a_card in assigned_cards:
                db.update_data_table("Card", {"owner": id}, "id = " + str(a_card))
                logger.debug("Card " + str(a_card) + " assigned to " + str(id))
        else:
            market_cards = db.get_data_table("Card", [["id","color"]], "owner = 1")
            present = False
            for market_card in market_cards:
                if market_card[1][0] in color:
                    present = True
                    card_id = market_card[0][0]
            if not present:
                return False
            db.update_data_table("Card", {"owner": id}, "id = " + str(card_id))
            logger.debug("Card " + str(a_card) + " assigned to " + str(id))

        return True

    def dispose_card(self, db, card_id):
        """Dispose a card"""
        db.update_data_table("Card", {"owner": 2}, "id = " + str(card_id))
        logger.debug("Card " + str(card_id) + " disposed!")

    def assign_tickets(self, db, id, amount = 1):
        """assigns an amount of tickets to a player chat_id"""
        assigned_tickets = []
        show_routes = []
        available_tickets = db.get_data_table("Ticket", [["id","city1","city2","value"]], "owner = 0")
        i = 0
        while i < amount:
            assigned_tickets.append(available_tickets[0][0])
            show_routes.append([str(available_tickets[0][0]) + ": " + str(available_tickets[1][0]) + " - " + str(available_tickets[2][0]) + " value: " + str(available_tickets[3][0])])
            i += 1
        for a_ticket in assigned_tickets:
            db.update_data_table("Card", {"owner": id}, "id = " + str(a_ticket))
            logger.debug("Card " + str(a_ticket) + " assigned to " + str(id))
        return show_routes, assigned_tickets
    
    def dispose_ticket(self, db, ticket_id):
        """Dispose a ticket"""
        db.update_data_table("Ticket", {"owner": 0}, "id = " + str(ticket_id))
        logger.debug("Ticket " + str(ticket_id) + " disposed!")

    def match_cards_with_routes(self, routes, cards):
        """See which routes are possible with the cards given.
        If one route given also return card combinations to build the route
        Both routes and cards are tuples containing all database columns"""
        deck = {}
        for card in cards:
            if card[1] not in deck:
                deck[card[1]] = 1
            else:
                deck[card[1]] = 1

        return_routes = []
        for route in routes:
            card_choices = []
            possible = True
            if route[5] > 0:
                if "locomotive" in deck:
                    if deck["locomotive"] < route[5]:
                        possible = False
                else:
                    possible = False
            if route[3] not in "blank":
                if route[3] in deck:
                    if deck[route[3]] < route[4]:
                        if "locomotive" in deck:
                            if deck[route[3]] + deck["locomotive"] < route[4]:
                                possible = False
                            # add choices
                    else:
                        card_choices.append[[route[4] + " " + route[3]]]
                        if "locomotive" in deck:
                            for locomotive in range(1,deck["locomotive"] + 1):
                               card_choices.append[[str(locomotive) + "locomotive + " + str(route[4]-1) + " " + route[3]]] 
            else:
                if "locomotive" in deck:
                    length = route[4] - deck["locomotive"]
                else:
                    length = route[4]
                found = False
                for color, amount in deck.items(): 
                    if amount >= length:
                        found = True
                if not found:
                    possible = False

            if possible:
                route_text = str(route[0]) + ": " + str(route[1]) + " - " + str(route[2]) + " " + str(route[3]) + " dist: " + str(route[4]) + " loc: " + str(route[5])
                if route[6] > 0:
                    route_text += " tunnel"
                return_routes.append([route_text])

        return return_routes, card_choices

    def build_route_with_cards(self, db, chat_id, selection):
        """Assign cards to graveyard"""
        ok = True
        splitted = selection.split(" + ")
        for split in splitted:
            pieces = split.split(" ")
            db.update_data_table("Card", {"owner": 2}, "id = " + str(chat_id) + " AND color LIKE '" + str(pieces[1]) + "'")
        return ok
    
    def make_nested_lists(self, data_list, items_each_line = 3):
        """Makes nested lists with a shape to use as keyboard in markup"""
        outer_list = []
        inner_list = []
        start_index = 0
        stop_index = len(data_list)
        index = start_index
        inner_index = 1
        while index < stop_index:
            inner_list.append(data_list[index])
            if inner_index < items_each_line:
                inner_index += 1
            else:
                outer_list.append(inner_list)

                inner_list = []
                inner_index = 1
            
            index += 1
        if len(inner_list) > 0:
            outer_list.append(inner_list)

        return outer_list

    def next_turn(self, db):
        """Sets the next turn"""
        player = db.get_data_table("Turn", [["sequence, turns"]], "playing = 1")
        db.update_data_table("Turn", {"playing": 0}, "playing = 1")
        players = db.get_data_table("Turn", [["trains"]], "color IS NOT NULL")
        if player[0][1] is None:
            for p in players:
                if p[0] <= self.trains_last_turns:
                    db.update_data_table("Turn", {"turns": self.turns_left}, "chat_id > 0")
        else:
            db.update_data_table("Turn", {"turns": player[0][1] - 1}, "sequence = " +  str(player[0][0]))

        if player[0][0] >= len(players):
            db.update_data_table("Turn", {"playing": 1}, "sequence = 1")
        else:
            db.update_data_table("Turn", {"playing": 1}, "sequence = " + str(player[0][0]))

        player = db.get_data_table("Turn", [["chat_id, sequence, turns"]], "playing = 1")
        if player[0][2] is not None:
            if player[0][2] <= 0:
                # end the game
                response = "GAME HAS ENDED\n\nRESULTS:"
                pass
        info = db.get_data_table("Player", db.player_columns, "chat_id = " + str(player[0][0]))
        response = "Turn for player " + info[5][0] + " -> " + info[1][0]
        # Broadcast
        

    ###########################################################################################################################################

    ### TELEGRAM PART

    ############################################################################################################################################

    def start(self, update, context):
        """Start: add the chat_id to the player table"""
        response = ""
        db = DatabaseSqlite3(self.url)
        players = db.get_data_table("Player", [["chat_id", "color"]], "color IS NOT NULL")
        for player in players:
            if update.message.chat_id == player["chat_id"]:
                response += "Welcome back to Bobbie's Venetian Hotel & Casino! \n\n We are still playing ticket to ride!!!\n\n"
                response += "Your color is: " + player[1][0]
                markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
                update.message.reply_text(response, reply_markup=markup)
                logger.info("user: " + str(update.message.chat_id) + " reconnected!")
                return OPTIONS

        present = False
        spectators = db.get_data_table("Player", [["chat_id", "color"]], "color IS NULL")
        present = False
        for spectator in spectators:
            if update.message.chat_id == spectator[0]:
                response += "Welcome back to Bobbie's Venetian Hotel & Casino! \n\n We are still playing ticket to ride!!!\n\nPlease choose a color you want to play"     
                present = True
                logger.info("user: " + str(update.message.chat_id) + " reconnected!")

        if not present:
            db.insert_data_table("Player", db.player_columns, [(update.message.chat_id, update.message.from_user.first_name, 0, 0, 0, None)])
            response += "Hello, \n\nWelcome to Bobbie\'s Venitian Hotel & Casino\nCome and play with us!\n\nWe are playing Ticket To Ride tonight...\nChoose an available color to add yourself to the game!\n\nYou are now a spectator!"
            logger.info("user: " + str(update.message.chat_id) + " added to player database!")
        available_colors = self.available_colors(db)
        markup = ReplyKeyboardMarkup(available_colors, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        db.close()
        return SELECTION

    def add(self, update, context):
        """Add a player to the game"""
        choice = update.message.text.lower()
        db = DatabaseSqlite3(self.url)
        result = db.get_data_table("Player", [["name","color"]], "color LIKE '" + choice + "'")
        if len(result) > 0:
            response = "Somebody else is already assigned to this color, please choose another one!"
            available_colors = self.available_colors(db)
            markup = ReplyKeyboardMarkup(available_colors, one_time_keyboard=True)
            update.message.reply_text(response, reply_markup=markup)
        else:
            db.update_data_table("Player", {"color": choice}, "chat_id = " + str(update.message.chat_id), True)
            response = "You are assigned to player color: " + choice
            logger.info("user: " + str(update.message.chat_id) + " choose color: " + str(choice))
            # Assign cards
            # Assign special_tickets
            # Assign trains and stations
            context.user_data['initialized'] = False
            context.user_data['dispose_second_ticket'] = False
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text(response, reply_markup=markup)
            db.close()
            return OPTIONS

    def start_game(self, update, context):
        """Start the game"""
        db = DatabaseSqlite3(self.url)
        players = db.get_data_table("Player", [["chat_id"]], "color IS NOT NULL")
        seq = 1
        for player in players:
            if seq is 1:
                db.insert_data_table("Turn", db.turn_columns, [(update.message.chat_id, 1, seq, None)])
                # Broadcast
            else:
                db.insert_data_table("Turn", db.turn_columns, [(update.message.chat_id, 0, seq, None)])
        # Broadcast

    def choose_tickets(self, update, context):
        """Assign three tickets and let them choose which on they want to hold"""
        db = DatabaseSqlite3(self.url)
        # check turn
        tickets, ticket_ids = self.assign_tickets(db, update.message.chat_id, 3)
        tickets.append(["Hold all"])
        context.user_data['tickets_selection'] = ticket_ids
        markup = ReplyKeyboardMarkup(tickets, one_time_keyboard=True)
        update.message.reply_text("Choose the ticket(s) you want to delete:", reply_markup=markup)
        db.close()
        return TICKET

    def pick_ticket(self, update, context):
        """Drop a tickets and let them choose which one they want to hold"""
        choice = update.message.text()
        if choice in "Hold all":
            del context.user_data['tickets_selection']
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("You hold all your new tickets!", reply_markup=markup)
            # Broadcast
            # Next Turn
            context.user_data['initialized'] = True
            return OPTIONS
        
        db = DatabaseSqlite3(self.url)
        ticket_list = choice.split(":")
        result = db.get_data_table("Ticket", db.ticket_columns, "id =" + ticket_list[0])
        if len(result) < 1:
            update.message.reply_text("Input was not correct, choose if you want to delete on of following routes:")
            return TICKET

        self.dispose_ticket(db, result[0][0])
        if context.user_data['dispose_second_ticket'] or not context.user_data['initialized']:
            context.user_data['initialized'] = True
            del context.user_data['tickets_selection']
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Ticket was deleted!", reply_markup=markup)
            # Broadcast
            # Next Turn
            db.close()
            return OPTIONS

        context.user_data['dispose_second_ticket'] = True
        ticket_ids = context.user_data['tickets_selection']
        ticket_ids.remove(int(ticket_list[0]))
        tickets_show = []
        for id in ticket_ids:
            result = db.get_data_table("Ticket", db.ticket_columns, "id = " + str(id))
            tickets_show.append([str(result[0][0]) + ": " + str(result[1][0]) + " - " + str(result[2][0]) + " value: " + str(result[3][0])])
        markup = ReplyKeyboardMarkup(tickets_show, one_time_keyboard=True)
        update.message.reply_text("Ticket was deleted, want to delete another route?", reply_markup=markup)
        db.close()
        return TICKET

    def build_station(self, update, context):
        """Build a station"""
        db = DatabaseSqlite3(self.url)
        # check turn
        # check cards (and check amount of stations build)
        context.user_data['station'] = True
        cities = db.get_data_table("City", db.city_columns, "station IS NULL")
        cities_list = []
        for city in cities:
            cities_list.append(city[1])
        cities_keyboard = self.make_nested_lists(cities_list, 4)
        cities_keyboard.append(["Back"])
        markup = ReplyKeyboardMarkup(cities_keyboard, one_time_keyboard=True)
        update.message.reply_text("Select the city where to build the station:", reply_markup=markup)
        db.close()
        return CITY

    def build_route(self, update, context):
        """Build a route"""
        db = DatabaseSqlite3(self.url)
        # check turn
        context.user_data['route'] = True
        cities = db.get_data_table("City", db.city_columns, "id > 0")
        cities_list = []
        for city in cities:
            cities_list.append(city[1])
        cities_keyboard = self.make_nested_lists(cities_list, 4)
        cities_keyboard.append(["Back"])
        markup = ReplyKeyboardMarkup(cities_keyboard, one_time_keyboard=True)
        update.message.reply_text("Select the city where the route starts:", reply_markup=markup)
        db.close()
        return CITY

    def city_information(self, update, context):
        """Show information about a city"""
        db = DatabaseSqlite3(self.url)
        cities = db.get_data_table("City", db.city_columns, "id > 0")
        cities_list = []
        for city in cities:
            cities_list.append(city[1])
        cities_keyboard = self.make_nested_lists(cities_list, 4)
        cities_keyboard.append(["Back"])
        markup = ReplyKeyboardMarkup(cities_keyboard, one_time_keyboard=True)
        update.message.reply_text("Select the city where the route starts:", reply_markup=markup)
        db.close()
        return CITY

    def pick_city(self, update, context):
        """Choose a city and do what you want to do"""
        choice = update.message.text()
        if choice in "Back":
            context.user_data['station'] = False
            context.user_data['route'] = False
            context.user_data['city_info'] = False
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Going back...", reply_markup=markup)
            return OPTIONS
        db = DatabaseSqlite3(self.url)
        # build station
        if "station" in context.user_data:
            if context.user_data['station']:
                cities = db.get_data_table("City", db.city_columns, "station IS NULL")
                for city in cities:
                    found = False
                    if city[1] in choice:
                        found = True
                    
                if not found:
                    cities_list = []
                    for city in cities:
                        cities_list.append(city[1])
                    cities_keyboard = self.make_nested_lists(cities_list, 4)
                    cities_keyboard.append(["Back"])
                    markup = ReplyKeyboardMarkup(cities_keyboard, one_time_keyboard=True)
                    update.message.reply_text("The input was not valid, choose a station from the list below:", reply_markup=markup)
                    return CITY

                db.update_data_table("City", {{"owner":update.message.chat_id}}, "name LIKE " + str(choice), True)
                logger.info("Station was built in" + str(choice) + "by player: " + str(update.message.chat_id))
                # broadcast
                # next turn
                context.user_data['station'] = False
                markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
                update.message.reply_text("Going back...", reply_markup=markup)
                return OPTIONS
        # build route
        if "route" in context.user_data:
            if context.user_data['route']:
                routes = db.get_data_table("Route", db.route_columns, "city1 LIKE '" + str(choice) + "' OR city2 LIKE '" + str(choice) + "' AND owner = 0")
                if len(routes) < 1:
                    cities = db.get_data_table("City", db.city_columns, "id > 0")
                    cities_list = []
                    for city in cities:
                        cities_list.append(city[1])
                    cities_keyboard = self.make_nested_lists(cities_list, 4)
                    cities_keyboard.append(["Back"])
                    markup = ReplyKeyboardMarkup(cities_keyboard, one_time_keyboard=True)
                    update.message.reply_text("The input was not valid, choose a city from the list below:", reply_markup=markup)
                    return CITY
                
                # get cards 
                player_cards = db.get_data_table("Card", [["color"]], "id = " + str(update.message.chat_id))
                buildable_routes, card_combinations = self.match_cards_with_routes(routes, player_cards)
                markup = ReplyKeyboardMarkup(buildable_routes, one_time_keyboard=True)
                update.message.reply_text("Select one of following route's to build:", reply_markup=markup)
                return ROUTE

        # show information
    def pick_route(self, update, context):
        """Choose a route to build and get cards selection"""
        choice = update.message.text()
        if choice in "Back" or not context.user_data['route']:
            context.user_data['route'] = False
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Going back...", reply_markup=markup)
            return OPTIONS

    def pick_cards(self, update, context):
        """Get the cards selection to build a route"""
        choice = update.message.text()
        if choice in "Back" or not context.user_data['route']:
            context.user_data['route'] = False
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Going back...", reply_markup=markup)
            return OPTIONS

    def choose_market(self, update, context):
        """Choose a card from the market place"""
        db = DatabaseSqlite3(self.url)
        # check turn
        context.user_data['second_pick'] = False
        market_cards = db.get_data_table("Card", db.card_columns, "id = 1")
        market_list = []
        for card in market_cards:
            market_list.append(card[1])
        market_list.append("random")
        market_keyboard = self.make_nested_lists(market_list, 2)
        market_keyboard.append(["Back"])
        markup = ReplyKeyboardMarkup(market_keyboard, one_time_keyboard=True)
        update.message.reply_text("Select a card from the market:", reply_markup=markup)
        db.close()
        return MARKET

    def pick_market(self, update, context):
        """Pick a card from the market"""
        choice = update.message.text()
        if choice in "Back":
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Going back...", reply_markup=markup)
            return OPTIONS
        db = DatabaseSqlite3(self.url)
        if choice in "random":
            self.assign_cards(db, update.message.chat_id)
            if context.user_data['second_pick']:
                markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
                update.message.reply_text("Selected a random card :", reply_markup=markup)
                # show deck
                # next turn
                # broadcast
                db.close()
                return OPTIONS
            else:
                market_cards = db.get_data_table("Card", db.card_columns, "id = 1 AND color NOT LIKE locomotive")
                market_list = []
                for card in market_cards:
                    market_list.append(card[1])
                market_list.append("random")
                market_keyboard = self.make_nested_lists(market_list, 2)
                market_keyboard.append(["Back"])
                markup = ReplyKeyboardMarkup(market_keyboard, one_time_keyboard=True)
                update.message.reply_text("Select a card from the market:", reply_markup=markup)
                # broadcast
                db.close()
                return MARKET
            
        market_colors = db.get_data_table("Card", [["color"]], "id = 1")
        found = False
        for color in market_colors:
            if choice in color:
                if context.user_data['second_pick'] and color not in "locomotive":
                    found = True
                else:
                    found = True

        if not found:
            market_list = []
            for card in market_cards:
                market_list.append(card[1])
            market_list.append("random")
            market_keyboard = self.make_nested_lists(market_list, 2)
            market_keyboard.append(["Back"])
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Input was not valid, try picking a card again:", reply_markup=markup)
            return MARKET

        self.assign_cards(db, update.message.chat_id, choice)
        self.assign_cards(db, 1)
        if context.user_data['second_pick']:
            context.user_data['second_pick'] = False
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("You chose a card!", reply_markup=markup)
            # show deck
            # next turn
            # broadcast
            db.close()
            return OPTIONS
        
        context.user_data['second_pick'] = True
        market_cards = db.get_data_table("Card", db.card_columns, "id = 1 AND color NOT LIKE locomotive")
        market_list = []
        for card in market_cards:
            market_list.append(card[1])
        market_list.append("random")
        market_keyboard = self.make_nested_lists(market_list, 2)
        market_keyboard.append(["Back"])
        markup = ReplyKeyboardMarkup(market_keyboard, one_time_keyboard=True)
        update.message.reply_text("You chose a card, choose another one:", reply_markup=markup)
        # show deck
        # broadcast
        return MARKET

    def deck(self, update, context):
        """Show your current deck"""
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS

    def market(self, update, context):
        """Show the market"""
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS
    
    def overview(self, update, context):
        """Shows the overview of the game"""
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS

    def map(self, update, context):
        """send the map as a png"""
        #bot.send_photo(chat_id=chat_id, photo=open('tests/test.png', 'rb'))
        #https://github.com/python-telegram-bot/python-telegram-bot/wiki/Code-snippets#post-an-image-file-from-disk
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS

    def all_routes(self, update, context):
        """Show all routes in the game"""
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS

    def your_routes(self, update, context):
        """Show all the route you pocess"""
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS

    def longest_route(self, update, context):
        """Show who has the longest continous route"""
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS

    def points(self, update, context):
        """Show all the players points"""
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS

    def help(self, update, context):
        """help section"""
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        return OPTIONS


    def error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)


if __name__ == "__main__":
    bot = VTR_BOT("europe")