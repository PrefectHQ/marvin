# Augmenting prompts with Python

## Web scraping

!!! example "Fetch rich prompt material with Python"

    Using an http client to fetch HTML that an LLM will filter for a `list[RelatedArticle]`:
    
    ```python
    import bs4
    import httpx
    import marvin
    from typing_extensions import TypedDict

    class RelatedArticle(TypedDict):
        title: str
        link: str


    @marvin.fn
    def retrieve_HN_articles(topic: str | None = None) -> list[RelatedArticle]:
        """Retrieve only articles from HN that are related to a given topic"""
        response = httpx.get("https://news.ycombinator.com/")
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        return [
            (link.text, link['href']) for link in soup.select('.titleline a')
        ]
    
    retrieve_HN_articles("rust")
    ```
    

    !!! success "Result"
        ```python
        [
            {
                'title': 'A lowering strategy for control effects in Rust',
                'link': 'https://www.abubalay.com/blog/2024/01/14/rust-effect-lowering'
            },
            {
                'title': 'Show HN: A minimal working Rust / SDL2 / WASM browser game',
                'link': 'https://github.com/awwsmm/hello-rust-sdl2-wasm'
            }
        ]
        ```

    !!! Tip "Note"
        You could also use `marvin.extract` to extract the `list[RelatedArticle]` from the output of the un-decorated function `retrieve_HN_articles`:
        
        ```python
        related_articles = marvin.extract(retrieve_HN_articles(), RelatedArticle)
        ```
    

## Vectorstore-based RAG

!!! example "Stuff `top k` document excerpts into a prompt"

    Using an http client to fetch HTML that an LLM will filter for a `list[RelatedArticle]`:
    
    ```python
    from typing_extensions import TypedDict
    import marvin
    from marvin.tools.chroma import query_chroma # you must have a vectorstore with embedded documents
    from marvin.utilities.asyncio import run_sync

    class Answer(TypedDict):
        answer: str
        supporting_links: list[str] | None

    @marvin.fn
    def answer_question(
        question: str,
        top_k: int = 2,
        style: str = "concise"
    ) -> Answer:
        """Answer a question given supporting context in the requested style"""
        return run_sync(query_chroma(question, n_results=top_k))
    
    answer_question("What are prefect blocks?", style="pirate")
    ```
    

    !!! success "Result"
        ```python
        {
            'answer': "Ahoy! Prefect blocks be a primitive within Prefect fer storin' configuration and interfacin' with th' external systems. Ye can use 'em to manage credentials and interact with services like AWS, GitHub, and Slack. Arr, they be comin' with methods for uploadin' or downloadin' data, among other actions, and ye can register new ones with Prefect Cloud or server.",
            'supporting_links': ['https://docs.prefect.io/latest/concepts/blocks/']
        }
        ```