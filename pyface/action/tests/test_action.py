

from traits.testing.unittest_tools import unittest

from ..action import Action
from ..action_event import ActionEvent


class TestAction(unittest.TestCase):
    def test_default_id(self):
        action = Action(name='Test')
        self.assertEqual(action.id, 'Test')

    def test_id(self):
        action = Action(name='Test', id='test')
        self.assertEqual(action.id, 'test')

    def test_perform(self):
        # test whether function is called by updating list
        # XXX should really use mock
        memo = []

        def perform():
            memo.append('called')

        action = Action(name='Test', on_perform=perform)
        event = ActionEvent()
        action.perform(event)
        self.assertEqual(memo, ['called'])

    def test_perform_none(self):
        action = Action(name='Test')
        event = ActionEvent()
        # does nothing, but shouldn't error
        action.perform(event)

    def test_destroy(self):
        action = Action(name='Test')
        # does nothing, but shouldn't error
        action.destroy()
