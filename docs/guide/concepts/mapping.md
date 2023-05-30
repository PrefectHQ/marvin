# 🪭 Mapping 

Sometimes you may want to apply an AI function or AI model over a whole iterable of items. For example, you may want to perform a sentiment analysis with an `ai_fn` over a list of tweets, or coerce a list of documents into a list of `ai_model`s.

At scale it can be quite slow to process each item sequentially, so Marvin provides a `.map` method that allows you to process items concurrently, or in parallel - [powered by Prefect](https://docs.prefect.io/latest/concepts/tasks/?h=.map#map).

!!! tip
    The `.map` method was released in `marvin==0.9.2`.


## Mapping `ai_fn` over an iterable

```python
from marvin import ai_fn

@ai_fn(llm_model_name="gpt-3.5-turbo")
def opposite(something: str) -> str:
    """Return the opposite of `something`"""

opposites = opposite.map(["up", "hot", "heads"])

print(opposites)
```

Calling `.map` on an AI function will spin up a Prefect flow, with one task per item in the iterable. The tasks will be executed concurrently, and the results will be returned as a list:
```bash
08:47:14.727 | INFO    | prefect.engine - Created flow run 'meaty-viper' for flow 'opposite'
08:47:15.626 | INFO    | Flow run 'meaty-viper' - Created task run 'opposite-1' for task 'opposite'
08:47:15.628 | INFO    | Flow run 'meaty-viper' - Submitted task run 'opposite-1' for execution.
08:47:15.657 | INFO    | Flow run 'meaty-viper' - Created task run 'opposite-2' for task 'opposite'
08:47:15.658 | INFO    | Flow run 'meaty-viper' - Submitted task run 'opposite-2' for execution.
08:47:15.722 | INFO    | Flow run 'meaty-viper' - Created task run 'opposite-0' for task 'opposite'
08:47:15.723 | INFO    | Flow run 'meaty-viper' - Submitted task run 'opposite-0' for execution.
08:47:16.781 | INFO    | Task run 'opposite-2' - Finished in state Completed()
08:47:16.790 | INFO    | Task run 'opposite-0' - Finished in state Completed()
08:47:17.018 | INFO    | Task run 'opposite-1' - Finished in state Completed()
08:47:17.170 | INFO    | Flow run 'meaty-viper' - Finished in state Completed('All states completed.')
['down', 'cold', 'tails']
```

## Mapping `ai_model` over an iterable
Similarly, you can call `.map` on an AI model to process each item in the iterable with the model. The results will be returned as a list of hydrated models:

```python
from marvin import ai_model

@ai_model(llm_model_name="gpt-3.5-turbo")
class Location(BaseModel):
    city: str
    country: str
    latitute: float
    longitude: float

locations = Location.map(["windy city", "big apple", "mile high city"])

print(locations)

# [
#   Location(city='Chicago',country='United States', latitute=41.8781, longitude=-87.6298),
#   Location(city='New York', country='United States', latitute=40.7128, longitude=-74.006),
#   Location(city='Denver', country='United States', latitute=39.7392, longitude=-104.9903)
# ]

```

!!! tip
    The `.map` method is powered by Prefect, and you can run `prefect server start` to get an observability into your AI workloads for free. You can also sign up for a free [Prefect Cloud](https://www.prefect.io/cloud) account to get a hosted version of Prefect Server.

## Caching results
Now that each ai function or ai model is being executed as a Prefect task, you can take advantage of Prefect's [caching](https://docs.prefect.io/latest/concepts/tasks/#caching) feature to avoid re-processing items / paying for duplicate AI calls.

Let's add one import to our example above to enable caching:
```python
from prefect.tasks import task_input_hash
from marvin import ai_fn

@ai_fn(llm_model_name="gpt-3.5-turbo")
def opposite(something: str) -> str:
    """Return the opposite of `something`"""

opposites = opposite.map(
    ["up", "hot", "heads"],
    task_kwargs=dict(cache_key_fn=task_input_hash)
)

print(opposites)
```
After the first execution, the results can be pulled from cache and subsequent executions will be much faster (and free 🙂):
```bash hl_lines="8,9,10"
09:08:46.428 | INFO    | prefect.engine - Created flow run 'fantastic-caterpillar' for flow 'opposite'
09:08:47.116 | INFO    | Flow run 'fantastic-caterpillar' - Created task run 'opposite-2' for task 'opposite'
09:08:47.118 | INFO    | Flow run 'fantastic-caterpillar' - Submitted task run 'opposite-2' for execution.
09:08:47.134 | INFO    | Flow run 'fantastic-caterpillar' - Created task run 'opposite-1' for task 'opposite'
09:08:47.135 | INFO    | Flow run 'fantastic-caterpillar' - Submitted task run 'opposite-1' for execution.
09:08:47.156 | INFO    | Flow run 'fantastic-caterpillar' - Created task run 'opposite-0' for task 'opposite'
09:08:47.156 | INFO    | Flow run 'fantastic-caterpillar' - Submitted task run 'opposite-0' for execution.
09:08:47.349 | INFO    | Task run 'opposite-2' - Finished in state Cached(type=COMPLETED)
09:08:47.372 | INFO    | Task run 'opposite-0' - Finished in state Cached(type=COMPLETED)
09:08:47.375 | INFO    | Task run 'opposite-1' - Finished in state Cached(type=COMPLETED)
09:08:47.496 | INFO    | Flow run 'fantastic-caterpillar' - Finished in state Completed('All states completed.')
['down', 'cold', 'tails']
```

!!! tip
    See the docs on Prefect tasks to see all the different [task configuration options](https://docs.prefect.io/latest/tutorial/flow-task-config/)! For example, you can achieve true parallelism with `task_runner=DaskTaskRunner()`, or you can use `retries=2` to retry failed tasks.