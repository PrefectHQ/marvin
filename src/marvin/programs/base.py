import abc


class Program(abc.ABC):
    @abc.abstractmethod
    async def run(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)
