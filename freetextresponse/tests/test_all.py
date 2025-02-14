"""
Module To Test FreeTextResponse XBlock
"""
from datetime import datetime, timedelta
from os import path
import json
import unittest

import ddt
from mock import MagicMock
from xblock.validation import ValidationMessage
from django.db import IntegrityError

from freetextresponse.models import Credit
from freetextresponse.views import _is_at_least_one_phrase_present  # noqa
from freetextresponse.xblocks import FreeTextResponse

from .tests_utils import make_xblock

tests_dir = path.dirname(__file__)


class TestData(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for validate_field_data
    """
    weight = 0
    max_attempts = 0
    max_word_count = 0
    min_word_count = 0
    submitted_message = None


class TestRequest(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for @json_handler
    """
    method = None
    body = None
    success = None


@ddt.ddt
class FreetextResponseXblockTestCase(unittest.TestCase):
    # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """
    A complete suite of unit tests for the Free-text Response XBlock
    """

    def setUp(self):
        """
        Creates an xblock
        """
        self.xblock = make_xblock('freetextresponse', FreeTextResponse, {})

    def test_workbench_scenarios(self):
        """
        Checks workbench scenarios title and basic scenario
        """
        result_title = 'Free Text Response Many'
        basic_scenario = "<freetextresponse />"
        test_result = sorted(self.xblock.workbench_scenarios())
        self.assertEqual(result_title, test_result[0][0])
        self.assertIn(basic_scenario, test_result[0][1])

    def test_generate_validation_message(self):
        # pylint: disable=invalid-name, protected-access
        """
        Checks classmethod _generate_validation_message
        """
        msg = 'weight attempts cannot be negative'
        result = ValidationMessage(
            ValidationMessage.ERROR,
            msg
        )
        test_result = self.xblock._generate_validation_message(msg)
        self.assertEqual(
            type(result),
            type(test_result),
        )
        self.assertEqual(
            result.text,
            test_result.text,
        )

    @ddt.file_data(path.join(tests_dir, 'validate_field_data.json'))
    def test_validate_field_data(self, **test_dict):
        """
        Checks classmethod validate_field_data
        tests the instructor values set in edit
        """
        test_data = TestData()
        test_data.weight = test_dict['weight']
        test_data.max_attempts = test_dict['max_attempts']
        test_data.max_word_count = test_dict['max_word_count']
        test_data.min_word_count = test_dict['min_word_count']
        test_data.submitted_message = test_dict['submitted_message']
        validation = set()
        self.xblock.validate_field_data(validation, test_data)
        validation_list = list(validation)
        # Only one validation error should be in set
        self.assertEqual(1, len(validation_list))
        self.assertEqual(
            test_dict['result'],
            validation_list[0].text,
        )

    def test_initialization_variables(self):
        """
        Checks that instance variables are initialized correctly
        """
        self.assertEqual('Free-text Response', self.xblock.display_name)
        self.assertEqual(
            'Please enter your response within this text area',
            self.xblock.prompt,
        )
        self.assertEqual(0.0, self.xblock.score)
        self.assertEqual(0, self.xblock.max_attempts)
        self.assertTrue(self.xblock.display_correctness)
        self.assertEqual(1, self.xblock.min_word_count)
        self.assertEqual(10000, self.xblock.max_word_count)
        self.assertEqual(
            [],
            self.xblock.fullcredit_keyphrases,
        )
        self.assertEqual(
            [],
            self.xblock.halfcredit_keyphrases,
        )
        self.assertEqual('', self.xblock.student_answer)
        self.assertEqual(0, self.xblock.count_attempts)

    # Default Views
    def test_student_view(self):
        # pylint: disable=protected-access
        """
        Checks the student view for student specific instance variables.
        """
        student_view = self.xblock.student_view()
        student_view_html = student_view.content
        self.assertIn(self.xblock.display_name, student_view_html)
        self.assertIn(self.xblock.prompt, student_view_html)

        self.assertIn(self.xblock._get_word_count_message(), student_view_html)
        self.assertIn(self.xblock._get_indicator_class(), student_view_html)
        self.assertIn(self.xblock._get_problem_progress(), student_view_html)
        self.assertIn(
            self.xblock._get_used_attempts_feedback(),
            student_view_html
        )
        self.assertIn(self.xblock._get_nodisplay_class(), student_view_html)
        self.assertIn(
            self.xblock._get_indicator_visibility_class(),
            student_view_html
        )

    def test_build_fragment_prompt_html(self):
        """
        Checks that build_fragment allows html in the prompt variable

        if the 'safe' filter is not used then the django
        template pipeline returns html tags like,
            '&lt;p&gt;Please enter your response here&lt;/p&gt;'
        """
        studio_settings_prompt = "<p>Please enter your response here</p>"
        context = {
            'prompt': studio_settings_prompt,
        }
        fragment = self.xblock.build_fragment(
            template='view.html',
            context=context,
            js_init='FreeTextResponseView',
            css=[],
            js=[],
        )
        self.assertIn(studio_settings_prompt, fragment.content)

    def test_max_score(self):
        """
        Tests max_score function
        Should return the weight
        """
        self.xblock.weight = 4
        self.assertEqual(self.xblock.weight, self.xblock.max_score())

    def test_studio_view(self):
        """
        Checks studio view for instance variables specified by the instructor.
        """
        studio_view_html = self.xblock.studio_view(context=None).content
        self.assertIn(self.xblock.display_name, studio_view_html)
        self.assertIn(self.xblock.prompt, studio_view_html)
        self.assertIn(str(self.xblock.weight), studio_view_html)
        self.assertIn(str(self.xblock.max_attempts), studio_view_html)
        self.assertIn(str(self.xblock.display_correctness), studio_view_html)
        self.assertIn(str(self.xblock.min_word_count), studio_view_html)
        self.assertIn(str(self.xblock.max_word_count), studio_view_html)
        self.assertIn(
            ', '.join(
                self.xblock.fullcredit_keyphrases,
            ),
            studio_view_html,
        )
        self.assertIn(
            ', '.join(
                self.xblock.halfcredit_keyphrases,
            ),
            studio_view_html,
        )
        self.assertIn(str(self.xblock.submitted_message), studio_view_html)

    # Scoring
    @ddt.file_data(path.join(tests_dir, 'determine_credit.json'))
    def test_determine_credit(self, **test_data):
        # pylint: disable=protected-access
        """
        Tests determine_credit
        After a student response this function will
        return the Credit enum full, half, or zero
        """
        self.xblock._word_count_valid = MagicMock(
            return_value=test_data['word_count_valid']
        )
        self.xblock.fullcredit_keyphrases = test_data['fullcredit']
        self.xblock.halfcredit_keyphrases = test_data['halfcredit']
        self.xblock.student_answer = test_data['student_answer']
        credit = Credit[test_data['credit']]
        self.assertEqual(credit, self.xblock._determine_credit())

    @ddt.data(Credit.zero, Credit.half, Credit.full)
    def test_compute_score(self, credit):
        # pylint: disable=protected-access
        """
        Tests _compute_score
        After a student response this function will
        set the xblock score and publish the grade
        """
        self.xblock.runtime.publish = MagicMock(return_value=None)
        self.xblock._determine_credit = MagicMock(return_value=credit)
        self.xblock._compute_score()
        self.xblock.runtime.publish.assert_called_with(
            self.xblock,
            'grade',
            {'value': credit.value, 'max_value': Credit.full.value},
        )

    def test_compute_score_integrity_error(self):
        # pylint: disable=protected-access, invalid-name
        """
        Tests that _compute_score gracefully handles IntegrityError exception.

        Tests to ensure that if an IntegrityError exception
        is thrown by any of the methods/functions called in the
        process of saving the score, the program handles it gracefully.
        We force runtime.publish to throw an IntegrityError exception,
        and expect _compute_score to be graceful about it.
        """
        self.xblock.runtime.publish = MagicMock(return_value=None)
        self.xblock.runtime.publish.side_effect = IntegrityError(
            "Unique Key Violation"
        )
        self.xblock._determine_credit = MagicMock(return_value=Credit.zero)
        self.xblock._compute_score()

    def test_is_at_least_one_phrase_present(self):
        # pylint: disable=invalid-name, protected-access
        """
        Tests _is_at_least_one_phrase_present
        Helper method to match student response
        with given phrase list
        """
        keyphrases_list = [
            'do dict phrase',
            're dict phrase',
            'mi dict phrase',
            'fa dict phrase'
        ]
        answer = keyphrases_list[1]
        answer = 'ajhsdfhjaefhaf ' + answer + 'jkfbaufebn;  fuqv'
        self.assertTrue(
            _is_at_least_one_phrase_present(
                keyphrases_list,
                answer,
            ),
        )

    def test_not_is_at_least_one_phrase_present(self):
        # pylint: disable=invalid-name, protected-access
        """
        Tests _is_at_least_one_phrase_present
        Helper method to match student response
        with given phrase list
        """
        keyphrases_list = [
            'do dict phrase',
            're dict phrase',
            'mi dict phrase',
            'fa dict phrase'
        ]
        answer = 'so dict phrase'
        answer = 'ajhsdfhjaefhaf ' + answer + 'jkfbaufebn;  fuqv'
        self.assertFalse(
            _is_at_least_one_phrase_present(
                keyphrases_list,
                answer,
            ),
        )

    @ddt.file_data(path.join(tests_dir, 'word_count_valid.json'))
    def test_word_count_valid(self, **test_data):
        # pylint: disable=protected-access
        """
        Tests _word_count_valid
        After a student response this will
        determine if the response meets word
        count criteria
        """
        self.xblock.min_word_count = test_data['min_word_count']
        self.xblock.max_word_count = test_data['max_word_count']
        self.xblock.student_answer = test_data['student_answer']
        self.assertEqual(test_data['result'], self.xblock._word_count_valid())

    # Messages
    @ddt.data(
        # max_attempts, count_attempts, result
        (None, 4, ''),
        (0, 4, ''),
        (1, 0, 'You have used 0 of 1 submission'),
        (3, 2, 'You have used 2 of 3 submissions'),
    )
    @ddt.unpack
    def test_used_attempts_feedback_normal(
            self,
            max_attempts,
            count_attempts,
            result
    ):
        # pylint: disable=invalid-name, protected-access
        """
        Tests get_used_attempts_feedback
        Returns the used attempts feedback message
        after a student response
        """
        self.xblock.max_attempts = max_attempts
        self.xblock.count_attempts = count_attempts
        self.assertEqual(
            result,
            self.xblock._get_used_attempts_feedback(),
        )

    @ddt.data(
        # min_word_count, max_word_count, result
        (0, 1, 'Your response must be between 0 and 1 word.'),
        (2, 3, 'Your response must be between 2 and 3 words.'),
    )
    @ddt.unpack
    def test_get_word_count_message(
            self,
            min_word_count,
            max_word_count,
            result,
    ):
        # pylint: disable=protected-access
        """
        Tests _get_word_count_message
        Returns the word count message
        based on instructor set word count
        min and max
        """
        self.xblock.min_word_count = min_word_count
        self.xblock.max_word_count = max_word_count
        self.assertEqual(
            result,
            self.xblock._get_word_count_message(),
        )

    # Tested from get_user_alert
    @ddt.file_data(path.join(tests_dir, 'invalid_word_count_message.json'))
    def test_get_user_alert(self, **test_data):
        # pylint: disable=protected-access
        """
        Tests _get_user_alert
        if the word count is invalid this will
        return the invalid word count message
        """
        self.xblock._word_count_valid = MagicMock(
            return_value=test_data['word_count_valid']
        )
        self.xblock.count_attempts = test_data['count_attempts']
        self.xblock.min_word_count = test_data['min_word_count']
        self.xblock.max_word_count = test_data['max_word_count']
        self.assertEqual(
            str(test_data['result']),
            self.xblock._get_user_alert(
                ignore_attempts=test_data['ignore_attempts']
            ),
        )

    @ddt.data(
        # word_count_valid, result
        (False, ''),
        (True, 'test submission received message'),
    )
    @ddt.unpack
    def test_get_submitted_message(
            self,
            word_count_valid,
            result
    ):
        # pylint: disable=protected-access
        """
        Tests _get_submitted_message
        Returns a message to display to
        the user after they submit a
        response
        """
        self.xblock._word_count_valid = MagicMock(
            return_value=word_count_valid
        )
        self.xblock.submitted_message = 'test submission received message'
        self.assertEqual(
            result,
            self.xblock._get_submitted_message(),
        )

    @ddt.file_data(path.join(tests_dir, 'problem_progress.json'))
    def test_get_problem_progress(self, **test_data):
        # pylint: disable=protected-access
        """
        Tests _get_problem_progress
        Score can be 0, 0.5, or 1
        Return a message for current
        problem progress
        """
        self.xblock.weight = test_data['weight']
        self.xblock.score = test_data['score']
        self.assertEqual(
            test_data['result'],
            self.xblock._get_problem_progress(),
        )

    # CSS Classes
    @ddt.file_data(path.join(tests_dir, 'indicator_class.json'))
    def test_get_indicator_class(self, **test_data):
        # pylint: disable=protected-access
        """
        Test _get_indicator_class
        Returns the correctness CCS class
        to show correct/incorrect/unanswered
        UI
        """
        credit = None
        if test_data['credit']:
            credit = Credit[test_data['credit']]
        self.xblock.display_correctness = test_data['display_correctness']
        self.xblock._word_count_valid = MagicMock(
            return_value=test_data['word_count_valid']
        )
        self.xblock._determine_credit = MagicMock(return_value=credit)
        self.assertEqual(
            test_data['result'],
            self.xblock._get_indicator_class()
        )

    @ddt.data(
        # display_correctness, result
        (True, ''),
        (False, 'hidden'),
    )
    @ddt.unpack
    def test_get_indicator_visibility_class(self, display_correctness, result):
        # pylint: disable=invalid-name, protected-access
        """
        Tests _get_indicator_visibility_class
        Return hidden or blank CCS class to
        hide correctness UI
        """
        self.xblock.display_correctness = display_correctness
        self.assertEqual(
            result,
            self.xblock._get_indicator_visibility_class(),
        )

    @ddt.file_data(path.join(tests_dir, 'submitdisplay_class.json'))
    def test_get_submitdisplay_class(self, **test_data):
        # pylint: disable=protected-access
        """
        Tests _get_submitdisplay_class
        Return blank or nodisplay CCS class
        that hide the submit buttons after
        a user has reached max_attempts
        """
        self.xblock.max_attempts = test_data['max_attempts']
        self.xblock.count_attempts = test_data['count_attempts']
        self.assertEqual(
            test_data['result'],
            self.xblock._get_nodisplay_class()
        )

    @ddt.data(
        ({'max_attempts': None, 'count_attempts': 1}, True),
        ({'max_attempts': None, 'count_attempts': 3}, True),
        ({'max_attempts': 0, 'count_attempts': 3}, True),
        ({'max_attempts': 3, 'count_attempts': 2}, True),
        ({'max_attempts': 3, 'count_attempts': 3}, False),
        ({'due': None, 'graceperiod': None}, True),
        ({'due': None, 'graceperiod': timedelta(hours=1)}, True),
        (
            {
                'due': datetime.utcnow() + timedelta(hours=1),
                'graceperiod': None,
            },
            True,
        ),
        (
            {
                'due': datetime.utcnow() - timedelta(hours=1),
                'graceperiod': None,
            },
            False,
        ),
        (
            {
                'due': datetime.utcnow() - timedelta(hours=1),
                'graceperiod': timedelta(hours=2),
            },
            True,
        ),
        (
            {
                'due': datetime.utcnow() - timedelta(hours=5),
                'graceperiod': timedelta(hours=2),
            },
            False,
        ),
    )
    @ddt.unpack
    def test_submit(self, xblock_config, can_submit):
        # pylint: disable=protected-access
        """
        Tests save_response results
        """
        student_answer = 'asdf'
        for key, value in xblock_config.items():
            setattr(self.xblock, key, value)
        data = json.dumps({'student_answer': student_answer})
        request = TestRequest()
        request.method = 'POST'
        request.body = data.encode('utf-8')
        response = self.xblock.submit(request)
        # Added for response json_body
        # pylint: disable=no-member
        self.assertEqual(
            response.json_body['status'],
            'success'
        )
        self.assertEqual(
            response.json_body['problem_progress'],
            self.xblock._get_problem_progress()
        )
        self.assertEqual(
            response.json_body['indicator_class'],
            self.xblock._get_indicator_class()
        )
        self.assertEqual(
            response.json_body['used_attempts_feedback'],
            self.xblock._get_used_attempts_feedback()
        )
        self.assertEqual(
            response.json_body['nodisplay_class'],
            self.xblock._get_nodisplay_class()
        )
        self.assertEqual(
            response.json_body['submitted_message'],
            self.xblock._get_submitted_message()
        )
        self.assertEqual(
            response.json_body['user_alert'],
            self.xblock._get_user_alert(
                ignore_attempts=True,
            )
        )
        self.assertEqual(
            response.json_body['visibility_class'],
            self.xblock._get_indicator_visibility_class()
        )
        self.assertEqual(
            self.xblock.student_answer,
            student_answer if can_submit else ''
        )

    @ddt.data(
        ({'max_attempts': None, 'count_attempts': 1}, True),
        ({'max_attempts': None, 'count_attempts': 3}, True),
        ({'max_attempts': 0, 'count_attempts': 3}, True),
        ({'max_attempts': 3, 'count_attempts': 3}, False)
    )
    @ddt.unpack
    def test_save_response(self, xblock_config, can_save):
        # pylint: disable=protected-access
        """
        Tests save_response results
        """
        student_answer = 'asdf'
        for key, value in xblock_config.items():
            setattr(self.xblock, key, value)
        data = json.dumps({'student_answer': student_answer})
        request = TestRequest()
        request.method = 'POST'
        request.body = data.encode('utf-8')
        response = self.xblock.save_reponse(request)
        # Added for response json_body
        # pylint: disable=no-member
        self.assertEqual(
            response.json_body['status'],
            'success'
        )
        self.assertEqual(
            response.json_body['problem_progress'],
            self.xblock._get_problem_progress()
        )
        self.assertIsNone(
            response.json_body.get('indicator_class', None),
        )
        self.assertEqual(
            response.json_body['used_attempts_feedback'],
            self.xblock._get_used_attempts_feedback()
        )
        self.assertEqual(
            response.json_body['nodisplay_class'],
            self.xblock._get_nodisplay_class()
        )
        self.assertEqual(
            response.json_body['submitted_message'],
            ''
        )
        self.assertEqual(
            response.json_body['user_alert'],
            self.xblock.saved_message
        )
        self.assertEqual(
            response.json_body['visibility_class'],
            self.xblock._get_indicator_visibility_class()
        )
        self.assertEqual(
            self.xblock.student_answer,
            student_answer if can_save else ''
        )
