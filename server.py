""" Websocket server that simulates live games """
import asyncio
from glob import glob
from sys import stdout
from json import load, dumps
from random import randint
from socket import gethostname, gethostbyname
from websockets import exceptions, serve
from aiohttp import web
from utils import Colours
from question import Question

SOCKET_PORT = 8765
GAME_RUNNING = False


class GameServer:
    """
    A representation of a HQTrivia Game socket server.
    Provides questions and answers to any client that connects to the socket.
    From https://github.com/freshollie/trivia-sim
    """
    PORT = 8765

    def __init__(self, game_ids):
        self.game_ids = game_ids
        self.active = False
        self._players = set()
        self._socket = None

    @staticmethod
    def generate_question_event(question, count):
        """
        Generate the question JSON response.

        :param Question question: Question object for current round
        :param int count: Total number of questions
        :return: Object representing question event
        :rtype: dict
        """
        return {"type": "question",
                "question": question.text,
                "answers": [{'text': answer} for key, answer in question.answers.items()],
                "questionNumber": question.number,
                "questionCount": count}

    @staticmethod
    def generate_round_summary_event(question):
        """
        After round is over, generate a round summary using random player counts.
        """
        answer_counts = [{
            'count': randint(0, 1000),
            'correct': (key == question.correct),
            'answer': question.answers.get(question.correct)
        } for key, answer in question.answers.items()]

        return {
            "type": "questionSummary",
            "questionId": question.id,
            "advancingPlayersCount": randint(1, 10000),
            "eliminatedPlayersCount": randint(1, 10000),
            "answerCounts": answer_counts
        }

    async def _broadcast_event(self, event):
        """
        Broadcast the given event to all connected players

        :param dict event: Event to broadcast
        """
        if self._players:
            await asyncio.wait([player.send(dumps(event)) for player in self._players])

    async def host_game(self):
        """
        Hosts a HQTrivia game on the HQTrivia game socket.
        """

        self.active = True

        game_ids = self.game_ids.split(',')
        game_files = [file for file in sorted(glob('games/*.json')) if file[22:-5] in game_ids]

        if not game_files or set(game_ids) != set([file[22:-5] for file in game_files]):
            print(f'Game ID {self.game_ids} not found.')
            exit(1)
        print(f'Playing Game IDs {game_ids}')

        for file in game_files:

            if not self._players:
                print('Waiting for players to connect...\n')
                while not self._players:
                    await asyncio.sleep(2)

            for count in reversed(range(5)):
                stdout.write(f'\rNext game in {count + 1} seconds')
                stdout.flush()
                await asyncio.sleep(1)

            quiz = load(open(file))

            stdout.write(f'\rStarting Game ID: {file[22:-5]}\n')
            stdout.flush()

            quiz_length = len(quiz['questions'])

            for question_data in quiz['questions']:
                question = Question(is_replay=True, **question_data)
                print(f'\n  Round {question.number}\n-----------')

                # Provide a question and wait for it to be answered
                print('  Question: ' + Colours.BOLD.value + question.text + Colours.ENDC.value)
                question_event = self.generate_question_event(question, quiz_length)
                await self._broadcast_event(question_event)
                for count in reversed(range(10)):
                    await asyncio.sleep(1)
                    stdout.write('\r  {} seconds'.format(count))
                    stdout.flush()

                # And then broadcast the answers
                stdout.write('\r  Answer: ' + Colours.BOLD.value +
                             f'{question.correct} - {question.answers[question.correct]}\n' +
                             Colours.ENDC.value)
                stdout.flush()
                summary_event = GameServer.generate_round_summary_event(question)
                await self._broadcast_event(summary_event)
                await asyncio.sleep(3)

        print('Games finished')
        self.active = False

    def _register_player(self, player):
        self._players.add(player)

    def _unregister_player(self, player):
        self._players.remove(player)

    async def _player_connection(self, socket, _path):
        """
        Handles players connecting to the socket and registers them for broadcasts
        """
        print('* Player connected')
        self._register_player(socket)
        try:
            # Keep listen for answers, but ignore them as they are not used.
            async for _ in socket:
                pass
        except exceptions.ConnectionClosed:
            pass
        finally:
            print('* Player disconnected')
            self._unregister_player(socket)

    async def start(self):
        """"
        Start the socket listening for player connections
        """
        self._socket = await serve(self._player_connection, "0.0.0.0", GameServer.PORT)

    async def close(self):
        """
        Drain the player connections and close the socket
        """
        if self._socket:
            self._socket.close()
            await self._socket.wait_closed()


class WebServer:
    """
    Represents the HQTrivia Web Server
    """

    PORT = "8732"

    def __init__(self, game_ids):
        self._next_game = None
        self._game_server = GameServer(game_ids)
        self._event_loop = asyncio.get_event_loop()

    @staticmethod
    def generate_next_game_info(next_show_time):
        """ Return the next show time """
        return {"nextShowTime": next_show_time, "nextShowPrize": "£1,000,000"}

    @staticmethod
    def generate_broadcast_info():
        """ Return the socket URL """
        return {"broadcast": {"socketUrl": f"ws://{Server.get_ip()}:{GameServer.PORT}"}}

    async def _serve_game_info(self, _request):
        if self._game_server.active:
            return web.json_response(WebServer.generate_broadcast_info())
        return web.json_response(WebServer.generate_next_game_info(
            self._next_game.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        ))

    async def run(self):
        """
        Create a websever and broadcast when the game will begin. Start the game when a player connects.
        """

        await self._event_loop.create_server(web.Server(self._serve_game_info), "0.0.0.0", WebServer.PORT)
        print(f'Web server started on 0.0.0.0:{WebServer.PORT}')

        await self._game_server.start()
        await self._game_server.host_game()
        await self._game_server.close()


class Server:
    """
    Server which manages the WebServer and GameServer loops
    """

    @staticmethod
    def get_ip():
        """ Get IP address of the machine """
        return gethostbyname(gethostname())

    @staticmethod
    def run(game_ids):
        """
        Create a WebServer instance and run until completion
        """
        asyncio.get_event_loop().run_until_complete(WebServer(game_ids).run())
