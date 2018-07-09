#!/usr/bin/python
import os
import sys
import json
import time
import glob
import configparser
import websocket
import requests
import utils
from compare import main as compare_main

# Read config from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Set global variables
USER_ID = config['Auth']['user_id']
BEARER_TOKEN = config['Auth']['bearer_token']
HEADERS = {
    'User-Agent': 'hq-viewer/1.2.4 (iPhone; iOS 11.1.1; Scale/3.00)',
    'Authorization': 'Bearer %s' % BEARER_TOKEN,
    'x-hq-stk': '',
    'x-hq-client': 'Android/1.11.2',
    'x-hq-country': 'IE',
    'x-hq-lang': 'en',
    'x-hq-timezone': 'Europe/Dublin',
}
broadcastEnded = False
currentGame = ''


# Get broadcast socket URL
def get_socket_url(headers):
    resp = requests.get('https://api-quiz.hype.space/shows/now?type=hq&userId=%s' % USER_ID, headers=headers)
    try:
        json = resp.json()
    except Exception:
        return None

    # Get next show time and prize
    nextShowTime = json.get('nextShowTime')
    nextShowPrize = json.get('nextShowPrize')

    # Check if broadcast socket URL exists
    if  not json.get('broadcast') or not json.get('broadcast').get('socketUrl'):
        print('Error: Next %s show on %s for %s.' % ('UK' if headers else 'US', nextShowTime, nextShowPrize))
        return None

    # Return socket URL for websocket connection
    return json.get('broadcast').get('socketUrl').replace('https', 'wss')


# Make it rain
def make_it_rain(headers):
    resp = requests.post('https://api-quiz.hype.space/easter-eggs/%s' % 'makeItRain', headers=headers)
    try:
        json = resp.json()
        print('Make it rain: %s' % json)
    except Exception:
        return None


# Message handler
def on_message(ws, message):
    global currentGame, broadcastEnded

    # Decode JSON data
    data_start = message.find('{')
    if data_start >= 0:
        try:
            data = json.loads(message[data_start:])
        except:
            print('ERROR - bad json: %s' % message)

        # Check for broadcast ended
        if data.get('type') == 'broadcastEnded' and not data.get('reason'):
            broadcastEnded = True
            print('BROADCAST ENDED.')
            ws.close()

        # Check for game status message
        elif data.get('type') == 'gameStatus':
            currentGame = '%s-game-%s' % (data.get('ts')[:10], data.get('showId'))

            # Create new save game file if not found
            if not os.path.isfile('./games/%s.json' % currentGame):
                with open('./games/%s.json' % currentGame, 'w') as file:
                    json.dump({
                        'showId': data.get('showId'),
                        'ts': data.get('ts'),
                        'prize': data.get('prize'),
                        'numCorrect': 0,
                        'questionCount': data.get('questionCount'),
                        'questions': [],
                    }, file, ensure_ascii=False, sort_keys=True, indent=4)

        # Check for question
        elif data.get('type') == 'question' and data.get('answers'):
            parsed_answers = utils.build_answers(data.get('answers'))
            (prediction, confidence) = utils.predict_answers(data, parsed_answers)

            # Load save game file and append question
            with open('./games/%s.json' % currentGame) as file:
                output = json.load(file)
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
            with open('./games/%s.json' % currentGame, 'w') as file:
                json.dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

        # Check for question summary
        elif data.get('type') == 'questionSummary':

            # Load save game file and update correct answer
            with open('./games/%s.json' % currentGame) as file:
                output = json.load(file)
            questions_output = output.get('questions')
            question_index = next((n for (n, val) in enumerate(questions_output) if val["questionId"] == data.get('questionId')))
            correct_index = next((n for (n, val) in enumerate(data.get('answerCounts')) if val["correct"]))
            prediction_correct = output['questions'][question_index]['prediction']['answer'] == chr(65 + correct_index)

            # Print results to console
            print(utils.Colours.BOLD + ('Correct Answer: %s - %s' % (chr(65 + correct_index), output['questions'][question_index]['answers'][chr(65 + correct_index)])) + utils.Colours.ENDC)
            if prediction_correct:
                print(utils.Colours.BOLD + utils.Colours.OKGREEN + "Prediction Correct? Yes" + utils.Colours.ENDC)
            else:
                print(utils.Colours.BOLD + utils.Colours.FAIL + "Prediction Correct? No" + utils.Colours.ENDC)

            # Set correct answer in question object
            output['questions'][question_index]['correct'] = chr(65 + correct_index)
            output['numCorrect'] += 1 if prediction_correct else 0

            # Update save game file
            with open('./games/%s.json' % currentGame, 'w') as file:
                json.dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

        # Check for question summary
        elif data.get('type') == 'gameSummary':

            print('GAME ENDED. %s WINNERS. AVG PAYOUT %s.\n' % (data.get('numWinners'), next(iter(data.get('winners', [])), {}).get('prize', 'Unknown')))

            # Print results to console
            print('Top 20 Winners:')
            for winner in sorted(data.get('winners'), key=lambda k: k['wins'], reverse=True)[:20]:
                print(utils.Colours.BOLD + winner.get('name') + utils.Colours.ENDC + " (Wins: %s)" % winner.get('wins'))

        # Print messages to log file
        hidden_messages = ['interaction', 'broadcastStats', 'kicked']
        if data.get('type') not in hidden_messages:
            with open('./games/messages.log', 'a') as file:
                if data.get('type') == 'gameStatus':
                    file.write('\nNEW GAME: %s\n' % currentGame)
                file.write('MESSAGE: %s\n' % message)


