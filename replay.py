""" Module for replaying a given game """
from glob import glob
from json import load, dump
from question import Question
from utils import predict_answers
from pandas import DataFrame
import os
import webbrowser

class Replayer(object):
    """ One instance of the game Replayer """
    def __init__(self, game_paths=None):
        self.questions = self.load_questions(game_paths)

    @staticmethod
    def load_questions(game_paths=None):
        """ Create a list of Question objects to replay """
        questions = []
        if not game_paths:
            game_paths = [filename for filename in glob('games/*.json')]
        for game_path in game_paths:
            game_data = load(open(game_path))
            for question in game_data['questions']:
                questions.append(Question(is_replay=True, **question))
        questions.sort(key=lambda q:q.number)
        return questions

    def play(self):
        """ Play all questions loaded from saved games """
        self.setup_output_file()
        for question in self.questions:
            (prediction, confidence) = predict_answers(question)
            question.add_prediction(prediction, confidence)

    def setup_output_file(self, mode='r+'):
        """ Create or load replayer output file """
        try:
            with open('replay_results.json', mode) as file:
                output = load(file) if mode == 'r+' else []
                output.append([])
                file.seek(0)
                dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)
        except FileNotFoundError:
            self.setup_output_file(mode='w+')

    def gen_report(self):

        with open('replay_results.json', 'r') as file:
            replays = load(file)
            max_q_index = len(replays[0]) - 1
            trimmed_replays = [replay[:max_q_index] if len(replay) > (max_q_index + 1) else replay for replay in replays]

        col_names = []
        run_results = []
        for replay_index, replay in enumerate(trimmed_replays):
            run_result = []
            for q_idx, question_kwargs in enumerate(replay):
                question = Question(is_replay=True, **question_kwargs)

                if replay_index == 0:
                    run_result.append(1 if question.answered_correctly else -1);
                    col_names.append("#{} \n {}".format(question.number, question.id))
                else:
                    try:
                        if question.prediction['answer'] == trimmed_replays[0][q_idx]['prediction']['answer']:
                            run_result.append(0)
                        elif question.answered_correctly:
                            run_result.append(1)
                        else:
                            run_result.append(-1)
                    except IndexError:
                            run_result.append(0)

            run_results.append(run_result)
        print(run_results)
        df = DataFrame(columns=col_names, data=run_results)
        with open('report_template.html', 'r') as file:
            template_string=file.read().replace('\n', '')
        html = template_string % df.to_html(classes='replay-table').replace('border="1"','border="0"')
        path = os.path.abspath('replay_report.html')
        url = 'file://' + path

        with open(path, 'w') as f:
            f.write(html)
        webbrowser.open(url)
