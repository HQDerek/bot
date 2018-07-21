#!/usr/bin/python
""" Implementing a bot for HQ Trivia """
from os import path
from sys import argv
from glob import glob
from time import sleep
from sqlite3 import connect
from configparser import ConfigParser
from json import load, loads, dump, JSONDecodeError
from requests import get, post, Request
from requests_cache import CachedSession
from websocket import WebSocketApp, WebSocketException, WebSocketTimeoutException
from utils import Colours, build_answers, predict_answers, \
    answer_words_queries, count_results_queries
from question import Question
from replay import Replayer


class HqTriviaBot(object):
    """ one instance of the HQ Trivia bot"""
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.broadcast_ended = False
        self.current_game = ''
        self.headers = {
            'User-Agent': 'hq-viewer/1.2.4 (iPhone; iOS 11.1.1; Scale/3.00)',
            'x-hq-stk': '',
            'x-hq-client': 'Android/1.11.2',
            'x-hq-country': 'IE',
            'x-hq-lang': 'en',
            'x-hq-timezone': 'Europe/Dublin',
        }
        if self.config.has_section('Auth'):
            self.headers['Authorization'] = 'Bearer %s' % self.config.get('Auth', 'bearer_token')

    def get_socket_url(self, headers):
        """ Get broadcast socket URL """
        user_id = self.config['Auth']['user_id']
        resp = get('https://api-quiz.hype.space/shows/now?type=hq&userId=%s' % user_id, headers=headers)
        try:
            initial_json = resp.json()
        except JSONDecodeError:
            return None

        # Get next show time and prize
        next_show_time = initial_json.get('nextShowTime')
        next_show_prize = initial_json.get('nextShowPrize')

        # Check if broadcast socket URL exists
        if not initial_json.get('broadcast') or not initial_json.get('broadcast').get('socketUrl'):
            print('Error: Next %s show on %s for %s.' % ('UK' if headers else 'US', next_show_time, next_show_prize))
            return None

        # Return socket URL for websocket connection
        return initial_json.get('broadcast').get('socketUrl').replace('https', 'wss')

    @staticmethod
    def make_it_rain(headers):
        """ Make it rain """
        resp = post('https://api-quiz.hype.space/easter-eggs/%s' % 'makeItRain', headers=headers)
        try:
            print('Make it rain: %s' % resp.json())
        except ValueError:
            pass

    def make_it_rain_for_all(self, headers):
        """ make it rain for me and then others"""
        try:
            for filename in sorted(glob('config*.ini')):
                config = ConfigParser()
                config.read(filename)
                other_headers = headers.copy()
                other_headers.update({'Authorization': 'Bearer %s' %  config.get('Auth', 'bearer_token')})
                print("Making it rain for %s:" % (filename.split('-')[1] if len(filename.split('-')) > 1 else 'me'))
                self.make_it_rain(other_headers)
        except TypeError:
            pass

    def game_status(self, data):
        """ status of the game """
        self.current_game = '%s-game-%s' % (data.get('ts')[:10], data.get('showId'))

        # Create new save game file if not found
        if not path.isfile('./games/%s.json' % self.current_game):
            with open('./games/%s.json' % self.current_game, 'w') as file:
                dump({
                    'showId': data.get('showId'),
                    'ts': data.get('ts'),
                    'prize': data.get('prize'),
                    'numCorrect': 0,
                    'questionCount': data.get('questionCount'),
                    'questions': [],
                }, file, ensure_ascii=False, sort_keys=True, indent=4)

    def prediction_time(self, data):
        """ build up answers and make predictions """
        data['answers'] = build_answers(data.get('answers'))
        question = Question(is_replay=False, **data)
        (prediction, confidence) = predict_answers(question)
        question.add_prediction(prediction, confidence)


    @staticmethod
    def game_summary(data):
        """" display the summary of a game """
        game_end_string = 'GAME ENDED. {} WINNERS. AVG PAYOUT {}.\n'
        print(game_end_string.format(data.get('numWinners'),
                                     next(iter(data.get('winners', [])), {}).get('prize', 'Unknown')))
        print('Top 20 Winners:')
        for winner in sorted(data.get('winners'), key=lambda k: k['wins'], reverse=True)[:20]:
            print(Colours.BOLD.value + winner.get('name') + Colours.ENDC.value + " (Wins: %s)" % winner.get('wins'))

    def on_message(self, web_socket, message):
        """ Message handler """
        data_start = message.find('{')
        if data_start >= 0:
            try:
                data = loads(message[data_start:])
                if data.get('type') == 'self.broadcast_ended' and not data.get('reason'):
                    self.broadcast_ended = True
                    print('BROADCAST ENDED.')
                    web_socket.close()
                elif data.get('type') == 'gameStatus':
                    self.game_status(data)
                elif data.get('type') == 'question' and data.get('answers'):
                    self.prediction_time(data)
                # Check for question summary
                elif data.get('type') == 'questionSummary':
                    correct_index = next((n for (n, val)
                                          in enumerate(data.get('answerCounts'))
                                          if val["correct"]))
                    correct_choice = chr(65 + correct_index) # A, B or C
                    question = Question(is_replay=False, load_id=data.get('questionId'))
                    question.add_correct(correct_choice)
                    question.display_summary()
                # Check for question summary
                elif data.get('type') == 'gameSummary':
                    self.game_summary(data)

                # Print messages to log file
                hidden_messages = ['interaction', 'broadcastStats', 'kicked']
                if data.get('type') not in hidden_messages:
                    with open('./games/messages.log', 'a') as file:
                        if data.get('type') == 'gameStatus':
                            file.write('\nNEW GAME: %s\n' % self.current_game)
                        file.write('MESSAGE: %s\n' % message)
            except JSONDecodeError:
                print('ERROR - bad json: %s' % message)

    def run(self):
        """ functional loop(s) """
        if not self.config.has_section('Auth'):
            exit('Error: Config file \'config.ini\' with [Auth] section not found. Please run generate-token.')
        while True:
            self.current_game = ''
            self.broadcast_ended = False
            socket_url_uk = self.get_socket_url(self.headers)
            socket_url = socket_url_uk if socket_url_uk else self.get_socket_url({})
            if socket_url:
                self.make_it_rain_for_all(self.headers)
                print('CONNECTING TO %s SHOW: %s' % ('UK' if socket_url_uk else 'US', socket_url))
                web_socket = WebSocketApp(socket_url,
                                          on_open=lambda _ws: print('CONNECTION SUCCESSFUL'),
                                          on_message=self.on_message,
                                          on_error=lambda _ws, err: print('ERROR: %s' % err),
                                          on_close=lambda _ws: print('SOCKET CLOSED'),
                                          header=self.headers)
                while not self.broadcast_ended:
                    try:
                        web_socket.run_forever(ping_interval=5)
                    except (WebSocketException, WebSocketTimeoutException):
                        print('CONNECTION LOST. RECONNECTING...')
            else:
                print('Sleeping for 2 minutes')
                sleep(120)

    def generate_token(self, phone):
        """ generate a JWT for a particular phone """
        unauth_headers = self.headers.copy()
        unauth_headers.pop('Authorization', None)
        phone_resp = post('https://api-quiz.hype.space/verifications', headers=unauth_headers, data={
            'method': 'sms',
            'phone': phone
        }).json()
        verification_id = phone_resp.get('verificationId')
        if not verification_id:
            print('Something went wrong. %s' % phone_resp.get('error', ''))
        else:
            print('Verification sent to %s.' % phone)
            code = input("Please enter the code: ")
            code_resp = post('https://api-quiz.hype.space/verifications/%s' % verification_id, \
                headers=unauth_headers, data={'code': code}).json()
            if not code_resp.get('auth'):
                print('Something went wrong. %s' % code_resp.get('error', ''))
            else:
                verify_file = 'config-%s-%s.ini' % (code_resp.get('auth').get('username'), code)
                with open(verify_file, 'w') as out:
                    out.write('%s\n%s\n%s' % (
                        '[Auth]',
                        'user_id = %s' % code_resp.get('auth').get('userId'),
                        'bearer_token = %s' % code_resp.get('auth').get('accessToken')
                    ))
                print('Verification successful. Details stored in %s' % verify_file)

    def get_wins(self, username):
        """ get the amount of times a specific user has won """
        resp = get('https://api-quiz.hype.space/users?q={"username":"%s"}' % username, headers=self.headers)
        try:
            json = resp.json()
            users = json.get('data', [])
            if users is not None:
                for user in users:
                    if user.get('username') == username:
                        user_id = user.get('userId')
                        resp = get('https://api-quiz.hype.space/users/%s' % user_id, headers=self.headers)
                        user = resp.json()
                        print('User:\t\t%s' % user.get('username'))
                        print('Total Earnings:\t%s' % user.get('leaderboard').get('total'))
                        print('Games Played:\t%s' % user.get('gamesPlayed'))
                        print('Wins:\t\t%s' % user.get('winCount'))
            else:
                print('%s is not a user.' % username)
        except JSONDecodeError:
            pass


    def cache(self, command):
        """ cache mode """
        session = CachedSession('db/cache', allowable_codes=(200, 302, 304))
        methods = [
            {
                'name': 'answer_words_google',
                'queries': answer_words_queries
            },
            {
                'name': 'count_results_google',
                'queries': count_results_queries
            }
        ]
        print('Running cache %s' % command)
        if command == 'prune':
            self.cache_prune(session, methods)
        elif command == 'refresh':
            self.cache_refresh(session, methods)
        elif command == 'vacuum':
            self.cache_vacuum(session, methods)
        elif command == 'import':
            self.cache_import(session, methods)
        elif command == 'export':
            self.cache_export(session, methods)

    @staticmethod
    def cache_prune(session, methods):
        """ cache prune mode """
        urls = []
        for method in methods:
            for filename in sorted(glob('games/*.json')):
                game = load(open(filename))
                for turn in game.get('questions'):
                    urls.extend(method['queries'](turn.get('question'), turn.get('answers')))
        stale_entries = []
        for key, (resp, _) in session.cache.responses.items():
            if resp.url not in urls and not any(step.url in urls for step in resp.history):
                stale_entries.append((key, resp))
        print('Found %s/%s stale entries' % (len(stale_entries), len(session.cache.responses.keys())))
        for key, resp in stale_entries:
            print('Deleting stale entry: %s' % resp.url)
            session.cache.delete(key)

    @staticmethod
    def cache_refresh(session, methods):
        """ cache refresh mode """
        urls = []
        for method in methods:
            for filename in sorted(glob('games/*.json')):
                game = load(open(filename))
                for turn in game.get('questions'):
                    urls.extend(method['queries'](turn.get('question'), turn.get('answers')))
        cache_misses = [
            url for url in urls if not session.cache.create_key(
                session.prepare_request(Request('GET', url))
            ) in session.cache.responses
        ]
        print('Found %s/%s URLs not in cache' % (len(cache_misses), len(urls)))
        for idx, url in enumerate(cache_misses):
            print('Adding cached entry: %s' % url)
            response = session.get(url)
            if '/sorry/index?continue=' in response.url:
                exit('ERROR: Google rate limiting detected. Cached %s pages.' % idx)

    @staticmethod
    def cache_vacuum(_session, _methods):
        """ cache vacuum mode """
        conn = connect("db/cache.sqlite")
        conn.execute("VACUUM")
        conn.close()

    @staticmethod
    def cache_import(_session, _methods):
        """ cache import mode """
        conn = connect("db/cache.sqlite")
        for filename in sorted(glob('db/*.sql')):
            print('Importing SQL %s' % filename)
            sql = open(filename, 'r').read()
            cur = conn.cursor()
            cur.executescript(sql)
        conn.close()

    @staticmethod
    def cache_export(session, methods):
        """ cache export mode """
        for filename in sorted(glob('games/*.json')):
            game = load(open(filename))
            show_id = path.basename(filename).split('.')[0]
            if not path.isfile('./db/%s.sql' % show_id):
                print('Exporting SQL %s' % show_id)
                urls = []
                for method in methods:
                    for turn in game.get('questions'):
                        urls.extend(method['queries'](turn.get('question'), turn.get('answers')))
                url_keys = [session.cache.create_key(session.prepare_request(Request('GET', url))) for url in urls]
                conn = connect(':memory:')
                cur = conn.cursor()
                cur.execute("attach database 'db/cache.sqlite' as cache")
                cur.execute("select sql from cache.sqlite_master where type='table' and name='urls'")
                cur.execute(cur.fetchone()[0])
                cur.execute("select sql from cache.sqlite_master where type='table' and name='responses'")
                cur.execute(cur.fetchone()[0])
                for key in list(set(url_keys)):
                    cur.execute("insert into urls select * from cache.urls where key = '%s'" % key)
                    cur.execute("insert into responses select * from cache.responses where key = '%s'" % key)
                conn.commit()
                cur.execute("detach database cache")
                with open('db/%s.sql' % show_id, 'w') as file:
                    for line in conn.iterdump():
                        file.write('%s\n' % line.replace(
                            'TABLE', 'TABLE IF NOT EXISTS'
                        ).replace(
                            'INSERT', 'INSERT OR IGNORE'
                        ))
                conn.close()




if __name__ == "__main__":
    BOT = HqTriviaBot()
    if len(argv) == 2 and argv[1] == "run":
        BOT.run()
    elif len(argv) == 3 and argv[1] == "cache":
        BOT.cache(argv[2])
    elif len(argv) >= 2 and argv[1] == "replay":
        replayer = Replayer()
        #replayer.play()
        replayer.gen_report()
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
