import os
import json
import logging
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

def start(update, context):
    update.message.reply_text('Hello, \n\nWelcome to Bobbie\'s Venitian Hotel & Casino\nCome and play with us!\n\nWe are playing Ticket To Ride tonight...\nUse /add and a color to add yourself to the game!\nPress /help to show the menu\n\nYou are now a spectator!')
    chat_id = update.message.chat_id
    data = json_load()
    data["spectators"].append(chat_id)
    json_save(data)
    available_player_colors = []
    for player in data["players"]:
        if player["chat_id"] < 1:
            available_player_colors.append(player["color"])

    update.message.reply_text("Available player colors are: " + str(available_player_colors))

def restart(update, context):
    """Restart the game"""
    pass

def pick(update, context):
    """Pick a cart"""
    pass

def route(update, context):
    """Create a route"""
    pass

def add(update, context):
    color = context.args[0]
    data = json_load()
    present = False
    for player in data["players"]:
        if color in player["color"]:
            if player["chat_id"] < 1:
                player["chat_id"] = update.message.chat_id
                player["name"] = update.message.from_user.first_name
                update.message.reply_text('You are assigned to player color: ' + player["color"])
                data["spectators"] = [x for x in data["spectators"] if x != update.message.chat_id]
            else:
                update.message.reply_text('Somebody else is already assigned to this color, please choose another one!')
            present = True
    if not present:
        update.message.reply_text('The provided color:' + color + ' is not available!')

    json_save(data)

def deck(update, context):
    """Get your deck"""
    data = json_load()
    response = ""

    for player in data["players"]:
        if update.message.chat_id == player["chat_id"]:
            response += "tickets:\n"
            for ticket in player["routes"]:
                response += ticket["city1"] + " - " + ticket["city2"] + " " + str(ticket["value"]) + "\n"

            response += "\ntrain cards: \n"
            for card in player["cards"]:
                response += card + "\n"

            response += "\n"
            if player["stations"][0] in "unknown":
                response += "No stations build yet!"
            elif player["stations"][1] in "unknown":
                response += "One station build in " + player["stations"][0] + "\n"
            elif player["stations"][2] in "unknown":
                response += "Two station build in " + player["stations"][0] + ","+ player["stations"][1] + "\n"
            else:
                response += "All stations build in: " + player["stations"][0] + ","+ player["stations"][1] + ","+ player["stations"][2] + "\n"
            
            response += "\nTrains left: " + str(player["trains"])
            
    update.message.reply_text(response)

def market(update, context):
    """Get the marketplace"""
    data = json_load()
    response = ""
    for i,card in enumerate(data["market"]):
        response += str(i+1) + " " + card + "\n"

    update.message.reply_text(response)

def routes(update, context):
    """Get all routes"""
    data = json_load()
    response = ""

    i = 0
    for route in data["routes"]:
        if i > 20:
            update.message.reply_text(response)
            response = ""
            i = 0

        i += 1
        response += route["city1"] + " - " + route["city2"] + " "
        if len(route["player"]) < 1:
            response += "open "
        else:
            response += route["player"] + " "
        response += "distance: " + str(route["distance"]) + " color: " + route["color"]
        if route["tunnel"]:
            response += " tunnel"

        if route["locomotives"] > 0:
            response += " locomotives: " + str(route["locomotives"])
        
        response += "\n"

    update.message.reply_text(response)

def yroutes(update, context):
    """Get your routes"""
    data = json_load()
    response = "routes:\n"

    for player in data["players"]:
        if update.message.chat_id == player["chat_id"]:
            color = player['color']
    
    for route in data["routes"]:
        if color in route["player"]:
            response += route["city1"] + " - " + route["city2"] + " "
            response += "distance: " + str(route["distance"]) + " color: " + route["color"] + "\n"

    update.message.reply_text(response)

def aroutes(update, context):
    """Get available routes"""
    data = json_load()
    response = ""
    data = json_load()
    response = ""

    i = 0
    for route in data["routes"]:
        if len(route["player"]) < 1:
            if i > 20:
                update.message.reply_text(response)
                response = ""
                i = 0

            i += 1
            response += route["city1"] + " - " + route["city2"] + " "
            response += "distance: " + str(route["distance"]) + " color: " + route["color"]
            if route["tunnel"]:
                response += " tunnel"

            if route["locomotives"] > 0:
                response += " locomotives: " + str(route["locomotives"])
            
            response += "\n"

    update.message.reply_text(response)

def lroute(update, context):
    """Get the longest Route"""
    update.message.reply_text("To Be Implemented!!!")

