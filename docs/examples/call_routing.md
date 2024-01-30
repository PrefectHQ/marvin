# Customer call routing

Automatically route customer calls to the right department.

!!! example "Call routing"
    ```python
    import marvin
    from enum import Enum

    # define departments as an Enum, with some additional instructions
    class Department(Enum):
        """Use `agent` when no other department is applicable."""
        SALES = "sales"
        SUPPORT = "support"
        BILLING = "billing"
        AGENT = "agent"


    # define a convenience function to route calls to the right department
    def router(text: str) -> Department:
        return marvin.classify(
            text,
            labels=Department,
            instructions="Select the best department for the customer request",
        )
    ```

    !!! success "Update payment method"
        ```python
        department = router("I need to update my payment method")
        assert department == Department.BILLING
        ```

    !!! success "Price matching"
        ```python
        department = router("Do you price match?")
        assert department == Department.SALES
        ```

    !!! success "Angry noises"
        ```python
        department = router("*angry noises*")
        assert department == Department.SUPPORT
        ```