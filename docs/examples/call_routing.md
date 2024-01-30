# Customer call routing

Automatically route customer calls to the right department.

!!! example "Call routing"
    ```python
    import marvin
    from enum import Enum


    class Department(Enum):
        SALES = "sales"
        SUPPORT = "support"
        BILLING = "billing"


    # define a convenience function
    def route_call(transcript: str) -> Department:
        return marvin.classify(
            transcript,
            labels=Department,
            instructions="Select the best department for the customer request",
        )
    ```

    !!! success "💳 Update payment method"
        ```python
        department = route_call("I need to update my payment method")
        assert department == Department.BILLING
        ```

    !!! success "💵 Price matching"
        ```python
        department = route_call("Well FooCo offered me a better deal")
        assert department == Department.SALES
        ```

    !!! success "🤬 Angry noises"
        ```python
        department = route_call("*angry noises*")
        assert department == Department.SUPPORT
        ```