# from pydantic import BaseModel, Field

# import marvin
# from marvin.models.messages import Message


# class AIApplication(BaseModel):
#     model: Model = Field(default_factory=lambda: Model(model="gpt-3.5-turbo-0613"))
#     prompts: list[Prompt] = Field(default_factory=list)
#     history: History = Field(default_factory=History)

#     def trim_messages(
#         self,
#         messages: list[Message],
#         max_tokens: int = marvin.settings.llm_max_tokens,
#     ) -> list[Message]:
#         # Implement the trimming logic here
#         return messages

#     async def run(self, user_input: str):
#         self.history.add_message(user_input)
#         function_history = History()

#         self.model.prompts = self.prompts + [
#             MessageHistory(history=self.history),
#             MessageHistory(history=function_history, position=-1),
#         ]

#         while True:
#             # Render all prompts
#             messages = self.model.render_prompts()
#             trimmed_messages = self.trim_messages(messages)

#             # Call LLM
#             llm_output = await marvin.utilities.llms.call_llm_messages(
#                 llm=self.model,
#                 messages=trimmed_messages,
#             )

#             if llm_output.role == "FUNCTION":
#                 function_history.add_message(llm_output)
#             else:
#                 self.user_history.add_message(llm_output)
#                 return llm_output
