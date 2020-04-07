import os
import json
import random

def main(numplay, game):
    data = {}

    # Insert players
    data["spectators"] = []
    data["players"] = []
    data["sequence"] = []

    # Insert cards
    cards = json_load("train_cards", game)
    cards_deck = create_shuffle_cards(cards)

    players = json_load("pieces", game)
    for i, player in enumerate(players):
        if i < numplay:
            player["name"] = ""
            player["chat_id"] = 0
            cards_deck, cards_player = assign_cards(cards_deck, 4)
            player["cards"] = cards_player
            player["points"] = 0
            player["stations"] = ["unknown","unknown","unknown"]
            data["players"].append(player)
            data["sequence"].append(player["color"])

    data["turn"] = data["players"][0]["color"]

    data["market"] = []
    for i in range(0,5):
        cards_deck, cards_market = assign_cards(cards_deck, 5)
        data["market"] = cards_market
    
    data["deck"] = cards_deck

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
    map_data = json_load("maps", game)
    for route in map_data["connections"]:
        route["player"] = ""
        data["routes"].append(route)

    # Add cities and do check
    data["cities"] = map_data["cities"]
    check = []
    for route in map_data["connections"]:
        check.append(route["city1"])
        check.append(route["city2"])

    check = set(check)
    check = list(check)

    data["cities"].sort()
    check.sort()
    print(str(data["cities"]))
    print(str(check))
    if set(data["cities"]) == set(check):
        print("Length of cities in routes matches")
    else:
        print("something went wrong in the cities section")

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

def assign_cards(cards, amount):
    assigned_cards = []
    for i in range(0, amount):
        assigned_cards.append(cards[-1])
        cards = cards[1:] + cards[:1]
    return cards, assigned_cards

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
    main(3, "europe")