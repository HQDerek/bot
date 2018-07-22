""" unit tests for the hqtrivia_bot.py """
from glob import glob
from json import load
from mock import patch
import utils
from question import Question


def test_games():
    """ testing games """
    correct = {}
    num_questions = {}
    orig_correct = {}
    for filename in sorted(glob('games/*.json')):
        game = load(open(filename))
        count_correct = 0
        for turn in game.get('questions'):
            question = Question(is_replay=True, **turn)
            number = question.number
            with patch('builtins.print'):
                (prediction, _confidence) = utils.predict_answers(question)
            count_correct += (1 if prediction == question.correct else 0)
            correct[number] = correct.get(number, 0) + \
                (1 if prediction == question.correct else 0)
            orig_correct[number] = orig_correct.get(number, 0) + \
                (1 if question.correct == question.prediction.get('answer') else 0)
            num_questions[number] = num_questions.get(number, 0) + 1
        print('Game %d: %d correct: %s' % \
            (game.get('showId'), count_correct, correct))
    count_correct = sum(correct.values())
    count_orig_correct = sum(orig_correct.values())
    count_num_questions = sum(num_questions.values())
    print('Total correct: %d/%d | %.2f%% | %s' % (count_correct, count_num_questions, \
        (count_correct / count_num_questions) * 100, correct))
    print('Original correct: %d/%d | %.2f%% | %s' % (count_orig_correct, count_num_questions, \
        (count_orig_correct / count_num_questions) * 100, orig_correct))
    print('Num Questions: %d | %s' % (count_num_questions, num_questions))
    assert (count_correct / count_num_questions) * 100 > 65
