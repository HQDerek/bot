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

    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = "Example Response"

    question, answers = question_api_response
    confidence = utils.find_answer_words_google(question, answers, {'A': 0, 'B': 0, 'C': 0}, [mock_response])

    assert confidence == {'A': 0, 'B': 0, 'C': 0}
