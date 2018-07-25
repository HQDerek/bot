#!/usr/bin/python
""" Main module """
from sys import argv
from bot import HqTriviaBot
from replay import Replayer

if __name__ == "__main__":
    BOT = HqTriviaBot()
    if len(argv) == 2 and argv[1] == "run":
        BOT.run()
    elif len(argv) == 3 and argv[1] == "cache":
        BOT.cache(argv[2])
    elif len(argv) >= 2 and argv[1] == "replay":
        REPLAYER = Replayer()
        REPLAYER.play()
        REPLAYER.gen_report()
    elif len(argv) == 2 and argv[1] == "get-wins":
        BOT.get_wins(argv[2])
    elif len(argv) == 3 and argv[1] == "generate-token":
        BOT.generate_token(argv[2])
    else:
        print('Error: Invalid syntax. Valid commands:')
        print('hqtrivia-bot.py run')
        print('hqtrivia-bot.py get-wins <username>')
        print('hqtrivia-bot.py generate-token <phone>')
        print('hqtrivia-bot.py replay <game-id>[,<game-id>]')
        print('hqtrivia-bot.py cache <refresh|prune|vacuum>')
