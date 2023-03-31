from marvin import ai_fn


@ai_fn()
def make_decorator() -> list[str]:
    """
    Returns Python code for a python decorator function that logs the activity of a function.
    Use functools wraps.  # added this line for the second example
    """


print(make_decorator())

# ["def log_decorator(func):\n    \n    def wrapper(*args, **kwargs):\n        with open('log.txt', 'a') as file:\n            file.write('Function '+func.__name__+' was called with arguments '+str(args)+' '+str(kwargs)+'\\n')\n        return func(*args,**kwargs)\n    \n    return wrapper"]
# ["def decorator(func):\n    import logging\n    from functools import wraps\n    logging.basicConfig(filename='{}.log'.format(func.__name__), level=logging.INFO)\n\n    @wraps(func)\n    def wrapper(*args, **kwargs):\n        logging.info('Ran with args: {}, and kwargs: {}'.format(args, kwargs))\n        return func(*args, **kwargs)\n    return wrapper"]
