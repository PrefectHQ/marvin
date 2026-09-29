import pydantic_ai.models
from pydantic_ai.models.test import TestModel

import marvin
from marvin.defaults import override_defaults


class TestContextIsolation:
    def test_plan_does_not_mutate_caller_context(self):
        """A caller-supplied `context` dict must not be mutated in place.

        `plan_async` used to do `task_context = context or {}` and then
        write into `task_context` directly, which aliases (rather than
        copies) any non-empty caller-supplied dict.
        """
        with pydantic_ai.models.override_allow_model_requests(False):
            with override_defaults(model=TestModel()):
                my_context = {"user_supplied_key": "should not change"}
                before = dict(my_context)

                marvin.plan("write a blog post", context=my_context)

                assert my_context == before
