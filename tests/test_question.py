""" Question class unit tests """
from unittest.mock import mock_open, patch
import pytest
from tests.utils import generate_question
import question


@pytest.fixture(scope="module")
def question_kwargs():
    """ Example question kwargs / stored values """
    return {
        "answers": {"A": "1st, Jr.", "B": "2nd", "C": "3rd"},
        "category": "History",
        "correct": "A",
        "prediction": {"answer": "A", "confidence": {"A": "69%", "B": "21%", "C": "8%"}},
        "question": "Question text?",
        "questionId": 28404,
        "questionNumber": 3
    }


@patch('builtins.open')
def test_question_init_kwargs(mock_builtin_open):
    """ Ensure passing a dictionary of values to the init method
    will instantiate a full Question without loading from JSON file
    """
    question.Question(is_replay=True, **question_kwargs())
    mock_builtin_open.assert_not_called()


def test_question_init_load_id(monkeypatch):
    """
    Ensure passing a load_id argument to the Question will find and load
    the kwargs from a JSON file and instantiate the question
    """
    def mock_load(file): # pylint: disable=unused-argument
        """ Mock previous replay lists """
        return [[], [question_kwargs()]]
    monkeypatch.setattr(question, "load", mock_load)
    monkeypatch.setattr('builtins.open', mock_open(read_data=b''))
    test_q = question.Question(is_replay=True, load_id=question_kwargs().get('questionId'))
    expected = question_kwargs()
    assert test_q.id == expected.get('questionId')
    assert test_q.text == expected.get('question')
    assert test_q.prediction == expected.get('prediction')


def test_ans_correct_no_ans():
    """ Ensure that if the Question instance has no correct answer value
    the correct property method returns False
    """
    test_q = generate_question()
    test_q.correct = None
    assert test_q.answered_correctly is False


def test_ans_correct_has_ans():
    """ Ensure a Question's answered_correctly property method returns True
     if the Question's prediction matches its correct answer value
    """
    test_q = generate_question(correct=True)
    assert test_q.answered_correctly is True


def test_ans_correct_wrong_ans():
    """ Ensure a Questions answered_correctly property returns False if
    the Questions prediction values doesn't match the correct answer value
    """
    test_q = generate_question(correct=False)
    assert test_q.answered_correctly is False


def test_game_path_is_replay():
    """ Ensure that a Question's game_path method while in replay mode
    will return replay_results.json
    """
    test_q = generate_question(is_replay=True)
    assert test_q.game_path == 'replay_results.json'


@patch('question.glob')
@patch('os.path.getctime')
def test_game_path_not_replay(mock_getctime, mock_glob):
    """ Ensure that a Question's game_path method while not in replay mode
    returns the most recently created file """
    mock_getctime.return_value = 1
    mock_glob.return_value = ['games/mock_game_file.json']
    test_q = generate_question(is_replay=False)
    assert test_q.game_path == 'games/mock_game_file.json'


def test_add_prediction():
    """ Ensure Question has its prediction dictionary updated and save is called """
    prediction = "B"
    confidence = {
        "A": "0%",
        "B": "100%",
        "C": "0%"
    }
    expected = {
        "answer": prediction,
        "confidence": confidence
    }
    test_q = generate_question(correct=True)
    test_q.prediction = None
    assert test_q.prediction is None
    test_q.add_prediction(prediction, confidence)
    assert test_q.prediction == expected


@patch('question.Question.save')
def test_add_correct_is_replay_false(mock_save):
    """
    Ensure a Question that is not in replay mode will update its correct answer
    and call its save method
    """
    test_q = generate_question(is_replay=False)
    test_q.add_correct('B')
    assert mock_save.called


@patch('question.Question.save')
def test_add_correct_is_replay_true(mock_save):
    """
    Ensure a Question that is in replay mode will not update its correct answer
    or call save
    """
    test_q = generate_question(is_replay=True)
    test_q.add_correct('B')
    assert mock_save.called is False
