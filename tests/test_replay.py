""" Tests for the Replayer class and its methods """
from unittest.mock import mock_open, patch, ANY
from json import loads
import pytest
from tests.utils import generate_game, generate_question
import replay


@pytest.mark.parametrize("globbed_paths, game_json", [
    ([], None), # no game in game folder, no json to return
    (['games/2018-02-25-game-3701'], generate_game(as_json=True)), # one game file, mock json
    (['games/2018-02-25-game-3701', 'games/2018-02-26-game-3702'], generate_game(as_json=True)), # two games, mock json
])
def test_load_questions(globbed_paths, game_json, monkeypatch):
    """ Ensure a Replay.load_question method will read correctly from the
    games directory and convert the JSON to Question instances ordered by their
    question number
    """
    # monkey patch the glob and json.load functions for values we want in the test
    def mock_glob(path):
        """ Mock builtin glob function """
        return globbed_paths
    def mock_load(file):
        """ Mock JSON loaded from game file """
        return loads(game_json)
    monkeypatch.setattr(replay, "glob", mock_glob)
    monkeypatch.setattr(replay, "load", mock_load)
    monkeypatch.setattr('builtins.open', mock_open(read_data=''))
    # call load_questions without instantiating (because init also calls load_questions)
    questions = replay.Replayer.load_questions()
    # make sure correct number of q's loaded
    assert len(questions) == len(globbed_paths) * 12
    # ensure q's ordered by numbers 1-12
    for idx, question in enumerate(questions):
        if idx == 0:
            assert question.number == 1
        else:
            assert question.number >= questions[idx-1].number


@pytest.mark.parametrize("loaded_questions", [
    [], # no questions loaded
    [generate_question(is_replay=True) for _ in range(1)], # single question
    [generate_question(is_replay=True) for _ in range(24)] # two games worth
])
@patch('replay.Replayer.load_questions')
@patch('replay.HqTriviaBot.prediction_time')
@patch('replay.Replayer.setup_output_file')
def test_play(mock_setup_file, mock_prediction_time, mock_load_question, loaded_questions):
    """ Ensure running play on Replayer will call its own setup_output_file methos,
    call HqTriviaBot.prediction_time
    """
    mock_load_question.return_value = loaded_questions
    replayer = replay.Replayer()
    replayer.play()
    # ensure output setup function called every time replay is used
    assert mock_setup_file.called
    # ensure prediction_time called for each loaded question
    assert mock_prediction_time.call_count == len(loaded_questions)

@patch('replay.dump')
def test_setup_output_file_read_mode(mock_dump, monkeypatch):
    """ Ensure when setup_output_file called in r+ mode it will read local
    replay file and append an empty list to it
    """
    def mock_load(file):
        """ Mock previous replay lists """
        return [[], []]
    monkeypatch.setattr(replay, "load", mock_load)
    monkeypatch.setattr('builtins.open', mock_open(read_data=''))
    replay.Replayer.setup_output_file()
    assert mock_dump.called
    mock_dump.assert_called_with([[], [], []], ANY, ensure_ascii=False, sort_keys=True, indent=4)

@patch('replay.DataFrame')
@patch('replay.webbrowser')
def test_gen_report_six_replays(mock_webbrowser, mock_data_frame, monkeypatch):
    """
    Ensure correct values are passed to the pandas dataframe. Six games will get
    progressively more 'correct'. Also ensure html file is generated.
    """
    monkeypatch.setattr('builtins.open', mock_open(read_data='%s'))

    def mock_load(file):
        """ Mock replay data. Makes 6 replays over 10 games. Progressively bumps
        up number of correct. Eg. replay1 - 0 correct, replay2 - 1 correct,
        ... replay6 - 5 correct
        """
        replays = []
        for i in range(6):
            replay = []
            for _ in range(10):
                for q in generate_game(num_correct=i, correct='A')['questions']:
                    replay.append(q)
            replay = sorted(replay, key=lambda q: q['questionNumber'])
            replays.append(replay)
        return replays

    monkeypatch.setattr(replay, "load", mock_load)
    replay.Replayer.gen_report()
    assert mock_webbrowser.open.called
    # ensure correct number of columns, one for each question over 10 games - 120
    assert len(mock_data_frame.call_args[1]['columns'][0]) == 120
    # ensure dataframe column titles orderd correctly
    assert '#1 \n' in mock_data_frame.call_args[1]['columns'][0]
    assert '#12 \n' in mock_data_frame.call_args[1]['columns'][-1]
    # ensure inital 'master' row in dataframe all incorrect
    assert mock_data_frame.call_args[1]['data'][0].count(-1) == 120
    # ensure first real comparison replay has improved by 10 (1 right per game)
    assert mock_data_frame.call_args[1]['data'][1].count(1) == 10
    assert mock_data_frame.call_args[1]['data'][1].count(0) == 110
    # ensure 6th real comparison replay has improved by 50 (5 right per game)
    assert mock_data_frame.call_args[1]['data'][5].count(1) == 50
    assert mock_data_frame.call_args[1]['data'][5].count(0) == 70
    # ensure dataframe converted to table
    assert  mock_data_frame.return_value.to_html.called
