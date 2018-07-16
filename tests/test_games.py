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
    correct = {}
    num_questions = {}
    orig_correct = {}
    for filename in sorted(glob('games/*.json')):
        game = load(open(filename))
        for turn in game.get('questions'):
            turn['is_replay'] = True
            number = turn.get('questionNumber')
            with patch('builtins.print'):
                (prediction, _confidence) = utils.predict_answers(turn, turn.get('answers'))
            correct[number] = correct.get(number, 0) + \
                (1 if prediction == turn.get('correct') else 0)
            orig_correct[number] = orig_correct.get(number, 0) + \
                (1 if turn.get('correct') == turn.get('prediction').get('answer') else 0)
            num_questions[number] = num_questions.get(number, 0) + 1
        print('Game %s: correct: %s' % \
            (game.get('showId'), correct))
    count_correct = sum(correct.values())
    count_orig_correct = sum(orig_correct.values())
    count_num_questions = sum(num_questions.values())
    print('Total correct: %d/%d | %.2f%% | %s' % (count_correct, count_num_questions, \
        (count_correct / count_num_questions) * 100, correct))
    print('Original correct: %d/%d | %.2f%% | %s' % (count_orig_correct, count_num_questions, \
        (count_orig_correct / count_num_questions) * 100, orig_correct))
    print('Num Questions: %d | %s' % (count_num_questions, num_questions))
    assert (count_correct / count_num_questions) * 100 > 65
