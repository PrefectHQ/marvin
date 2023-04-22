from marvin.ai_functions import strings as string_fns


class TestTitleCase:
    def test_short_prepositions_not_capitalized(self):
        result = string_fns.title_case(
            input="let me go to the store",
        )

        assert result == "Let Me Go to the store"
