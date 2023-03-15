from marvin.utilities.types import get_id_type

# Generic IDs can match any prefixed ID but generate IDs with the "id" prefix.
GenericID = get_id_type(prefix=None)

# Specific IDs are for specific models and generate IDs with the model's prefix.
BotID = get_id_type(prefix="bot")
ThreadID = get_id_type(prefix="thr")
MessageID = get_id_type(prefix="msg")
TopicID = get_id_type(prefix="top")
