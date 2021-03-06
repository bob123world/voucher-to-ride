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

#option_keyboard = [["Get Market Card", "Build Route"],["Build Station", "Get New Tickets"],["Deck", "Market", "Overview", "Map"], ["Routes", "City", "Your Routes"],["Longest Route", "Points", "Help"]]
option_keyboard = [["Get Market Card", "Get New Tickets"], ["Deck", "Market", "Overview", "Map", "City"],["Next Turn"]]

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
        self.map_name = map_name

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
            random.shuffle(ticket_data["normal"])
            for ticket in ticket_data["normal"]:
                city1 = self.db.get_data_table("City", [["id"]], "name LIKE '" + str(ticket["city1"]) + "'")
                city2 = self.db.get_data_table("City", [["id"]], "name LIKE '" + str(ticket["city2"]) + "'")
                insert_data.append((city1[0][0], city2[0][0], ticket["value"], 0, None))
            random.shuffle(ticket_data["special"])
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

        self.token = config["telegram"]["token"]
        
        # Initialize Telegram bot
        pp = PicklePersistence(filename="bobbieventianbot")
        updater = Updater(self.token, persistence= pp, use_context=True)
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
                MessageHandler(Filters.regex("^(Points)$"), self.points), MessageHandler(Filters.regex("^(Help)$"), help), MessageHandler(Filters.regex("^(Next Turn)$"), self.next_turn_hehe)],
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
            p_colors.remove(player[1])
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
                assigned_cards.append(available_cards[i][0])
                i += 1
            for a_card in assigned_cards:
                db.update_data_table("Card", {"owner": id}, "id = " + str(a_card))
                logger.debug("Card " + str(a_card) + " assigned to " + str(id))
        else:
            market_cards = db.get_data_table("Card", [["id","color"]], "owner = 1")
            present = False
            for market_card in market_cards:
                if color in market_card[1]:
                    present = True
                    card_id = market_card[0]
            if not present:
                return False
            db.update_data_table("Card", {"owner": id}, "id = " + str(card_id))
            logger.debug("Card " + str(color) + " assigned to " + str(id))

        return True

    def dispose_card(self, db, card_id):
        """Dispose a card"""
        db.update_data_table("Card", {"owner": 2}, "id = " + str(card_id))
        logger.debug("Card " + str(card_id) + " disposed!")

    def assign_tickets(self, db, id, amount = 1):
        """assigns an amount of tickets to a player chat_id"""
        assigned_tickets = []
        show_routes = []
        available_tickets = db.get_data_table("Ticket", [["id","city1","city2","value"]], "owner IS NULL")
        i = 0
        while i < amount:
            assigned_tickets.append(available_tickets[i][0])
            city1 = db.get_data_table("City", [["name"]], "id = " + str(available_tickets[i][1]))
            city2 = db.get_data_table("City", [["name"]], "id = " + str(available_tickets[i][2]))
            show_routes.append([str(available_tickets[i][0]) + ": " + str(city1[0][0]) + " - " + str(city2[0][0]) + " value: " + str(available_tickets[i][3])])
            i += 1
        for a_ticket in assigned_tickets:
            db.update_data_table("Ticket", {"owner": id}, "id = " + str(a_ticket))
            logger.debug("Ticket " + str(a_ticket) + " assigned to " + str(id))
        return show_routes, assigned_tickets
    
    def dispose_ticket(self, db, ticket_id):
        """Dispose a ticket"""
        db.update_data_table("Ticket", {"owner": 0}, "id = " + str(ticket_id))
        logger.debug("Ticket " + str(ticket_id) + " disposed!")

    def show_route(self, db, routes, array = False):
        """See which routes are possible with the cards given.
        If one route given also return card combinations to build the route
        Both routes and cards are tuples containing all database columns"""
        return_routes = []
        for route in routes:
            city1 = db.get_data_table("City", [["name"]], "id = " + str(route[1]))
            city2 = db.get_data_table("City", [["name"]], "id = " + str(route[2]))
            route_text = str(route[0]) + ": " + str(city1[0][0]) + " - " + str(city2[0][0]) + " " + str(route[3]) + " dist: " + str(route[4]) + " loc: " + str(route[5])
            if route[6] > 0:
                route_text += " tunnel"
            if array:
                return_routes.append([route_text])
            else:
                return_routes.append(route_text)

        return return_routes

    def possible_card_combination(self, db, id, distance, color, locomotives = 0):
        """Check what card combinations are possible for a route"""
        possible = True
        deck_cards = db.get_data_table("Ticket", [["color"]], "owner = " + str(id))
        deck = {}
        possible_combinations = []
        rest_distance = distance

        for card in deck_cards:
            if card[0] in deck:
                deck[card[0]] += 1
            else:
                deck[card[0]] = 1

        if locomotives > 0:
            if "locomotive" in deck:
                if deck["locomotive"] >= locomotives:
                    deck["locomotive"] -= locomotives
                    rest_distance -= locomotives
                else:
                    possible = False
            else:
                possible = False
        
        colors = []
        if color in "blank":
            for c in deck:
                colors.append[c]
        else:
            colors.append[color]

        combination_found = False
        for c in colors:
            if c in deck:
                # All color cards
                if rest_distance >= deck[c]:
                    combination_found = True
                    locos = deck["locomotive"]
                    if locos > 0:
                        if locomotives > 0:
                            for l in range(0,locos+1):
                                possible_combinations.append([str(locomotives + l) + " x locomotives + " +  str(deck[c] - l) + " x " + c])
                        else:
                            possible_combinations.append [str(deck[c]) + " x " + c]
                            for l in range(1,locos+1):
                                possible_combinations.append([str(l) + " x locomotives + " +  str(deck[c] - l) + " x " + c])
                    else:
                        if locomotives > 0:
                            possible_combinations.append([str(locomotives) + " x locomotives + " +  str(deck[c]) + " x " + c])
                        else:
                            possible_combinations.append([str(deck[c]) + " x " + c])
                # color and locomotives
                elif rest_distance >= deck[c] + deck["locomotive"]:
                    combination_found = True
                    locos_nec = rest_distance - deck[c]
                    locos = deck["locomotive"] - locos_nec
                    if locos > 0:
                        if locomotives > 0:
                            for l in range(0,locos+1):
                                possible_combinations.append([str(locomotives + l + locos_nec) + " x locomotives + " +  str(deck[c] - l) + " x " + c])
                        else:
                            possible_combinations.append([str(locos_nec) + " x locomotives + " +  str(deck[c]) + " x " + c])
                            for l in range(1,locos+1):
                                possible_combinations.append([str(l + locos_nec) + " x locomotives + " +  str(deck[c] - l) + " x " + c])
                    else:
                        if locomotives > 0:
                            possible_combinations.append([str(locomotives + locos_nec) + " x locomotives + " +  str(deck[c]) + " x " + c])
                        else:
                            possible_combinations.append([str(locos_nec) + " x locomotives + " +  str(deck[c]) + " x " + c])
            else:
                possible = False

        if not combination_found:
            possible = False
        
        return possible, possible_combinations

    def build_route_with_cards(self, db, chat_id, selection):
        """Assign cards to graveyard"""
        ok = True
        splitted = selection.split(" + ")
        for split in splitted:
            pieces = split.split(" ")
            db.update_data_table("Card", {"owner": 2}, "id = " + str(chat_id) + " AND color LIKE '" + str(pieces[1]) + "'")
        return ok

    def show_deck(self, db, id, anonimity = False):
        """Places the deck inside a return string"""
        response = ""
        tickets = db.get_data_table("Ticket", [["id","city1","city2","value"]], "owner = " + str(id))
        response = "Tickets: " + str(len(tickets)) + "\n"
        if not anonimity:
            for ticket in tickets:
                city1 = db.get_data_table("City", [["name"]], "id = " + str(ticket[1]))
                city2 = db.get_data_table("City", [["name"]], "id = " + str(ticket[2]))
                response += str(ticket[0]) + ": " + str(city1[0][0]) + " - " + str(city2[0][0]) + " value: " + str(ticket[3]) + "\n"
            response += "\n"

        cards = db.get_data_table("Card", [["color"]], "owner = " + str(id))
        response += "Cards: " + str(len(cards)) + "\n"
        if not anonimity:
            card_dict = {}
            for card in cards:
                if card[0] in card_dict:
                    card_dict[card[0]] += 1
                else:
                    card_dict[card[0]] = 1
            for color, amount in card_dict.items():
                response += str(amount) + " " + str(color) + "\n"
            response += "\n"

        player = db.get_data_table("Player", [["trains","stations"]], "chat_id = " + str(id))
        response += "Trains: " + str(player[0][0]) + "\n"
        response += "Stations: " + str(player[0][1]) + "\n"
        if player[0][1] < self.amount_stations:
            stations = db.get_data_table("Station", [["name"]], "owner = " + str(id))
            response += "Station(s) built in: "
            for station in stations:
                response += str(station[0]) + ", "
            response = response[:-2]
        return response

    def show_market(self, db):
        """Show the train cards in the market"""
        response = "Market:\n"
        market = db.get_data_table("Card", [["color"]], "owner = 1")
        for i,card in enumerate(market):
            response += str(i+1) + " " + str(card[0]) + "\n"

        return response
    
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
        if len(player) < 1:
            return
        db.update_data_table("Turn", {"playing": 0}, "playing = 1")
        players = db.get_data_table("Player", [["trains"]], "color IS NOT NULL")
        if player[0][1] is None:
            for p in players:
                if p[0] <= self.trains_last_turns:
                    db.update_data_table("Turn", {"turns": self.turns_left}, "chat_id > 0")
        else:
            db.update_data_table("Turn", {"turns": player[0][1] - 1}, "sequence = " +  str(player[0][0]))

        if player[0][0] >= len(players):
            db.update_data_table("Turn", {"playing": 1}, "sequence = 1")
        else:
            db.update_data_table("Turn", {"playing": 1}, "sequence = " + str(player[0][0] + 1))

        player = db.get_data_table("Turn", [["chat_id, sequence, turns"]], "playing = 1")
        if player[0][2] is not None:
            if player[0][2] <= 0:
                # end the game
                response = "GAME HAS ENDED\n\nRESULTS:"
                pass
        info = db.get_data_table("Player", db.player_columns, "chat_id = " + str(player[0][0]))
        response = "Turn for player " + info[0][5] + " -> " + info[0][1]
        self.broadcast(db, response)

    def your_turn(self, db, id):
        """Check if it is your turn"""
        player = db.get_data_table("Turn", [["chat_id"]], "playing = 1")
        if player[0][0] == id:
            return True
        else:
            return False

    def broadcast(self, db, message):
        """broadcast a message to all the players"""
        players = db.get_data_table("Player", db.player_columns, "chat_id > 0")
        
        for player in players:
            send_text = 'https://api.telegram.org/bot' + self.token + '/sendMessage?chat_id=' + str(player[0]) + '&parse_mode=Markdown&text=' + message

            response = requests.get(send_text)
        

    ###########################################################################################################################################

    ### TELEGRAM PART

    ############################################################################################################################################

    def start(self, update, context):
        """Start: add the chat_id to the player table"""
        response = ""
        db = DatabaseSqlite3(self.url)
        self.broadcast(db, update.message.from_user.first_name + " has joined!")
        players = db.get_data_table("Player", [["chat_id", "color"]], "color IS NOT NULL")
        for player in players:
            if update.message.chat_id == player[0]:
                response += "Welcome back to Bobbie's Venetian Hotel & Casino! \n\n We are still playing ticket to ride!!!\n\n"
                response += "Your color is: " + str(player[1][0])
                markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
                update.message.reply_text(response, reply_markup=markup)
                logger.info("user: " + str(update.message.chat_id) + " reconnected!")
                self.broadcast(db, update.message.from_user.first_name + " has joined again!")
                return OPTIONS

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
            response = "You are assigned to player color: " + choice
            logger.info("user: " + str(update.message.chat_id) + " choose color: " + str(choice))
            # Assign cards
            self.assign_cards(db, update.message.chat_id, None, 4)
            # Assign special_tickets
            special_tickets = db.get_data_table("Ticket", [["id"]], "special = 1 AND owner IS NULL")
            db.update_data_table("Ticket", {"owner": update.message.chat_id}, "id = " + str(special_tickets[0][0]))
            # Assign trains and stations
            db.update_data_table("Player", {"trains": self.amount_trains, "stations": self.amount_stations, "color": choice}, "chat_id = " + str(update.message.chat_id), True)
            context.user_data['initialized'] = False
            context.user_data['dispose_second_ticket'] = False
            # Show the map
            present = False
            for board in os.listdir(os.path.join(self.path, "board")):
                if self.map_name in board:
                    try:
                        picture = os.path.join(self.path, "board", board)
                        present = True
                    except Exception as e:
                        logger.error(e)
            if not present:
                update.message.reply_text("Unable to find map picture!")
            else:
                update.message.reply_photo(open(picture, 'rb'))
            # Show the deck
            deck = "Deck:\n"
            deck += self.show_deck(db, update.message.chat_id)
            update.message.reply_text(deck)
            # Assing 3 normal tickets
            tickets, ticket_ids = self.assign_tickets(db, update.message.chat_id, 3)
            tickets.append(["Hold all"])
            context.user_data['tickets_selection'] = ticket_ids
            response += "\nChoose if you want to delete one of the below route's:"
            markup = ReplyKeyboardMarkup(tickets, one_time_keyboard=True)
            update.message.reply_text(response, reply_markup=markup)
            self.broadcast(db, update.message.from_user.first_name + " choose color " + choice + " and was added to the game's players.")
            logger.info("Player " + str(update.message.chat_id) + " choose color " + choice)
            db.close()
            return TICKET

    def start_game(self, update, context):
        """Start the game"""
        db = DatabaseSqlite3(self.url)
        players = db.get_data_table("Player", [["chat_id","name","color"]], "color IS NOT NULL")
        seq = 1
        message = "THE GAME STARTS\n\nCHEW CHEW\n\nGOOD LUCK AND HAVE FUN!\n\n"
        for player in players:
            if seq is 1:
                db.insert_data_table("Turn", db.turn_columns, [(player[0], 1, seq, None)])
                message += str(player[2]) + "(" + str(player[1]) + ") goes first"
            else:
                db.insert_data_table("Turn", db.turn_columns, [(player[0], 0, seq, None)])
            seq += 1
        self.broadcast(db, message)
        db.close()

    def choose_tickets(self, update, context):
        """Assign three tickets and let them choose which on they want to hold"""
        db = DatabaseSqlite3(self.url)
        if not self.your_turn(db, update.message.chat_id):
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("It's not your turn yet! Going back...", reply_markup=markup)
            db.close()
            return OPTIONS
        tickets, ticket_ids = self.assign_tickets(db, update.message.chat_id, 3)
        tickets.append(["Hold all"])
        context.user_data['tickets_selection'] = ticket_ids
        context.user_data['dispose_second_ticket'] = False
        markup = ReplyKeyboardMarkup(tickets, one_time_keyboard=True)
        player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
        self.broadcast(db, player[0][1] + " (" + player[0][0] + ") " + " took 3 new tickets")
        deck = self.show_deck(db, update.message.chat_id)
        update.message.reply_text(deck)
        update.message.reply_text("Choose the ticket(s) you want to delete:", reply_markup=markup)
        db.close()
        logger.debug("Player " + str(update.message.chat_id) + " has had three new tickets")
        return TICKET

    def pick_ticket(self, update, context):
        """Drop a tickets and let them choose which one they want to hold"""
        choice = update.message.text
        db = DatabaseSqlite3(self.url)
        if choice in "Hold all":
            del context.user_data['tickets_selection']
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("You hold all the rest of the new tickets!", reply_markup=markup)
            player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
            self.broadcast(db, str(player[0][0]) + " (" + str(player[0][1]) + ") " + " holds the rest of the new tickets")
            self.next_turn(db)
            context.user_data['initialized'] = True
            deck = self.show_deck(db, update.message.chat_id)
            update.message.reply_text(deck)
            db.close()
            return OPTIONS
        
        db = DatabaseSqlite3(self.url)
        ticket_list = choice.split(":")
        result = db.get_data_table("Ticket", db.ticket_columns, "id = " + ticket_list[0])
        if len(result) < 1:
            update.message.reply_text("Input was not correct, choose if you want to delete on of following routes:")
            return TICKET

        self.dispose_ticket(db, result[0][0])
        if context.user_data['dispose_second_ticket'] or not context.user_data['initialized']:
            context.user_data['initialized'] = True
            del context.user_data['tickets_selection']
            del context.user_data['dispose_second_ticket']
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Ticket was deleted!", reply_markup=markup)
            player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
            deck = self.show_deck(db, update.message.chat_id)
            update.message.reply_text(deck)
            self.broadcast(db, player[0][1] + " (" + player[0][0] + ") " + " deleted one of the new tickets.")
            self.next_turn(db)
            db.close()
            return OPTIONS

        context.user_data['dispose_second_ticket'] = True
        ticket_ids = context.user_data['tickets_selection']
        ticket_ids.remove(int(ticket_list[0]))
        tickets_show = []
        for id in ticket_ids:
            result = db.get_data_table("Ticket", db.ticket_columns, "id = " + str(id))
            tickets_show.append([str(result[0][0]) + ": " + str(result[0][1]) + " - " + str(result[0][2]) + " value: " + str(result[0][3])])
        markup = ReplyKeyboardMarkup(tickets_show, one_time_keyboard=True)
        player = db.get_data_table("Player", [["name", "color"]], "id = " + str(update.message.chat_id))
        self.broadcast(db, player[0][1] + " (" + player[0][0] + ") " + " deletes one of the new tickets")
        deck = self.show_deck(db, update.message.chat_id)
        update.message.reply_text(deck)
        update.message.reply_text("Ticket was deleted, want to delete another route?", reply_markup=markup)
        db.close()
        return TICKET

    def build_station(self, update, context):
        """Build a station"""
        db = DatabaseSqlite3(self.url)
        station = db.get_data_table("City", [["id"]], "station = " + str(update.message.chat_id))
        possible, combination = self.possible_card_combination(db, update.message.chat_id, len(station)+1, "blank")
        if not self.your_turn(db, update.message.chat_id) or not possible:
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("You don't have the cards to build a new station or it's just not your turn yet! Going back...", reply_markup=markup)
            db.close()
            logger.debug("Player " + str(update.message.chat_id) + " tried to build a station, but was denied!")
            return OPTIONS

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
        logger.debug("Player " + str(update.message.chat_id) + " tries to build a station in CITY state")
        return CITY

    def build_route(self, update, context):
        """Build a route"""
        db = DatabaseSqlite3(self.url)
        if not self.your_turn(db, update.message.chat_id):
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("It's not your turn yet! Going back...", reply_markup=markup)
            db.close()
            return OPTIONS
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
        logger.debug("Player " + str(update.message.chat_id) + " wants to build route goto CITY state")
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
        update.message.reply_text("Select the city for which you want information:", reply_markup=markup)
        db.close()
        logger.debug("Player " + str(update.message.chat_id) + " wants city information goto CITY state")
        return CITY

    def pick_city(self, update, context):
        """Choose a city and do what you want to do"""
        choice = update.message.text
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
                    db.close()
                    logger.debug("Player " + str(update.message.chat_id) + " gave invalid input in build station")
                    return CITY

                db.update_data_table("City", {{"owner":update.message.chat_id}}, "name LIKE " + str(choice), True)
                logger.info("Station was built in" + str(choice) + "by player: " + str(update.message.chat_id))
                player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
                self.broadcast(db, player[0][0] + " (" + player[0][0] + ") " + " build a station in " + choice)
                station = db.get_data_table("City", [["id"]], "station = " + str(update.message.chat_id))
                possible, combination = self.possible_card_combination(db, update.message.chat_id, len(station)+1, "blank")
                context.user_data['station'] = False
                markup = ReplyKeyboardMarkup(combination, one_time_keyboard=True)
                update.message.reply_text("Select the cards you want to use to build this station:", reply_markup=markup)
                db.close()
                logger.info("Player " + str(update.message.chat_id) + " wants to build a station in " + choice + " going to state CARDS")
                return CARDS

        # build route
        if "route" in context.user_data:
            if context.user_data['route']:
                city = db.get_data_table("City", [["id"]], "name LIKE '" + choice + "'")
                routes = db.get_data_table("Route", db.route_columns, "city1 = " + str(city[0][0]) + " OR city2 = " + str(city[0][0]) + " AND owner = 0")
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
                 
                possible_routes = []
                for route in routes:
                    possible, combination = self.possible_card_combination(db, update.message.chat_id, route[4], route[3],route[5])
                    if possible:
                        possible_routes.append(route)
                
                routes_keyboard = self.show_route(possible_routes, True)
                routes_keyboard.append(["Back"])

                markup = ReplyKeyboardMarkup(routes_keyboard, one_time_keyboard=True)
                update.message.reply_text("Select one of following route's to build:", reply_markup=markup)
                logger.info("Player " + str(update.message.chat_id) + " wants to build a route from " + choice + " going to state ROUTE")
                context.user_data['route_city'] = choice
                return ROUTE

        # city information
        cities = db.get_data_table("City", db.city_columns, "id > 0")
        found = False
        for city in cities:
            if choice in city[1]:
                found = True

        if not found:
            cities_list = []
            for city in cities:
                cities_list.append(city[1])
            cities_keyboard = self.make_nested_lists(cities_list, 4)
            cities_keyboard.append(["Back"])
            markup = ReplyKeyboardMarkup(cities_keyboard, one_time_keyboard=True)
            update.message.reply_text("The input was not valid, choose a city from the list below:", reply_markup=markup)

        response = choice + "\nroutes:\n"
        city = db.get_data_table("City", [["id"]], "name LIKE '" + choice + "'")
        routes = db.get_data_table("Route", db.route_columns, "city1 = " + str(city[0][0]) + " OR city2 = " + str(city[0][0]) + " AND owner = 0")
        routes_info = self.show_route(db, routes, False)
        for r in routes_info:
            response += r + "\n"
        city = db.get_data_table("City", [["station"]], "name like '" + choice + "'")
        if city[0][0] is not None:
            player = db.get_data_table("Player", [["name"]], "chat_id = " + str(city))
            response += "Station built by " + str(player[0][0])
        else:
            response += "No station built yet in this city"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response , reply_markup=markup)
        return OPTIONS


    def pick_route(self, update, context):
        """Choose a route to build and get cards selection"""
        choice = update.message.text
        db = DatabaseSqlite3(self.url)
        if choice in "Back" or not context.user_data['route']:
            context.user_data['route'] = False
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Going back...", reply_markup=markup)
            logger.debug("Player " + str(update.message.chat_id) + " goes back to OPTIONS")
            return OPTIONS

        city = db.get_data_table("City", [["id"]], "name LIKE '" + context.user_data['route_city'] + "'")
        routes = db.get_data_table("Route", db.route_columns, "city1 = " + str(city[0][0]) + " OR city2 = " + str(city[0][0]) + " AND owner = 0")
        del context.user_data['route_city']
        possible_routes = []
        for route in routes:
            possible, combination = self.possible_card_combination(db, update.message.chat_id, route[4], route[3],route[5])
            if possible:
                possible_routes.append(route)
        
        routes_keyboard = self.show_route(possible_routes, True)
        
        if choice not in possible_routes:
            routes_keyboard.append(["Back"])
            markup = ReplyKeyboardMarkup(routes_keyboard, one_time_keyboard=True)
            update.message.reply_text("Input not valid, select one of following route's to build:", reply_markup=markup)
            logger.info("Player " + str(update.message.chat_id) + " invalid input in ROUTE => wants to build a route from " + choice + " going to state ROUTE")
            return ROUTE
        
        choice_sections = choice.split(":")
        route = db.get_data_table("Route", [["color","distance","locomotives"]], "id = " + choice_sections[0])
        possible, combination = self.possible_card_combination(db, update.message.chat_id, route[0][1], route[0][0], route[0][2])
        markup = ReplyKeyboardMarkup(combination, one_time_keyboard=True)
        update.message.reply_text("Select the cards you want to use to build this route:", reply_markup=markup)
        context.user_data['route_id'] = choice_sections[0]
        logger.info("Player " + str(update.message.chat_id) + " wants to build a route " + choice + " going to state CARDS")
        return CARDS


    def pick_cards(self, update, context):
        """Get the cards selection to build a route or station"""
        db = DatabaseSqlite3(self.url)
        choice = update.message.text
        if choice in "Back":
            context.user_data['route'] = False
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Going back...", reply_markup=markup)
            self.next_turn(db)
            db.close()
            return OPTIONS

        if context.user_data['station']:
            stations = db.get_data_table("Route", db.route_columns, "owner = " + str(update.message.chat_id))
            possible, combination = self.possible_card_combination(db, update.message.chat_id, len(stations) + 1, "blank")
            input_correct = False
            for combo in combination:
                if choice in combo:
                    input_correct = True
            
            if not input_correct:
                combination.append(["Back"])
                markup = ReplyKeyboardMarkup(combination, one_time_keyboard=True)
                update.message.reply_text("Input was not valid, select the cards you want to use to build this station:", reply_markup=markup)
                return CARDS

            context.user_data['station'] = False
            choice_split = choice.split(" + ")
            if len(choice_split) < 2:
                card_split = choice_split[0].split(" x ")
                used_cards = int(card_split[0]) * [card_split[1]]
            else:
                card_split = choice_split[0].split(" x ")
                used_cards = int(card_split[0]) * [card_split[1]]
                card_split = choice_split[1].split(" x ")
                used_cards += int(card_split[0]) * [card_split[1]]
            for card in used_cards:
                db.update_data_table("Card", {{"id":2}}, "color LIKE '" + card + "' AND owner = " + str(update.message.chat_id))

            db.update_data_table("City", {{"station":update.message.chat_id}}, "name LIKE '" + context.user_data['station_city'] + "'")
            logger.info("Player " + str(update.message.chat_id) + " has build a station in " + context.user_data['station_city'] + " with cards " + choice + " back to state OPTIONS")
            player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
            self.broadcast(db, str(player[0][0]) + " (" + str(player[0][1]) + ") has build a station in city: " + context.user_data['station_city'] + " with cards " + choice)
            self.next_turn(db)
            deck = self.show_deck(db, update.message.chat_id)
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text(deck, reply_markup=markup)
            db.close()
            return OPTIONS

        if context.user_data['route']:
            route = db.get_data_table("Route", db.route_columns, "id = " + context.user_data['route_id'])
            possible, combination = self.possible_card_combination(db, update.message.chat_id, route[0][4], route[0][3], route[0][5])
            input_correct = False
            for combo in combination:
                if choice in combo:
                    input_correct = True

            if not input_correct:
                combination.append(["Back"])
                markup = ReplyKeyboardMarkup(combination, one_time_keyboard=True)
                update.message.reply_text("Input was not valid, select the cards you want to use to build this route:", reply_markup=markup)
                return CARDS

            choice_split = choice.split(" + ")
            if len(choice_split) < 2:
                card_split = choice_split[0].split(" x ")
                used_cards = int(card_split[0]) * [card_split[1]]
            else:
                card_split = choice_split[0].split(" x ")
                used_cards = int(card_split[0]) * [card_split[1]]
                card_split = choice_split[1].split(" x ")
                used_cards += int(card_split[0]) * [card_split[1]]
            for card in used_cards:
                db.update_data_table("Card", {{"id":2}}, "color LIKE '" + card + "' AND owner = " + str(update.message.chat_id))

            db.update_data_table("Route", {{"owner":update.message.chat_id}}, "id = " + str(context.user_data['route_id']) )
            del context.user_data['route_id']
            context.user_data['route'] = False
            route_info = self.show_route(db, route, False)
            logger.info("Player " + str(update.message.chat_id) + " has build route " + route_info + " with cards " + choice + " back to state OPTIONS")
            player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
            self.broadcast(db, str(player[0][0]) + " (" + str(player[0][1]) + ") has build following route: " + route_info + " with the cards " + choice)
            self.next_turn(db)
            deck = self.show_deck(db, update.message.chat_id)
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text(deck, reply_markup=markup)
            db.close()
            return OPTIONS

        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text("Something went wrong, going back", reply_markup=markup)
        db.close()
        return OPTIONS


    def choose_market(self, update, context):
        """Choose a card from the market place"""
        db = DatabaseSqlite3(self.url)
        if not self.your_turn(db, update.message.chat_id):
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("It's not your turn yet! Going back...", reply_markup=markup)
            db.close()
            return OPTIONS
        context.user_data['second_pick'] = False
        market_cards = db.get_data_table("Card", db.card_columns, "owner = 1")
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
        choice = update.message.text
        if choice in "Back":
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("Going back...", reply_markup=markup)
            return OPTIONS
        db = DatabaseSqlite3(self.url)
        if choice in "random":
            self.assign_cards(db, update.message.chat_id)
            if context.user_data['second_pick']:
                markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
                update.message.reply_text("Selected a random card.", reply_markup=markup)
                self.next_turn(db)
                deck = self.show_deck(db, update.message.chat_id)
                update.message.reply_text(deck)
                player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
                self.broadcast(db, player[0][1] + " (" + player[0][0] + ") " + " choose a random card!")
                db.close()
                return OPTIONS
            else:
                market_cards = db.get_data_table("Card", db.card_columns, "owner = 1 AND color NOT LIKE 'locomotive'")
                market_list = []
                for card in market_cards:
                    market_list.append(card[1])
                market_list.append("random")
                market_keyboard = self.make_nested_lists(market_list, 2)
                market_keyboard.append(["Back"])
                markup = ReplyKeyboardMarkup(market_keyboard, one_time_keyboard=True)
                deck = self.show_deck(db, update.message.chat_id)
                update.message.reply_text(deck)
                update.message.reply_text("Select a card from the market:", reply_markup=markup)
                player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
                self.broadcast(db, player[0][1] + " (" + player[0][0] + ") " + " choose a random card!")
                db.close()
                return MARKET
            
        market_colors = db.get_data_table("Card", [["color"]], "owner = 1")
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
            player = db.get_data_table("Player", [["name", "color"]], "id = " + str(update.message.chat_id))
            self.broadcast(db, player[0][1] + " (" + player[0][0] + ") " + " choose a random card!")
            return MARKET

        self.assign_cards(db, update.message.chat_id, choice)
        self.assign_cards(db, 1)
        deck = self.show_deck(db, update.message.chat_id)
        update.message.reply_text(deck)
        player = db.get_data_table("Player", [["name", "color"]], "chat_id = " + str(update.message.chat_id))
        self.broadcast(db, player[0][1] + " (" + player[0][0] + ") " + " choose " + choice + " from the market.")
        market_info = "New Market: \n"
        market_info += self.show_market(db)
        self.broadcast(db, market_info)
        if context.user_data['second_pick']:
            context.user_data['second_pick'] = False
            markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
            update.message.reply_text("You choose a card!", reply_markup=markup)
            deck = self.show_deck(db, update.message.chat_id)
            update.message.reply_text(deck)
            self.next_turn(db)
            db.close()
            return OPTIONS
        
        context.user_data['second_pick'] = True
        deck = self.show_deck(db, update.message.chat_id)
        update.message.reply_text(deck)
        market_cards = db.get_data_table("Card", db.card_columns, "id = 1 AND color NOT LIKE 'locomotive'")
        market_list = []
        for card in market_cards:
            market_list.append(card[1])
        market_list.append("random")
        market_keyboard = self.make_nested_lists(market_list, 2)
        market_keyboard.append(["Back"])
        markup = ReplyKeyboardMarkup(market_keyboard, one_time_keyboard=True)
        update.message.reply_text("You choose a card, choose another one:", reply_markup=markup)
        return MARKET

    def deck(self, update, context):
        """Show your current deck"""
        db = DatabaseSqlite3(self.url)
        deck = self.show_deck(db, update.message.chat_id)
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(deck, reply_markup=markup)
        db.close()
        return OPTIONS

    def market(self, update, context):
        """Show the market"""
        db = DatabaseSqlite3(self.url)
        response = self.show_market(db)
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        db.close()
        return OPTIONS
    
    def overview(self, update, context):
        """Shows the overview of the game"""
        db = DatabaseSqlite3(self.url)
        players = db.get_data_table("Player", [["id","name","color"]], "color IS NOT NULL")
        for player in players:
            deck = str(player[2]) + " (" + str(player[1]) + ")\n"
            deck += self.show_deck(db, update.message.chat_id, True)
            update.message.reply_text(deck)
        turn = db.get_data_table("Turn", [["chat_id"]], "playing = 1")
        if len(turn) > 0:
            player = db.get_data_table("Player", [["name","color"]], "chat_id = " + str(turn[0][0]))
            response = "Turn for " + str(player[0][1]) + " (" + str(player[0][0]) + ")"
        else:
            response = "Game hasn't started yet!"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text(response, reply_markup=markup)
        db.close()
        return OPTIONS

    def map(self, update, context):
        """send the map as a png"""
        #https://github.com/python-telegram-bot/python-telegram-bot/wiki/Code-snippets#post-an-image-file-from-disk
        response = "Not implemented yet"
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        present = False
        for board in os.listdir(os.path.join(self.path, "board")):
            if self.map_name in board:
                try:
                    picture = os.path.join(self.path, "board", board)
                    present = True
                except Exception as e:
                    logger.error(e)
        if not present:
            update.message.reply_text("Unable to find map picture!", reply_markup=markup)
        else:
            update.message.reply_photo(open(picture, 'rb'), reply_markup=markup)
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

    def next_turn_hehe(self, update, context):
        """help section"""
        db = DatabaseSqlite3(self.url)
        markup = ReplyKeyboardMarkup(option_keyboard, one_time_keyboard=True)
        update.message.reply_text("Turn done...", reply_markup=markup)
        self.next_turn(db)
        db.close()
        return OPTIONS


    def error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)


if __name__ == "__main__":
    bot = VTR_BOT("europe")