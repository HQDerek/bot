#!/usr/bin/python
""" Implementing a bot for HQ Trivia """
import webbrowser
from os import path
from sys import argv
from glob import glob
from time import sleep
from sqlite3 import connect
from configparser import ConfigParser
from json import load, loads, dump, JSONDecodeError
from requests import get, post, Request
from requests_cache import CachedSession
from requests_futures.sessions import FuturesSession
from websocket import WebSocketApp, WebSocketException, WebSocketTimeoutException
from solvers import GoogleAnswerWordsSolver, GoogleResultsCountSolver
from utils import Colours


class HqTriviaBot(object):
    """ one instance of the HQ Trivia bot"""
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.broadcast_ended = False
        self.current_game = ''
        self.solvers = [
            GoogleAnswerWordsSolver(),
            GoogleResultsCountSolver()
        ]
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
        if isinstance(data.get('answers'), list):
            data['answers'] = {
                'A': data.get('answers')[0]['text'],
                'B': data.get('answers')[1]['text'],
                'C': data.get('answers')[2]['text']
            }

        print('\n\n\n------------ QUESTION %s | %s ------------' %
              (data.get('questionNumber'), data.get('category')))
        print('%s\n\n------------ ANSWERS ------------\n%s\n------------------------' %
              ((Colours.BOLD.value + data.get('question') + Colours.ENDC.value), data.get('answers')))

        # Create session and open browser
        if not data.get('is_replay', False):
            session = FuturesSession(max_workers=10)
            webbrowser.open('https://www.google.co.uk/search?pws=0&q=' + data.get('question'))
        else:
            session = CachedSession('db/cache', allowable_codes=(200, 302, 304))

        # Run solvers
        responses = {}
        confidence = {'A': 0, 'B': 0, 'C': 0}
        for solver in self.solvers:
            responses[solver] = solver.fetch_responses(
                solver.build_urls(data.get('question'), data.get('answers')), session
            )
        for solver, responses in responses.items():
            (prediction, confidence) = solver.run(
                data.get('question'), data.get('answers'), responses, confidence
            )

        # Show prediction in console
        print('\nPrediction:')
        total_confidence = sum(confidence.values())
        for index, count in confidence.items():
            likelihood = int(count/total_confidence * 100) if total_confidence else 0
            confidence[index] = '%d%%' % likelihood
            result = '%sAnswer %s: %s - %s%%' % \
                ('-> ' if index == prediction else '   ', index, data.get('answers').get(index), likelihood)
            print(Colours.OKBLUE.value + Colours.BOLD.value + result + Colours.ENDC.value \
                if index == prediction else result)

        # Load save game file and append question
        if not data.get('is_replay', False):
            with open('./games/%s.json' % self.current_game) as file:
                output = load(file)
            output.get('questions').append({
                'question': data.get('question'),
                'category': data.get('category'),
                'questionId': data.get('questionId'),
                'questionNumber': data.get('questionNumber'),
                'answers': data.get('answers'),
                'prediction': {
                    'answer': prediction,
                    'confidence': confidence
                }
            })

            # Update save game file
            with open('./games/%s.json' % self.current_game, 'w') as file:
                dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

        return prediction

    def question_summary(self, data):
        """" display the summary of a question """
        # Load save game file and update correct answer
        with open('./games/%s.json' % self.current_game) as file:
            output = load(file)
        questions_output = output.get('questions')
        question_index = next((n for (n, val)
                               in enumerate(questions_output)
                               if val["questionId"] == data.get('questionId')))
        correct_index = next((n for (n, val)
                              in enumerate(data.get('answerCounts'))
                              if val["correct"]))
        correct = output['questions'][question_index]['prediction']['answer'] == chr(65 + correct_index)

        # Print results to console
        correct_string = Colours.BOLD.value + '\n\nCorrect Answer: {} - {}' + Colours.ENDC.value
        print(correct_string.format(chr(65 + correct_index),
                                    output['questions'][question_index]['answers'][chr(65 + correct_index)]))
        if correct:
            print(Colours.BOLD.value + Colours.OKGREEN.value + "Prediction Correct? Yes" + Colours.ENDC.value)
        else:
            print(Colours.BOLD.value + Colours.FAIL.value + "Prediction Correct? No" + Colours.ENDC.value)

        # Set correct answer in question object
        output['questions'][question_index]['correct'] = chr(65 + correct_index)
        output['numCorrect'] += 1 if correct else 0

        # Update save game file
        with open('./games/%s.json' % self.current_game, 'w') as file:
            dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

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
                    self.question_summary(data)
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
        """
        generate a JWT for a particular phone
        phone should be in a format such as '+353861234567'
        """
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

    def replay(self, arguments):
        """ replay mode """
        print("Running in Replay Mode")
        total = 0
        total_correct = 0
        orig_total_correct = 0

        for filename in sorted(glob('games/*.json')):
            if len(arguments) == 2 or (len(arguments) == 3 and filename[22:26] in arguments[2].split(',')):
                game = load(open(filename))
                print("Replaying Round %s" % game.get('showId'))
                num = 0
                num_correct = 0

                for data in game.get('questions'):
                    data['is_replay'] = True
                    prediction = self.prediction_time(data)
                    correct = prediction == data.get('correct')
                    num += 1
                    num_correct += 1 if correct else 0

                    # Print results to console
                    correct_string = Colours.BOLD.value + '\n\nCorrect Answer: {} - {}' + Colours.ENDC.value
                    print(correct_string.format(data.get('correct'), data.get('answers').get(data.get('correct'))))
                    if correct:
                        print(Colours.BOLD.value + Colours.OKGREEN.value + \
                            "Prediction Correct? Yes" + Colours.ENDC.value)
                    else:
                        print(Colours.BOLD.value + Colours.FAIL.value + \
                            "Prediction Correct? No" + Colours.ENDC.value)

                total += num
                total_correct += num_correct
                orig_total_correct += game.get('numCorrect')
                print("[ORIG] Correct: %s/%s" % (game.get('numCorrect'), len(game.get('questions'))))
                print("Number Correct: %s/%s" % (num_correct, num))

        print(Colours.BOLD.value + "Replay Complete" + Colours.ENDC.value)
        print("[ORIG] Correct: %s/%s" % (orig_total_correct, total))
        print("Total Correct: %s/%s" % (total_correct, total))

    def cache(self, command):
        """ cache mode """
        session = CachedSession('db/cache', allowable_codes=(200, 302, 304))
        solvers = [
            GoogleAnswerWordsSolver(),
            GoogleResultsCountSolver()
        ]
        print('Running cache %s' % command)
        if command == 'prune':
            self.cache_prune(session, solvers)
        elif command == 'refresh':
            self.cache_refresh(session, solvers)
        elif command == 'vacuum':
            self.cache_vacuum(session, solvers)
        elif command == 'import':
            self.cache_import(session, solvers)
        elif command == 'export':
            self.cache_export(session, solvers)

    @staticmethod
    def cache_prune(session, solvers):
        """ cache prune mode """
        urls = []
        for solver in solvers:
            for filename in sorted(glob('games/*.json')):
                game = load(open(filename))
                for turn in game.get('questions'):
                    urls.extend(solver.build_urls(turn.get('question'), turn.get('answers')))
        stale_entries = []
        for key, (resp, _) in session.cache.responses.items():
            if resp.url not in urls and not any(step.url in urls for step in resp.history):
                stale_entries.append((key, resp))
        print('Found %s/%s stale entries' % (len(stale_entries), len(session.cache.responses.keys())))
        for key, resp in stale_entries:
            print('Deleting stale entry: %s' % resp.url)
            session.cache.delete(key)

    @staticmethod
    def cache_refresh(session, solvers):
        """ cache refresh mode """
        urls = []
        for solver in solvers:
            for filename in sorted(glob('games/*.json')):
                game = load(open(filename))
                for turn in game.get('questions'):
                    urls.extend(solver.build_urls(turn.get('question'), turn.get('answers')))
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
    def cache_vacuum(_session, _solvers):
        """ cache vacuum mode """
        conn = connect("db/cache.sqlite")
        conn.execute("VACUUM")
        conn.close()

    @staticmethod
    def cache_import(_session, _solvers):
        """ cache import mode """
        conn = connect("db/cache.sqlite")
        for filename in sorted(glob('db/*.sql')):
            print('Importing SQL %s' % filename)
            sql = open(filename, 'r').read()
            cur = conn.cursor()
            cur.executescript(sql)
        conn.close()

    @staticmethod
    def cache_export(session, solvers):
        """ cache export mode """
        for filename in sorted(glob('games/*.json')):
            game = load(open(filename))
            show_id = path.basename(filename).split('.')[0]
            if not path.isfile('./db/%s.sql' % show_id):
                print('Exporting SQL %s' % show_id)
                urls = []
                for solver in solvers:
                    for turn in game.get('questions'):
                        urls.extend(solver.build_urls(turn.get('question'), turn.get('answers')))
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
        BOT.replay(argv)
    elif len(argv) == 3 and argv[1] == "get-wins":
        BOT.get_wins(argv[2])
    elif len(argv) == 3 and argv[1] == "generate-token":
        BOT.generate_token(argv[2])
    else:
        print('Error: Invalid syntax. Valid commands:')
        print('hqtrivia_bot.py run')
        print('hqtrivia_bot.py get-wins <username>')
        print('hqtrivia_bot.py generate-token <phone>')
        print('hqtrivia_bot.py replay <game-id>[,<game-id>]')
        print('hqtrivia_bot.py cache <refresh|prune|vacuum>')
