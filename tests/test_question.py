from unittest.mock import mock_open, patch
import pytest
from tests.utils import generate_game, generate_question
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
def test_question_init_kwargs(mock_open):
    """ Ensure passing a dictionary of values to the init method
    will instantiate a full Question without loading from JSON file
    """
    qs = question.Question(is_replay=True, **question_kwargs())
    mock_open.assert_not_called()


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
    qs = question.Question(is_replay=True, load_id=question_kwargs().get('questionId'))
    expected = question_kwargs()
    assert qs.id == expected.get('questionId')
    assert qs.text == expected.get('question')
    assert qs.prediction == expected.get('prediction')


def test_answered_correctly_no_answer_yet():
    """ Ensure that if the Question instance has no correct answer value
    the correct property method returns False
    """
    question = generate_question()
    question.correct = None
    assert question.answered_correctly is False


def test_answered_correctly_has_correct_answer():
    """ Ensure a Question's answered_correctly property method returns True
     if the Question's prediction matches its correct answer value
    """
    question = generate_question(correct=True)
    assert question.answered_correctly is True


def test_answered_correctly_has_incorrect_answer():
    """ Ensure a Questions answered_correctly property returns False if
    the Questions prediction values doesn't match the correct answer value
    """
    question = generate_question(correct=False)
    assert question.answered_correctly is False


def test_game_path_is_replay_true():
    """ Ensure that a Question's game_path method while in replay mode
    will return replay_results.json
    """
    question = generate_question(is_replay=True)
    assert question.game_path == 'replay_results.json'


def test_game_path_is_replay_false():
    """ Ensure that a Question's game_path method while not in replay mode
    returns the most recently created file """
    question = generate_question(is_replay=False)
    assert question.game_path == 'replay_results.json'


# params (in_replay, file_val, expected_save)
def test_save():
    """ Ensure a Question saves itself in the correct location depending on its
     replay mode and whether it has been previously saved
     """
    pass


def test_prediction():
    """ Ensure Question has its prediction dictionary updated and save is called """
    pass


def test_add_correct_is_replay_false():
    """
    Ensure a Question that is not in replay mode will update its correct answer
    and call its save method
    """
    pass


def test_add_correct_is_replay_true():
    """
    Ensure a Question that is in replay mode will not update its correct answer
    or call save
    """
    pass