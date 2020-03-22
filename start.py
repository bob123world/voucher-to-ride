import os
import json
import random

def main(numplay, game):
    data = {}

    # Insert players
    data["spectators"] = []
    data["players"] = []
    data["sequence"] = []
    players = json_load("pieces", game)
    for i, player in enumerate(players):
        if i < numplay:
            player["name"] = ""
            player["chat_id"] = 0
            player["cards"] = ""
            player["points"] = 0
            player["stations"] = ["unknown","unknown","unknown"]
            data["players"].append(player)
            data["sequence"].append(player["color"])

    data["turn"] = data["players"][0]["color"]

    # Insert cards
    cards = json_load("train_cards", game)
    data["deck"] = create_shuffle_cards(cards)

    data["market"] = []
    for i in range(0,5):
        data["market"].append(data["deck"][-1])
        data["deck"].pop()
    
    # Routes
    routes = json_load("route_cards", game)
    data["tickets"] = shuffle_routes(routes["normal"])
    long_routes = shuffle_routes(routes["special"])
    for player in players:
        player["routes"] = []
        player["routes"].append(long_routes[-1])
        long_routes.pop()

    # Routes
    data["routes"] = []
    routes = json_load("maps", game)
    for route in routes["connections"]:
        route["player"] = ""
        data["routes"].append(route)

    json_save(data)

def create_shuffle_cards(cards):
    deck =  []
    for card in cards:
        for i in range(1,card["cards"]):
            deck.append(card["color"])
    random.shuffle(deck)
    return deck

def shuffle_routes(cards):
    random.shuffle(cards)
    return cards

def json_load(path, game):
    dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    for filename in os.listdir(dir):
        if game in filename:
            try:
                with open(os.path.join(path, filename), 'r') as f:
                    data = json.load(f)
            except Exception as e:
                print(e)
    return data

def json_save(data):
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'data.json')
        with open(path, 'w') as json_file:
            json_file.write(json.dumps(data, ensure_ascii=False))
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main(4, "europe")