import abc


class Program(abc.ABC):
    """
    Programs are "observable containers" for one or more bots. By providing a
    contained runtime environment, programs can be used to manage the
    interactions of bots with users, each other, and their own history, in
    addition to providing an opportunity to define structured inputs and
    outputs. Whereas bots are primarily conversational agents, programs are the
    glue that binds them together into reusable, callable functions.
    """

    @abc.abstractmethod
    async def run(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)
