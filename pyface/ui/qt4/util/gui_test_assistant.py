# Copyright (c) 2013-2017 by Enthought, Inc., Austin, TX
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in enthought/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
# Thanks for using Enthought open source!

import contextlib
import threading

import mock

from pyface.qt.QtGui import QApplication
from pyface.ui.qt4.gui import GUI
from traits.testing.unittest_tools import UnittestTools
from traits.testing.unittest_tools import _TraitsChangeCollector as \
    TraitsChangeCollector

from .testing import find_qt_widget, print_qt_widget_tree
from .event_loop_helper import EventLoopHelper, ConditionTimeoutError


class GuiTestAssistant(UnittestTools):

    #### 'TestCase' protocol ##################################################

    def setUp(self):
        qt_app = QApplication.instance()
        if qt_app is None:
            qt_app = QApplication([])
        self.qt_app = qt_app
        self.gui = GUI()
        self.event_loop_helper = EventLoopHelper(
            qt_app=self.qt_app,
            gui=self.gui
        )
        self.traitsui_raise_patch = mock.patch(
            'traitsui.qt4.ui_base._StickyDialog.raise_')
        self.traitsui_raise_patch.start()

        def new_activate(self):
            self.control.activateWindow()

        self.pyface_raise_patch = mock.patch(
            'pyface.ui.qt4.window.Window.activate',
            new_callable=lambda: new_activate)
        self.pyface_raise_patch.start()

    def tearDown(self):
        with self.event_loop_with_timeout(repeat=5):
            self.gui.invoke_later(self.qt_app.closeAllWindows)
        self.qt_app.flush()
        self.qt_app.quit()
        self.pyface_raise_patch.stop()
        self.traitsui_raise_patch.stop()

        del self.pyface_raise_patch
        del self.traitsui_raise_patch
        del self.event_loop_helper
        del self.gui
        del self.qt_app

    #### 'GuiTestAssistant' protocol ##########################################

    @contextlib.contextmanager
    def event_loop(self, repeat=1):
        """Artificially replicate the event loop by Calling sendPostedEvents
        and processEvents ``repeat`` number of times. If the events to be
        processed place more events in the queue, begin increasing the value
        of ``repeat``, or consider using ``event_loop_until_condition``
        instead.

        Parameters
        ----------
        repeat : int
            Number of times to process events.
        """
        yield
        self.event_loop_helper.event_loop(repeat=repeat)

    @contextlib.contextmanager
    def delete_widget(self, widget, timeout=1.0):
        """Runs the real Qt event loop until the widget provided has been
        deleted.

        Parameters
        ----------
        widget : QObject
            The widget whose deletion will stop the event loop.
        timeout : float
            Number of seconds to run the event loop in the case that the
            widget is not deleted.
        """
        try:
            with self.event_loop_helper.delete_widget(widget, timeout=timeout):
                yield
        except ConditionTimeoutError:
            self.fail('Could not destroy widget before timeout: {!r}'.format(
                widget))

    @contextlib.contextmanager
    def event_loop_until_condition(self, condition, timeout=10.0):
        """Runs the real Qt event loop until the provided condition evaluates
        to True.

        This should not be used to wait for widget deletion. Use
        delete_widget() instead.

        Parameters
        ----------
        condition : callable
            A callable to determine if the stop criteria have been met. This
            should accept no arguments.
        timeout : float
            Number of seconds to run the event loop in the case that the
            condition is not satisfied.
        """
        try:
            yield
            self.event_loop_helper.event_loop_until_condition(
                condition, timeout=timeout)
        except ConditionTimeoutError:
            self.fail('Timed out waiting for condition')

    @contextlib.contextmanager
    def assertTraitChangesInEventLoop(self, obj, trait, condition, count=1,
                                      timeout=10.0):
        """Runs the real Qt event loop, collecting trait change events until
        the provided condition evaluates to True.

        Parameters
        ----------
        obj : HasTraits
            The HasTraits instance whose trait will change.
        trait : str
            The extended trait name of trait changes to listen to.
        condition : callable
            A callable to determine if the stop criteria have been met. This
            should accept no arguments.
        count : int
            The expected number of times the event should be fired. The default
            is to expect one event.
        timeout : float
            Number of seconds to run the event loop in the case that the trait
            change does not occur.
        """
        condition_ = lambda: condition(obj)
        collector = TraitsChangeCollector(obj=obj, trait=trait)

        collector.start_collecting()
        try:
            try:
                yield collector
                self.event_loop_helper.event_loop_until_condition(
                    condition_, timeout=timeout)
            except ConditionTimeoutError:
                actual_event_count = collector.event_count
                msg = ("Expected {} event on {} to be fired at least {} "
                       "times, but the event was only fired {} times "
                       "before timeout ({} seconds).")
                msg = msg.format(
                    trait, obj, count, actual_event_count, timeout)
                self.fail(msg)
        finally:
            collector.stop_collecting()

    @contextlib.contextmanager
    def event_loop_until_traits_change(self, traits_object, *traits, **kw):
        """Run the real application event loop until a change notification for
        all of the specified traits is received.

        Paramaters
        ----------
        traits_object : HasTraits instance
            The object on which to listen for a trait events
        traits : one or more str
            The names of the traits to listen to for events
        timeout : float, optional, keyword only
            Number of seconds to run the event loop in the case that the trait
            change does not occur. Default value is 10.0.
        """
        timeout = kw.pop('timeout', 10.0)
        condition = threading.Event()

        traits = set(traits)
        recorded_changes = set()

        # Correctly handle the corner case where there are no traits.
        if not traits:
            condition.set()

        def set_event(trait):
            recorded_changes.add(trait)
            if recorded_changes == traits:
                condition.set()

        def make_handler(trait):
            def handler():
                set_event(trait)
            return handler

        handlers = {trait: make_handler(trait) for trait in traits}

        for trait, handler in list(handlers.items()):
            traits_object.on_trait_change(handler, trait)
        try:
            with self.event_loop_until_condition(
                    condition=condition.is_set, timeout=timeout):
                yield
        finally:
            for trait, handler in list(handlers.items()):
                traits_object.on_trait_change(handler, trait, remove=True)

    @contextlib.contextmanager
    def event_loop_with_timeout(self, repeat=2, timeout=10.0):
        """Helper context manager to send all posted events to the event queue
        and wait for them to be processed.

        This differs from the `event_loop()` context manager in that it
        starts the real event loop rather than emulating it with
        `QApplication.processEvents()`

        Parameters
        ----------
        repeat : int
            Number of times to process events. Default is 2.
        timeout : float, optional, keyword only
            Number of seconds to run the event loop in the case that the trait
            change does not occur. Default value is 10.0.
        """
        yield
        self.event_loop_helper.event_loop_with_timeout(
            repeat=repeat, timeout=timeout)

    def find_qt_widget(self, start, type_, test=None):
        """Recursively walks the Qt widget tree from Qt widget `start` until it
        finds a widget of type `type_` (a QWidget subclass) that
        satisfies the provided `test` method.

        Parameters
        ----------
        start : QWidget
            The widget from which to start walking the tree
        type_ : type
            A subclass of QWidget to use for an initial type filter while
            walking the tree
        test : callable
            A filter function that takes one argument (the current widget being
            evaluated) and returns either True or False to determine if the
            widget matches the required criteria.
        """
        return find_qt_widget(start, type_, test=test)
