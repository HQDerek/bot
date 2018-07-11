#!/usr/bin/python
""" Implementing a bot for HQ Trivia """
from os import path
from sys import argv
from glob import glob
from time import sleep
from sqlite3 import connect
from configparser import ConfigParser
from json import load, loads, dump, JSONDecodeError
from requests import get, post
from requests_cache import CachedSession
from websocket import WebSocketApp, WebSocketException, WebSocketTimeoutException
from utils import Colours, build_answers, predict_answers, answer_words_queries, count_results_queries, wikipedia_queries


class HqTriviaBot(object):
    """ one instance of the HQ Trivia bot"""
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.broadcast_ended = False
        self.current_game = ''

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
        self.make_it_rain(headers)
        try:
            for token in loads(self.config['Auth'].get('other_tokens', [])):
                other_headers = headers.copy()
                other_headers.update({'Authorization': 'Bearer %s' % token.get('token')})
                print("Making it rain for %s:" % token.get('name'))
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
        parsed_answers = build_answers(data.get('answers'))
        (prediction, confidence) = predict_answers(data, parsed_answers)

        # Load save game file and append question
        with open('./games/%s.json' % self.current_game) as file:
            output = load(file)
        output.get('questions').append({
            'question': data.get('question'),
            'category': data.get('category'),
            'questionId': data.get('questionId'),
            'questionNumber': data.get('questionNumber'),
            'answers': parsed_answers,
            'prediction': {
                'answer': prediction,
                'confidence': confidence
            }
        })

        # Update save game file
        with open('./games/%s.json' % self.current_game, 'w') as file:
            dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

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
        correct_string = Colours.BOLD.value + 'Correct Answer: {} - {}' + Colours.ENDC.value
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

    @staticmethod
    def on_open(_web_socket):
        """" open callback """
        print('CONNECTION SUCCESSFUL')

    @staticmethod
    def on_error(_web_socket, error):
        """" error callback """
        print('ERROR: %s' % error)

    @staticmethod
    def on_ping(web_socket, data):
        """" ping callback """
        print('RECEIVED PING: %s, SENDING PONG' % data)
        web_socket.pong(data)

    @staticmethod
    def on_close(_web_socket):
        """" close callback """
        print('SOCKET CLOSED')

    def run(self):
        """ functional loop(s) """
        while True:
            self.current_game = ''
            self.broadcast_ended = False
            headers = {
                'User-Agent': 'hq-viewer/1.2.4 (iPhone; iOS 11.1.1; Scale/3.00)',
                'Authorization': 'Bearer %s' % self.config['Auth']['bearer_token'],
                'x-hq-stk': '',
                'x-hq-client': 'Android/1.11.2',
                'x-hq-country': 'IE',
                'x-hq-lang': 'en',
                'x-hq-timezone': 'Europe/Dublin',
            }
            socket_url_uk = self.get_socket_url(headers)
            socket_url = socket_url_uk if socket_url_uk else self.get_socket_url({})
            if socket_url:
                self.make_it_rain_for_all(headers)
                print('CONNECTING TO %s SHOW: %s' % ('UK' if socket_url_uk else 'US', socket_url))
                web_socket = WebSocketApp(socket_url,
                                          on_open=self.on_open,
                                          on_message=self.on_message,
                                          on_error=self.on_error,
                                          on_close=self.on_close,
                                          header=headers)
                while not self.broadcast_ended:
                    try:
                        web_socket.run_forever(ping_interval=5)
                    except (WebSocketException, WebSocketTimeoutException):
                        print('CONNECTION LOST. RECONNECTING...')
            else:
                print('Sleeping for 2 minutes')
                sleep(120)

    @staticmethod
    def replay(arguments):
        """ replay mode """
        print("Running in Replay Mode")
        total = 0
        total_correct = 0
        orig_total_correct = 0
        for filename in glob('games/*.json'):
            if len(arguments) == 2 or (len(arguments) == 3 and filename[22:26] in arguments[2].split(',')):
                game = load(open(filename))
                print("Replaying Round %s" % game.get('showId'))
                num = 0
                num_correct = 0
                for question in game.get('questions'):
                    question['is_replay'] = True

                    (prediction, _confidence) = predict_answers(question, question.get('answers'))
                    correct = prediction == question.get('correct')
                    print('Predicted: %s, Correct: %s' % (prediction, question.get('correct')))

                    if correct:
                        print(Colours.BOLD.value + Colours.OKGREEN.value + "Correct? Yes" + Colours.ENDC.value)
                    else:
                        print(Colours.BOLD.value + Colours.FAIL.value + "Correct? No" + Colours.ENDC.value)
                    num += 1
                    num_correct += 1 if correct else 0
                total += num
                total_correct += num_correct
                orig_total_correct += game.get('numCorrect')
                print("[ORIG] Correct: %s/%s" % (game.get('numCorrect'), len(game.get('questions'))))
                print("Number Correct: %s/%s" % (num_correct, num))
        print(Colours.BOLD.value + "Replay Complete" + Colours.ENDC.value)
        print("[ORIG] Correct: %s/%s" % (orig_total_correct, total))
        print("Total Correct: %s/%s" % (total_correct, total))

    @staticmethod
    def cache(command):
        """ cache mode """
        methods = [
            {
                'name': 'answer_words_google',
                'queries': answer_words_queries,
                'session': CachedSession('db/answer_words_google', allowable_codes=(200, 302, 304))
            },
            {
                'name': 'count_results_google',
                'queries': count_results_queries,
                'session': CachedSession('db/count_results_google', allowable_codes=(200, 302, 304))
            },
            {
                'name': 'question_words_wikipedia',
                'queries': wikipedia_queries,
                'session': CachedSession('db/question_words_wikipedia', allowable_codes=(200, 302, 304))
            }
        ]
        if command == 'prune':
            for method in methods:
                cache = method['session'].cache
                urls = []
                for filename in glob('games/*.json'):
                    game = load(open(filename))
                    for turn in game.get('questions'):
                        urls.extend(method['queries'](turn.get('question'), turn.get('answers')))
                stale_entries = []
                for key, (resp, _) in cache.responses.items():
                    if resp.url not in urls and not any(step.url in urls for step in resp.history):
                        stale_entries.append((key, resp))
                print('[%s] Found %s/%s stale cache entries' % (method['name'], len(stale_entries), len(cache.responses.keys())))
                for key, resp in stale_entries:
                    print('[%s] Deleting stale entry: %s' % (method['name'], resp.url))
                    cache.delete(key)

        if command == 'refresh':
            for method in methods:
                cache = method['session'].cache
                urls = []
                for filename in glob('games/*.json'):
                    game = load(open(filename))
                    for turn in game.get('questions'):
                        urls.extend(method['queries'](turn.get('question'), turn.get('answers')))
                cache_misses = [url for url in urls if not cache.has_url(url)]
                print('[%s] Found %s/%s URLs not in cache' % (method['name'], len(cache_misses), len(urls)))
                for url in cache_misses:
                    print('[%s] Adding cached entry: %s' % (method['name'], url))
                    response = method['session'].get(url)
                    if '/sorry/index?continue=' in response.url:
                        exit('ERROR: Google rate limiting detected.')

        if command == 'vacuum':
            for method in methods:
                print('[%s] Running sqlite vacuum' % method['name'])
                conn = connect("%s.sqlite" % method['session']._cache_name)
                conn.execute("VACUUM")
                conn.close()


if __name__ == "__main__":
    BOT = HqTriviaBot()
    if len(argv) == 2 and argv[1] == "run":
        BOT.run()
    elif len(argv) == 3 and argv[1] == "cache":
        BOT.cache(argv[2])
    elif len(argv) >= 2 and argv[1] == "replay":
        BOT.replay(argv)
    else:
        print('Error: Invalid syntax. Valid commands:')
        print('hqtrivia-bot.py run')
        print('hqtrivia-bot.py replay <game-id>[,<game-id>]')
        print('hqtrivia-bot.py cache <refresh|prune|vacuum>')
