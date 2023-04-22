from marvin.ai_functions import strings as string_fns


class TestFixCapitalization:
    def test_fix_capitalization(self):
        result = string_fns.fix_capitalization("the european went over to canada, eh?")
        assert result == "The European went over to Canada, eh?"


class TestTitleCase:
    def test_title_case(self):
        result = string_fns.title_case("the european went over to canada, eh?")
        assert result == "The European Went Over to Canada, Eh?"

    def test_short_prepositions_not_capitalized(self):
        result = string_fns.title_case(
            input="let me go to the store",
        )

        assert result == "Let Me Go to the Store"