def overview(update, context):
    """Get the game overview"""
    data = json_load()
    for player in data["players"]:
        response = ""

        response += player["color"] + " - " + player["name"] + "\n"
        response += "cards: " + str(len(player["cards"])) + "\n"
        response += "tickets: " + str(len(player["routes"])) + "\n"
        response += "trains left: " + str((player["trains"])) + "\n"
        if player["stations"][0] in "unknown":
            response += "No stations build yet!"
        elif player["stations"][1] in "unknown":
            response += "One station build in " + player["stations"][0] + "\n"
        elif player["stations"][2] in "unknown":
            response += "Two station build in " + player["stations"][0] + ","+ player["stations"][1] + "\n"
        else:
            response += "All stations build in: " + player["stations"][0] + ","+ player["stations"][1] + ","+ player["stations"][2] + "\n"
        response += "\nroutes:\n"

        for route in data["routes"]:
            if player["color"] in route["player"]:
                response += route["city1"] + " - " + route["city2"] + " "
                response += "distance: " + str(route["distance"]) + " color: " + route["color"]
                if route["tunnel"]:
                    response += " tunnel"

                if route["locomotives"] > 0:
                    response += " locomotives: " + str(route["locomotives"])
                
                response += "\n"

        update.message.reply_text(response)

def player(update, context):
    """Get player information"""
    color = context.args[0]
    data = json_load()
    found = True
    for player in data["players"]:
        if player["color"] in color:
            response = ""

            response += player["color"] + " - " + player["name"] + "\n"
            response += "cards: " + str(len(player["cards"])) + "\n"
            response += "tickets: " + str(len(player["routes"])) + "\n"
            response += "trains left: " + str(player["trains"]) + "\n"
            if player["stations"][0] in "unknown":
                response += "No stations build yet!"
            elif player["stations"][1] in "unknown":
                response += "One station build in " + player["stations"][0] + "\n"
            elif player["stations"][2] in "unknown":
                response += "Two station build in " + player["stations"][0] + ","+ player["stations"][1] + "\n"
            else:
                response += "All stations build in: " + player["stations"][0] + ","+ player["stations"][1] + ","+ player["stations"][2] + "\n"
            response += "\nroutes:\n"

            for route in data["routes"]:
                if player["color"] in route["player"]:
                    response += route["city1"] + " - " + route["city2"] + " "
                    response += "distance: " + str(route["distance"]) + " color: " + route["color"]
                    if route["tunnel"]:
                        response += " tunnel"

                    if route["locomotives"] > 0:
                        response += " locomotives: " + str(route["locomotives"])
                    
                    response += "\n"

            update.message.reply_text(response)
    
    if not found:
        update.message.reply_text("Player was not found!!!")

def points(update, context):
    update.message.reply_text("To Be Implemented!!!")

def city(update, context):
    """Get city details"""
    city = context.args[0]
    data = json_load()
    
    response = "routes in this city:\n"
    i = 0
    for route in data["routes"]:
        if city in route["city1"] or city in route["city2"]:
            i += 1
            response += route["city1"] + " - " + route["city2"] + " "
            if len(route["player"]) < 1:
                response += "open "
            else:
                response += route["player"] + " "
            response += "distance: " + str(route["distance"]) + " color: " + route["color"]
            if route["tunnel"]:
                response += " tunnel"

            if route["locomotives"] > 0:
                response += " locomotives: " + str(route["locomotives"])
            
            response += "\n"
        
    if i < 1:
        update.message.reply_text("City is unknown!")
    else:
        build = False
        for player in data["players"]:
            if city in player["stations"]:
                build = True
                response += "Station build for player: " + player["color"]
        if not build:
            response += "No station build in this city yet."
    update.message.reply_text(response)

def help(update, context):
    """Help section"""
    response = "HELP\n\n"
    response += "/add\tAdd yourself to the game, example /add green\n"
    response += "/deck\tGet your deck information\n"
    response += "/market\tGet the market\n"
    response += "/routes\tGet all routes\n"
    response += "/yroutes\tGet your routes\n"
    response += "/aroutes\tGet the available routes\n"
    response += "/lroute\tGet player with longest route\n"
    response += "/overview\tGet an overview of the game\n"
    response += "/player\tGet information about a player, example: /player green\n"
    response += "/points\tGet the points overview\n"
    response += "/city\tGet information about the city, example: /city London\n"
    update.message.reply_text(response)

def get_player(data, id):
    p = None
    for player in data["players"]:
        if id == player["chat_id"]:
            p = player
    return p

def json_load():
    data = {}
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'data.json')
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(e)
    
    return data

def json_save(data):
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'data.json')
        with open(path, 'w') as json_file:
            json_file.write(json.dumps(data, ensure_ascii=False))
    except Exception as e:
        logger.error(e)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    updater = Updater("", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add))
    dp.add_handler(CommandHandler("deck", deck))
    dp.add_handler(CommandHandler("market", market))
    dp.add_handler(CommandHandler("routes", routes))
    dp.add_handler(CommandHandler("yroutes", yroutes))
    dp.add_handler(CommandHandler("aroutes", aroutes))
    dp.add_handler(CommandHandler("lroute", lroute))
    dp.add_handler(CommandHandler("overview", overview))
    dp.add_handler(CommandHandler("player", player))
    dp.add_handler(CommandHandler("points", points))
    dp.add_handler(CommandHandler("city", city))
    dp.add_handler(CommandHandler("help", help))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()