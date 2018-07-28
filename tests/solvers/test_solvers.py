""" unit tests for solvers """
import pytest
from mock import Mock
from solvers import GoogleAnswerWordsSolver, GoogleResultsCountSolver

@pytest.fixture(scope="module")
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

def test_google_answer_words_run(api_response): # pylint: disable=redefined-outer-name
    """
    Run GoogleAnswerWords Solver with empty response and ensure confidence is zero.
    """

    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = ""

    mock_future = Mock()
    mock_future.result.return_value = mock_response

    (prediction, confidence) = GoogleAnswerWordsSolver().run(
        api_response.get('question'), api_response.get('answers'), {'_': mock_future}, {'A': 0, 'B': 0, 'C': 0}
    )

    assert prediction == 'A'
    assert confidence == {'A': 0, 'B': 0, 'C': 0}


def test_google_results_count_run(api_response): # pylint: disable=redefined-outer-name
    """
    Run GoogleResultsCount Solver with empty response and ensure confidence is zero.
    """

    mock_response = Mock()
    mock_response.url = "/"
    mock_response.text = ""

    mock_future = Mock()
    mock_future.result.return_value = mock_response

    (prediction, confidence) = GoogleResultsCountSolver().run(
        api_response.get('question'),
        api_response.get('answers'),
        {'A': mock_future, 'B': mock_future, 'C': mock_future},
        {'A': 0, 'B': 0, 'C': 0}
    )

    assert prediction == 'A'
    assert confidence == {'A': 0, 'B': 0, 'C': 0}
