import logging
import os
import json
import requests

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

class VTR():
    def __init__(self):
        keepGoing = True
        self.json_load()
        if len(self.data["turn"]) < 1:
            self.broadcast("Welcome to the game, we're starting now!\n\nCHEW CHEW")
            for player in self.data["players"]:
                for i in range(3):
                    player["cards"].append(self.data["deck"][-1])
                    self.data["deck"] = self.data["deck"][-1:] + self.data["deck"][:-1]
                    player["routes"].append(self.data["tickets"][-1])
                    self.data["tickets"].pop()
            self.json_save()


            
            self.data["turn"] = self.data["players"][0]["color"]
            self.broadcast("It's " + self.data["players"][0]["color"] + " -> " + self.data["players"][0]["name"] + " turn")
            self.json_save()



        seq = 0
        while keepGoing:
            self.json_load()
            
            self.data["turn"] = self.data["players"][0]["color"]
            seq += 1
            if seq > 3:
                seq = 0
            self.broadcast("It's " + self.data["players"][seq]["color"] + " -> " + self.data["players"][seq]["name"] + " turn")
            self.json_save()

    def start(self, update, context):
        update.message.reply_text('Hello, \n\nWelcome to Bobbie\'s Venitian Hotel & Casino\nCome and play with us!\n\nWe are playing Ticket To Ride tonight...\nUse /add to add yourself to the game')

    def add(self, update, context):
        update.message.reply_text('Hello, \n\nWelcome to Bobbie\'s Venitian Hotel & Casino\nCome and play with us!\n\nWe are playing Ticket To Ride tonight...\nUse /add to add yourself to the game')


    def check_game(self, context):
        pass

    def broadcast(self, message):
        """Send a message to all players and spectators"""
        bot_token = ''
        for spectator in self.data["spectators"]:
            try:
                send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + str(spectator) + '&parse_mode=Markdown&text=' + message
                response = requests.get(send_text)
            except Exception as e:
                logger.error(e)

        for player in self.data["players"]:
            try:
                send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + str(player["chat_id"]) + '&parse_mode=Markdown&text=' + message
                response = requests.get(send_text)
            except Exception as e:
                logger.error(e)

    def json_load(self):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'data.json')
            with open(path, 'r') as f:
                self.data = json.load(f)
        except Exception as e:
            logger.error(e)
    
    def json_save(self):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'data.json')
            with open(path, 'w') as json_file:
                json_file.write(json.dumps(self.data, ensure_ascii=False))
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    game = VTR()
