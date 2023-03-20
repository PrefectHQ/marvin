import inspect

from marvin.bots.utility_bots import UtilityBot
from marvin.programs import Program


class ApproximatelyEquivalent(Program):
    """
    Determines if two statements are approximately (semantically) equivalent.
    """

    async def run(self, statement_1: str, statement_2: str):
        bot = UtilityBot(
            instructions=inspect.cleandoc(
                """
                The user will give you two statements. Your only job is to
                determine if the two statements are approximately equivalent.
                You will respond ONLY with either the word `true` or `false`. Do
                not say anything else, for any reason.
                """
            )
        )

        message = inspect.cleandoc(
            """
            # Statement 1
            {statement_1}
            
            # Statement 2
            {statement_2}
            """
        ).format(statement_1=statement_1, statement_2=statement_2)

        response = await bot.say(message)
        if response.content.lower() == "true":
            return True
        else:
            return False
