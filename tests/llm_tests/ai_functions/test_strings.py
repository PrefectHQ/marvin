import pytest
from dateutil.rrule import rrulestr
from marvin.ai_functions import strings as string_fns


class TestFixCapitalization:
    def test_fix_capitalization(self, gpt_4):
        result = string_fns.fix_capitalization("the european went over to canada, eh?")
        assert result == "The European went over to Canada, eh?"


class TestTitleCase:
    def test_title_case(self):
        result = string_fns.title_case("the european went over to canada, eh?")
        assert result == "The European Went Over to Canada, Eh?"

    def test_short_prepositions_not_capitalized(self):
        result = string_fns.title_case("let me go to the store")

        assert result == "Let Me Go to the Store"


class TestRRule:
    @pytest.mark.parametrize(
        "description, rrule",
        [
            ("every day at 9am", "RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0;BYSECOND=0"),
            (
                "every other day and 9am and 1pm",
                "RRULE:FREQ=DAILY;INTERVAL=2;BYHOUR=9,13;BYMINUTE=0;BYSECOND=0",
            ),
            (
                "9am on the first business day of the quarter",
                "RRULE:FREQ=MONTHLY;BYSETPOS=1;BYDAY=MO,TU,WE,TH,FR;BYMONTH=1,4,7,10;BYHOUR=9;BYMINUTE=0;BYSECOND=0;BYWEEKNO=1,14,27,40",
            ),
        ],
    )
    def test_rrules(self, description, rrule):
        result = string_fns.rrule(description)
        assert str(rrulestr(result)) == str(rrulestr(rrule))