def on_open(_ws):
    print('CONNECTION SUCCESSFUL')


def on_error(_ws, error):
    print('ERROR: %s' % error)


def on_ping(ws, data):
    print('RECEIVED PING: %s, SENDING PONG' % data)
    ws.pong(data)


def on_close(_ws):
    print('SOCKET CLOSED')


if __name__ == "__main__":
    if len(sys.argv) == 1:
        while True:
            currentGame = ''
            broadcastEnded = False
            socket_url_uk = get_socket_url(HEADERS)
            socket_url = socket_url_uk if socket_url_uk else get_socket_url({})
            if socket_url:
                # Make it rain for me
                print("Making it rain for me:")
                make_it_rain(HEADERS)

                # Make it rain for others
                for token in json.loads(config['Auth'].get('other_tokens', [])):
                    other_headers = HEADERS.copy()
                    other_headers.update({'Authorization':'Bearer %s' % token.get('token')})
                    print("Making it rain for %s:" % token.get('name'))
                    make_it_rain(other_headers)

                print('CONNECTING TO %s SHOW: %s' % ('UK' if socket_url_uk else 'US', socket_url))
                ws = websocket.WebSocketApp(socket_url,
                                            on_open=on_open,
                                            on_message=on_message,
                                            on_error=on_error,
                                            on_close=on_close,
                                            header=HEADERS)
                while not broadcastEnded:
                    try:
                        ws.run_forever(ping_interval=5)
                    except:
                        print('CONNECTION LOST. RECONNECTING...')
            else:
                print('Sleeping for 2 minutes')
                time.sleep(120)
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "test":
        print("Running in Test Mode")
        path = 'games/*.json'
        total = 0
        total_correct = 0
        orig_total_correct = 0
        for filename in glob.glob(path):
            if len(sys.argv) == 2 or (len(sys.argv) == 3 and filename[22:26] in sys.argv[2].split(',')):
                game = json.load(open(filename))
                print("Testing Round %s" % game.get('showId'))
                num = 0
                num_correct = 0
                for q in game.get('questions'):
                    q['is_testing'] = True

                    (prediction, confidence) = utils.predict_answers(q, q.get('answers'))
                    prediction_correct = prediction == q.get('correct')
                    print('Predicted: %s, Correct: %s' % (prediction, q.get('correct')))

                    if prediction_correct:
                        print(utils.Colours.BOLD + utils.Colours.OKGREEN + "Correct? Yes" + utils.Colours.ENDC)
                    else:
                        print(utils.Colours.BOLD + utils.Colours.FAIL + "Correct? No" + utils.Colours.ENDC)
                    num += 1
                    num_correct += 1 if prediction_correct else 0
                total += num
                total_correct += num_correct
                orig_total_correct += game.get('numCorrect')
                print("[ORIG] Correct: %s/%s" % (game.get('numCorrect'), len(game.get('questions'))))
                print("Number Correct: %s/%s" % (num_correct, num))
        print(utils.Colours.BOLD + "Testing Complete" + utils.Colours.ENDC)
        print("[ORIG] Correct: %s/%s" % (orig_total_correct, total))
        print("Total Correct: %s/%s" % (total_correct, total))
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "compare":
        compare_main(sys.argv)
    else:
        print('Error: Syntax is ./hqtrivia-bot.py [test] [<game-id>]')
