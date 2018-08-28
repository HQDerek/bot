#!/usr/bin/python
""" Main module """
import argparse
from sys import argv
from bot import HqTriviaBot
import replay
import cache
import server


class Main(object):
    """ Main class for defining command line arguments """

    def __init__(self):
        self.bot = HqTriviaBot()
        self.parser = argparse.ArgumentParser(
            usage=f'''pipenv run <command> [<args>]

Valid commands are:
   bot       {self.bot.run.__doc__}
   cache     {cache.__doc__}
   replay    {replay.__doc__}
   server    {server.__doc__}
   stats     {self.bot.get_stats.__doc__}
   token     {self.bot.generate_token.__doc__}''',
            prog='pipenv run'
        )
        self.parser.add_argument('command', help=argparse.SUPPRESS)
        args = self.parser.parse_args(argv[1:2])
        if not hasattr(self, args.command):
            self.parser.print_help()
            exit(1)

        getattr(self, args.command)()

    def run(self):
        """ Run the bot with a live game websocket """
        parser = argparse.ArgumentParser(description=self.bot.run.__doc__,
                                         prog=f'{self.parser.prog} bot')
        parser.add_argument('--test-server', help="Use local test websocket",
                            action='store_true')
        args = vars(parser.parse_args(argv[2:]))
        if args.get('test_server', '') is True:
            self.bot.api_url = 'http://localhost:8765'
        self.bot.run()

    def cache(self):
        """ Perform caching operations """
        cacher = cache.Cache()
        parser = argparse.ArgumentParser(
            prog=f'{self.parser.prog} cache',
            usage=f'''pipenv run cache <operation>

Valid cache commands are:
   prune       {cacher.prune.__doc__}
   refresh     {cacher.refresh.__doc__}
   vacuum      {cacher.vacuum.__doc__}
   import_sql  {cacher.import_sql.__doc__}
   export      {cacher.export.__doc__}
''')
        parser.add_argument('operation', help=argparse.SUPPRESS)
        args = parser.parse_args(argv[2:3])
        if not hasattr(cacher, args.operation):
            parser.print_help()
            exit(1)
        getattr(cacher, args.operation)()

    @staticmethod
    def server():
        """ Replay a game and generate report """
        game = server.Server()
        game.run()

    @staticmethod
    def replay():
        """ Replay a game and generate report """
        replayer = replay.Replayer()
        replayer.play()
        replayer.gen_report()

    def stats(self):
        """ Query play stats for a given user """
        parser = argparse.ArgumentParser(description=self.bot.get_stats.__doc__,
                                         prog=f'{self.parser.prog} stats')
        parser.add_argument('username', help="Username of the user to query")
        args = vars(parser.parse_args(argv[2:]))
        self.bot.get_stats(**args)

    def token(self):
        """ Generate an auth token for number """
        parser = argparse.ArgumentParser(description=self.bot.generate_token.__doc__,
                                         prog=f'{self.parser.prog} token')
        parser.add_argument('number', help='Number in international format e.g. +353861230000')
        args = vars(parser.parse_args(argv[2:]))
        self.bot.generate_token(**args)


if __name__ == '__main__':
    Main()
