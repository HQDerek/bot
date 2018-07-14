""" unit tests for the hqtrivia_bot.py """
import pytest
from mock import Mock, patch
import utils


@pytest.fixture
def api_response():
    """ question/answers example set """
    return {
        "answers": {
            "A": "Badger",
            "B": "Cheetah",
            "C": "Giraffe"
        },
        "category": "Nature",
        "is_replay": True,
        "question": "What is the world's fastest land animal?",
        "questionId": 28482,
        "questionNumber": 1
    }


def mock_future_get(_url):
    """ mocked get response """
    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = "Example Response"

    mock_future = Mock()
    mock_future.result.return_value = mock_response
    return mock_future


@patch('utils.FuturesSession.get', side_effect=mock_future_get)
def test_predict_answers(_mock_session_get, api_response):  # pylint: disable=redefined-outer-name
    """ testing predict_answers """

    (prediction, confidence) = utils.predict_answers(
        api_response, api_response.get('answers')
    )

    assert prediction == 'A'
    assert confidence == {'A': '0%', 'B': '0%', 'C': '0%'}


def test_answer_words_google(api_response):  # pylint: disable=redefined-outer-name
    """ testing basic behaviour in find_answer_words_google """

    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = "Example Response"

    confidence = utils.find_answer_words_google(
        api_response.get('question'), api_response.get('answers'), \
        {'A': 0, 'B': 0, 'C': 0}, [mock_response]
    )

    assert confidence == {'A': 0, 'B': 0, 'C': 0}


def test_results_number_google(api_response):  # pylint: disable=redefined-outer-name
    """ testing basic behaviour in count_results_number_google """

    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = "Example Response"

    confidence = utils.count_results_number_google(
        api_response.get('question'), api_response.get('answers'), \
        {'A': 0, 'B': 0, 'C': 0}, [mock_response]
    )

    assert confidence == {'A': 0, 'B': 0, 'C': 0}


def test_question_words_wikipedia(api_response):  # pylint: disable=redefined-outer-name
    """ testing basic behaviour in find_question_words_wikipedia """

    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = "Example Response"

    confidence = utils.find_question_words_wikipedia(
        api_response.get('question'), api_response.get('answers'), \
        {'A': 0, 'B': 0, 'C': 0}, [mock_response]
    )

    assert confidence == {'A': 0, 'B': 0, 'C': 0}
