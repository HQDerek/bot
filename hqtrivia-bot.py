#!/usr/bin/python
import os
import sys
import json
import websocket
import grequests
import requests
import utils

USER_ID = '***REMOVED***'
BEARER_TOKEN = '***REMOVED***'
HEADERS = {
    'User-Agent'    : 'hq-viewer/1.2.4 (iPhone; iOS 11.1.1; Scale/3.00)',
    'Authorization' : 'Bearer %s' % BEARER_TOKEN,
    'x-hq-stk'      : 'Mg==',
    'x-hq-client'   : 'Android/1.2.0',
}
broadcastEnded = False
currentGame = ''

# Get broadcast socket URL
def get_socket_url():
    resp = requests.get('https://api-quiz.hype.space/shows/now?type=hq&userId=%s' % USER_ID, headers=HEADERS)
    json = resp.json()

    # Get next show time and prize
    nextShowTime = json.get('nextShowTime')
    nextShowPrize = json.get('nextShowPrize')

    # Check if broadcast socket URL exists
    if  not json.get('broadcast') or not json.get('broadcast').get('socketUrl'):
        print('Broadcast ended. Next show on %s for %s.' % (nextShowTime, nextShowPrize))
        return None

    # Return socket URL for websocket connection
    return json.get('broadcast').get('socketUrl').replace('https', 'wss')


# Message handler
def on_message(ws, message):
    global currentGame, broadcastEnded

     # Decode JSON data
    data_start = message.find('{')
    if data_start >= 0:
        data = json.loads(message[data_start:])

        # Check for game status message
        if data.get('type') == 'gameStatus':
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

        # Check for broadcast ended
        if data.get('type') == 'broadcastEnded' and not data.get('reason'):
            broadcastEnded = True
            print('Broadcast ended.')
            ws.close()

        # Check for question
        if data.get('type') == 'question' and data.get('answers'):
            parsed_answers = utils.build_answers(data.get('answers'))
            (prediction, confidence) = utils.predict_answers(data.get('question'), parsed_answers)

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
        if data.get('type') == 'questionSummary':

            # Load save game file and update correct answer
            with open('./games/%s.json' % currentGame) as file:    
                output = json.load(file)
            questions_output = output.get('questions')
            question_index = next((n for (n, val) in enumerate(questions_output) if val["questionId"] == data.get('questionId')))
            correct_index = next((n for (n, val) in enumerate(data.get('answerCounts')) if val["correct"]))
            prediction_correct = output['questions'][question_index]['prediction']['answer'] == chr(65 + correct_index)
            print(utils.colors.BOLD + ('Correct Answer: %s - %s' % (chr(65 + correct_index), output['questions'][question_index])) + utils.colors.ENDC)
            if prediction_correct:
                print(utils.colors.BOLD + utils.colors.OKGREEN + "Prediction Correct? Yes" + utils.colors.ENDC)
            else:
                print(utils.colors.BOLD + utils.colors.FAIL + "Prediction Correct? No" + utils.colors.ENDC)

            # Set correct answer in question object
            output['questions'][question_index]['correct'] = chr(65 + correct_index)
            output['numCorrect'] += 1 if prediction_correct else 0

            # Update save game file
            with open('./games/%s.json' % currentGame, 'w') as file:
                json.dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)
        
        # Print message to console
        hidden_messages = ['interaction', 'broadcastStats', 'kicked']
        if data.get('type') not in hidden_messages:
            print('MESSAGE: %s' % message)

def on_error(ws, error):
    print('ERROR: %s' % error)

def on_ping(ws, data):
    print('RECEIVED PING: %s, SENDING PONG' % data)
    ws.pong(data)

def on_close(ws):
    print('SOCKET CLOSED')

if __name__ == "__main__":

    if not "test" in sys.argv:
        socket_url = get_socket_url()
        if socket_url:
            print('CONNECTING TO %s' % socket_url)
            websocket.enableTrace(True)
            ws = websocket.WebSocketApp(socket_url,
                on_message = on_message,
                on_error = on_error,
                on_close = on_close,
                header = HEADERS
            )
            while not broadcastEnded:
                try:
                    ws.run_forever(ping_interval=5)
                except:
                    print('RECONNECTING')
    else:
        print("Running in Test Mode")

        # Load questions from file
        questions = json.load(open('questions.json'))

        # Loop through questions
        total = 0
        total_correct = 0

        for q in questions:
            if q.get('round') and q.get('round') <= 4:
                prediction = utils.predict_answers(q.get('question'), q.get('answers'))
                prediction_correct = prediction == q.get('correct')
                print('Predicted: %s, Correct: %s' % (prediction, q.get('correct')))
                if prediction_correct:
                    print(utils.colors.BOLD + utils.colors.OKGREEN + "Correct? Yes" + utils.colors.ENDC)
                else:
                    print(utils.colors.BOLD + utils.colors.FAIL + "Correct? No" + utils.colors.ENDC)
                total += 1
                total_correct += 1 if prediction_correct else 0

        print("Testing Complete")
        print("Total Correct: %s/%s" % (total_correct, total))
