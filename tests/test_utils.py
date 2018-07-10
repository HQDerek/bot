""" unit tests for the hqtrivia_bot.py """
import pytest
from mock import Mock
import utils


@pytest.fixture
def question_api_response():
    """ question/answers example set """
    question = "What did Yankee Doodle stick in his cap?"
    answers = {
        'A': 'Feather',
        'B': 'Noodle soup',
        'C': 'Duck'
    }
    return question, answers


def test_find_answer_words_google(question_api_response):  # pylint: disable=redefined-outer-name
    """ testing basic behaviour in find_answer_words_google """

    mock_result = Mock()
    mock_result.url = "/"
    mock_result.text = "Example Response"

    mock_future = Mock()
    mock_future.result.return_value = mock_result

    question, answers = question_api_response
    confidence = utils.find_answer_words_google(question, answers, {'A': 0, 'B': 0, 'C': 0}, [mock_future])

    assert confidence == {'A': 0, 'B': 0, 'C': 0}
