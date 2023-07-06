# AI Classifier

## Use Large Language Models to *classify user input*.
`ai_classifier` is a decorator that employs the power of Large Language Models to classify provided input into predefined categories. It enables a flexible way of classifying information based on context, surpassing conventional, rigid rule-based methods. It takes advantage of the deductive capability of Large Language Models to deduce labels from its internal context.

!!! note

    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla et euismod
    nulla. Curabitur feugiat, tortor non consequat finibus, justo purus auctor
    massa, nec semper lorem quam in massa.

```python
@ai_classifier
def classify_user_intent(
    text: str, 
    options = ['billing', 'returns', 'rescheduling']
) -> list[str]:
    """
    Returns customer's intent from live chat conversation
    """
```

```python
@ai_classifier
def smart_router(
    text: str, 
    options = ['/home', '/features', '/support']
) -> list[str]:
    """
    Returns users's command bar intent to navigate to correct page
    """
```

## Bulletproof, fast, and cost-effective classification. 

`ai_classifier` is a bulletproof, lightning fast and cost-effiective drop-in for classification tasks where 
you have little-to-no training data. It constrains Large Language Models using logit_bias to 
force a single-token choice representing your presented options.

## No Prompting Required

If you can write python, you can use ai_classifier. No prompts required.
We use your class labels to craft a templated prompt.
We send that prompt to a Large Language Model to infer new input's class.

## No Machine Learning Required

`ai_classifier` is especially useful for classifiers that would be difficult, time-consuming, or impossible to code. 

## Rapidly prototype natural language classification pipelines

 Classify data that would be impossible or prohibitively expensive to classify using rule-based or statistical methods, as you rapidly prototype NLP pipelines.

### Classify Sentiment

```python

@ai_classifier
def classify_tweet_sentiment(tweet: str, sentiment_options: list[str]) -> str:
    """
    Classifies the sentiment of a given tweet.
    """
```

### Classify Intent

```python

@ai_classifier
def classify_news_article(article: str, categories: list[str]) -> str:
    """
    Classifies the category of an unseen recipe.
    """
```
