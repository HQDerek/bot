""" unit tests for the hqtrivia_bot.py """
import pytest
from mock import Mock, patch
from question import Question
import utils
from question import Question


@pytest.fixture
def question_instance():
    """ mock question object """
    q_kwargs = {
        "answers": {
            "A": "Badger",
            "B": "Cheetah",
            "C": "Giraffe"
        },
        "category": "Nature",
        "question": "What is the world's fastest land animal?",
        "questionId": 28482,
        "questionNumber": 1
    }
    return Question(is_replay=True, **q_kwargs)


def mock_cache_get(_url):
    """ mocked get response """
    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = "Example Response"

    mock_get = Mock()
    mock_get.result.return_value = mock_response
    return mock_get


@patch('utils.CachedSession.get', side_effect=mock_cache_get)
def test_predict_answers(_mock_session_get, question_instance):  # pylint: disable=redefined-outer-name
    """ testing predict_answers """

    (prediction, confidence) = utils.predict_answers(question_instance)

    assert prediction == 'A'
    assert confidence == {'A': '0%', 'B': '0%', 'C': '0%'}


def test_answer_words_google(question_instance):  # pylint: disable=redefined-outer-name
    """ testing basic behaviour in find_answer_words_google """

    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = "Example Response"

    confidence = utils.find_answer_words_google(
        question_instance.text, question_instance.answers, \
        {'A': 0, 'B': 0, 'C': 0}, [mock_response]
    )

    assert confidence == {'A': 0, 'B': 0, 'C': 0}


def test_results_number_google(question_instance):  # pylint: disable=redefined-outer-name
    """ testing basic behaviour in count_results_number_google """

    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = "Example Response"

    confidence = utils.count_results_number_google(
        question_instance.text, question_instance.answers, \
        {'A': 0, 'B': 0, 'C': 0}, [mock_response]
    )

    assert confidence == {'A': 0, 'B': 0, 'C': 0}
