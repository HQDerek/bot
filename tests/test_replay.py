""" Tests for the Replayer class and its methods """
import pytest
from tests.utils import generate_game
import replay
from unittest.mock import mock_open
from json import loads


@pytest.mark.parametrize("globbed_paths, game_json", [
    ([], None), # no game in game folder, no json to return
    (['games/2018-02-25-game-3701'], generate_game(as_JSON=True)), # one game file, mock json
    (['games/2018-02-25-game-3701', 'games/2018-02-26-game-3702'], generate_game(as_JSON=True)), # two games, mock json
])
def test_load_questions(globbed_paths, game_json, monkeypatch):
    """ Ensure a Replay.load_question method will read correctly from the
    games directory and convert the JSON to Question instances ordered by their
    question number
    """
    # monkey patch the glob and json.load functions for values we want in the test
    def mock_glob(path):
        return globbed_paths
    def mock_load(file):
        """ Mock JSON loaded from game file """
        return loads(game_json)
    monkeypatch.setattr(replay, "glob", mock_glob)
    monkeypatch.setattr(replay, "load", mock_load)
    monkeypatch.setattr('builtins.open', mock_open(read_data=''))
    # call load_questions without instantiating (because init also calls load_questions)
    questions = replay.Replayer.load_questions()
    print("RUNNING")
    # make sure correct number of q's loaded
    assert len(questions) == len(globbed_paths) * 12
    # ensure q's ordered by numbers 1-12
    for idx, q in enumerate(questions):
        if idx == 0:
            assert q.number == 1
        else:
            assert q.number >= questions[idx-1].number
