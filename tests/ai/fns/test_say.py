import pydantic_ai.models
from pydantic_ai.models.test import TestModel

import marvin
from marvin.defaults import override_defaults


class TestSay:
    def test_say(self):
        result = marvin.say("Hello")
        assert result

    def test_say_adds_user_message(self):
        thread = marvin.Thread()
        marvin.say("abc123", thread=thread)
        messages = thread.get_messages()
        assert messages[0].message.parts[0].part_kind == "user-prompt"
        assert messages[0].message.parts[0].content == "abc123"

    def test_say_with_thread(self):
        thread1 = marvin.Thread()
        thread2 = marvin.Thread()

        assert (l1 := len(thread1.get_messages())) == 0
        assert (l2 := len(thread2.get_messages())) == 0

        marvin.say("Hello", thread=thread1)
        assert (l1_1 := len(thread1.get_messages())) > l1
        assert len(thread2.get_messages()) == l2

        marvin.say("Hello", thread=thread2)
        assert len(thread1.get_messages()) == l1_1
        assert (l2_1 := len(thread2.get_messages())) > l2

        marvin.say("Hello", thread=thread1)
        assert len(thread1.get_messages()) > l1_1
        assert len(thread2.get_messages()) == l2_1

    def test_say_with_context_thread(self):
        thread1 = marvin.Thread()
        thread2 = marvin.Thread()

        assert (l1 := len(thread1.get_messages())) == 0
        assert (l2 := len(thread2.get_messages())) == 0

        with thread1:
            marvin.say("Hello")
        assert (l1_1 := len(thread1.get_messages())) > l1
        assert len(thread2.get_messages()) == l2

        with thread2:
            marvin.say("Hello")

        assert len(thread1.get_messages()) == l1_1
        assert (l2_1 := len(thread2.get_messages())) > l2

        with thread1:
            marvin.say("Hello")
        assert len(thread1.get_messages()) > l1_1
        assert len(thread2.get_messages()) == l2_1

    def test_say_with_string_thread(self):
        thread1 = marvin.Thread()
        thread2 = marvin.Thread()

        assert (l1 := len(thread1.get_messages())) == 0
        assert (l2 := len(thread2.get_messages())) == 0

        marvin.say("Hello", thread=thread1.id)
        assert (l1_1 := len(thread1.get_messages())) > l1
        assert len(thread2.get_messages()) == l2

        marvin.say("Hello", thread=thread2.id)

        assert len(thread1.get_messages()) == l1_1
        assert (l2_1 := len(thread2.get_messages())) > l2

        marvin.say("Hello", thread=thread1.id)
        assert len(thread1.get_messages()) > l1_1
        assert len(thread2.get_messages()) == l2_1


class TestContextIsolation:
    def test_say_does_not_mutate_caller_context(self):
        """A caller-supplied `context` dict must not be mutated in place.

        `say_async` used to do `task_context = context or {}` and then
        write into `task_context` directly, which aliases (rather than
        copies) any non-empty caller-supplied dict.
        """
        with pydantic_ai.models.override_allow_model_requests(False):
            with override_defaults(model=TestModel()):
                my_context = {"user_supplied_key": "should not change"}
                before = dict(my_context)

                marvin.say("hello", instructions="be nice", context=my_context)

                assert my_context == before
