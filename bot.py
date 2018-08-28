""" Bot module where main game actions are performed """
import webbrowser
from os import path
from glob import glob
from time import sleep
from datetime import datetime
from configparser import ConfigParser
from json import loads, dump, JSONDecodeError
from pytz import utc
from dateutil import parser
from requests import get, post
from requests_cache import CachedSession
from requests_futures.sessions import FuturesSession
from websocket import WebSocketApp, WebSocketException, WebSocketTimeoutException
from solvers import GoogleAnswerWordsSolver, GoogleResultsCountSolver
from utils import Colours
from question import Question


class HqTriviaBot(object):
    """ one instance of the HQ Trivia bot"""

    api_url = 'https://api-quiz.hype.space'

    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.broadcast_ended = False
        self.current_game = ''
        self.solvers = [
            GoogleAnswerWordsSolver(),
            GoogleResultsCountSolver()
        ]
        self.next_show_time = None
        self.next_show_prize = None
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
        resp = get(self.api_url + '/shows/now?type=hq&userId=%s' % self.config['Auth']['user_id'], headers=headers)
        try:
            initial_json = resp.json()
        except JSONDecodeError:
            return None

        # Get next show time and prize
        self.next_show_time = initial_json.get('nextShowTime')
        self.next_show_prize = initial_json.get('nextShowPrize')

        # Check if broadcast socket URL exists
        if not initial_json.get('broadcast') or not initial_json.get('broadcast').get('socketUrl'):
            print('Error: Next UK show on %s for %s.' % (self.next_show_time, self.next_show_prize))
            return None

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
                other_headers.update({'Authorization': 'Bearer %s' % config.get('Auth', 'bearer_token')})
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

    def prediction_time(self, question):
        """ Predict a question objects answer using Solver instances """
        print('\n\n\n------------ QUESTION %s | %s ------------' %
              (question.number, question.category))
        print('%s\n\n------------ ANSWERS ------------\n%s\n------------------------' %
              ((Colours.BOLD.value + question.text + Colours.ENDC.value), question.answers))

        # Create session and open browser
        if not question.is_replay:
            session = FuturesSession(max_workers=10)
            webbrowser.open('https://www.google.co.uk/search?pws=0&q=' + question.text)
        else:
            session = CachedSession('db/cache', allowable_codes=(200, 302, 304))

        # Run solvers
        responses = {}
        prediction = None
        confidence = {'A': 0, 'B': 0, 'C': 0}
        for solver in self.solvers:
            responses[solver] = solver.fetch_responses(
                solver.build_urls(question.text, question.answers), session
            )
        for solver, responses in responses.items():
            (prediction, confidence) = solver.run(
                question.text, question.answers, responses, confidence
            )

        # calculate confidences as percentage and add to q
        total_confidence = sum(confidence.values())
        for answer_key, count in confidence.items():
            likelihood = int(count/total_confidence * 100) if total_confidence else 0
            confidence[answer_key] = '%d%%' % likelihood
        question.add_prediction(prediction, confidence)

        # Show prediction in console
        print('\nPrediction:')
        for answer_key in sorted(confidence.keys()):
            result = '%sAnswer %s: %s - %s' % ('-> ' if answer_key == prediction else '   ',
                                                 answer_key,
                                                 question.answers.get(answer_key),
                                                 confidence[answer_key])
            print(Colours.OKBLUE.value + Colours.BOLD.value + result + Colours.ENDC.value
                  if answer_key == prediction else result)

        return prediction

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
                    if isinstance(data.get('answers'), list):
                        data['answers'] = {
                            'A': data.get('answers')[0]['text'],
                            'B': data.get('answers')[1]['text'],
                            'C': data.get('answers')[2]['text']
                        }
                    question = Question(is_replay=False, **data)
                    self.prediction_time(question)
                # Check for question summary
                elif data.get('type') == 'questionSummary':
                    correct_index = next((n for (n, val)
                                          in enumerate(data.get('answerCounts'))
                                          if val["correct"]))
                    correct_choice = chr(65 + correct_index)  # A, B or C
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
        """ Run the bot with a live game websocket """
        if not self.config.has_section('Auth'):
            exit('Error: Config file \'config.ini\' with [Auth] section not found. Please run generate-token.')
        while True:
            self.current_game = ''
            self.broadcast_ended = False
            socket_url = self.get_socket_url(self.headers)
            if socket_url:
                print('CONNECTING TO UK SHOW: %s' % socket_url)
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
            elif self.next_show_time:
                next_show_time = parser.parse(self.next_show_time)
                seconds_until_show = (next_show_time - datetime.now(utc)).total_seconds()
                if seconds_until_show < 0:
                    print('\nGame should have started. Sleeping for 10 seconds.')
                    sleep(10)
                else:
                    print('\nSleeping until {} ({} seconds)'.format(next_show_time.strftime('%c'), seconds_until_show))
                    sleep(seconds_until_show)
            else:
                print('Could not connect to API. Sleeping for 10 seconds.')
                sleep(10)

    def generate_token(self, number):
        """ Generate an auth token for number """
        unauth_headers = self.headers.copy()
        unauth_headers.pop('Authorization', None)
        phone_resp = post('https://api-quiz.hype.space/verifications', headers=unauth_headers, data={
            'method': 'sms',
            'phone': number
        }).json()
        verification_id = phone_resp.get('verificationId')
        if not verification_id:
            print('Something went wrong. %s' % phone_resp.get('error', ''))
        else:
            print('Verification sent to %s.' % number)
            code = input("Please enter the code: ")
            code_resp = post('https://api-quiz.hype.space/verifications/%s' % verification_id,
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

    def get_stats(self, username):
        """ Query play stats for a given user """
        resp = get(f'https://api-quiz.hype.space/users?q={username}', headers=self.headers)
        try:
            json = resp.json()
            user_id = None
            users = json.get('data', [])
            if users is not None:
                for user in users:
                    if user.get('username') == username:
                        user_id = user.get('userId')
                        user = get('https://api-quiz.hype.space/users/{}'.format(user_id), headers=self.headers).json()
                        print('User:\t\t{}'.format(user.get('username')))
                        print('Total Earnings:\t{}'.format(user.get('leaderboard').get('total')))
                        print('Games Played:\t{}'.format(user.get('gamesPlayed')))
                        print('Wins:\t\t{}'.format(user.get('winCount')))
                if not user_id:
                    print('%s is not a user.' % username)
            else:
                print('%s is not a user.' % username)
        except JSONDecodeError:
            pass
