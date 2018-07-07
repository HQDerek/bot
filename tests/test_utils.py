import pytest
from mock import Mock, patch
import utils

class TestUtils(object):

    @pytest.fixture
    def question_api_response(self):
        question = "What did Yankee Doodle stick in his cap?"
        answers = {
            'A': 'Feather',
            'B': 'Noodle soup',
            'C': 'Duck'
        }
        return (question, answers)


    @patch('utils.grequests.get')
    def test_find_answer_words_google(self, mock_grequests_get, question_api_response):

        mock_response = Mock()
        mock_grequests_get.return_value = mock_response
        mock_response.url = "/"
        mock_response.text = "Example Response"

        question, answers = question_api_response
        google_responses = utils.build_google_queries(question, answers)

        confidence = utils.find_answer_words_google(question, answers, {'A': 0, 'B': 0, 'C': 0}, google_responses[:1])

        assert confidence == {'A': 0, 'B': 0, 'C': 0}
