from glob import glob
import os
from json import load, dump

class Question(object):
    """ An instance of a HQ Trivia question """

    def __init__(self, is_replay=False, **kwargs):
        self.id = kwargs.get('questionId', None)
        self.number = kwargs.get('questionNumber', None)
        self.text = kwargs.get('question', None)
        self.answers = kwargs.get('answers', None)
        self.correct = kwargs.get("correct", None)
        self.category = kwargs.get("category", None)
        self.prediction = kwargs.get("prediction", {})
        self.is_replay = is_replay

    def get_output_path(self):
        """ Determine what file to save question in """
        path = 'replay_results.json'

        if self.is_replay is False:
            game_files = glob.glob('games/*.json')
            path = max(game_files, key=os.path.getctime)

        return path

    def save(self):
        """
        Checks most recently created results file, checks it for question with same id.
        If present, updates. If not, appends itself.
        """
        file_path = self.get_output_path()
        output_key = -1 if self.is_replay else 'questions' # last list in replay games or 'questions' key in live saved games

        with open(file_path) as file:
            output = load(file)

        # pull questions out of file
        questions = output[output_key]

        updated = False
        for idx, saved_question in enumerate(questions):
            if saved_question['id'] == self.id:
                questions[idx] = self._dict_for_json()
                updated = True
        if updated is False:
            questions.append(self._dict_for_json())

        # re-insert updated questions
        output[output_key] = questions

        # Update save game file
        with open(file_path, 'w') as file:
            dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

    def display_summary(self):
        pass

    def add_prediction(self, prediction, confidence):
        """ Add the prediction dict to the Question """
        self.prediction = {
            'answer': prediction,
            'confidence': confidence
        }
        self.save()

    def add_correct(self):
        pass

    def _dict_for_json(self):
        """ Convert instance to dict with correct keys in preparation for saving to JSON """
        output = vars(self)
        output['questionId'] = output.pop('id', None)
        output['questionNumber'] = output.pop('number', None)
        return output
