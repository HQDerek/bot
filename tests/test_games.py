""" unit tests for the hqtrivia_bot.py """
from glob import glob
from json import load
from mock import Mock, patch
from requests_cache import CachedSession
import utils

def cached_get(url):
    """ cached session """
    session = CachedSession('db/cache', allowable_codes=(200, 302, 304))
    response = Mock()
    response.result.return_value = session.get(url)
    return response

@patch('utils.FuturesSession.get', side_effect=cached_get)
def test_games(_mock_futures):
    """ testing games """
    total_correct = 0
    total_questions = 0
    for filename in glob('games/*.json'):
        game = load(open(filename))
        correct = 0
        for turn in game.get('questions'):
            turn['is_replay'] = True
            # (prediction, _confidence) = utils.predict_answers(turn, turn.get('answers'))
            # if prediction == turn.get('correct'):
            #     correct += 1
            total_questions += 1
        total_correct += correct
        print('Game %s: %s/%s correct (Original: %s)' % \
            (game.get('showId'), correct, len(game.get('questions')), game.get('numCorrect')))
    print('Total correct: %s/%s' % (total_correct, total_questions))
