# xkcd scientific paper classifier

[![](https://imgs.xkcd.com/comics/types_of_scientific_paper_2x.png){width="550"}](https://xkcd.com/2456/)


!!! example "What kind of paper is 'Attention is All You Need'?"

    This example extracts the types of papers from the comic and uses them to classify the paper "[Attention is All You Need](https://arxiv.org/abs/1706.03762)".

    ```python
    import marvin


    # extract labels from the comic
    paper_types = marvin.beta.extract(
        data=marvin.beta.Image(
            "https://imgs.xkcd.com/comics/types_of_scientific_paper_2x.png"
        ), 
        instructions="Extract the types of papers from the comic",
    )

    
    # classify the paper
    paper_text = load_paper("https://arxiv.org/pdf/1706.03762.pdf")
    result = marvin.classify(paper_text, labels=paper_types)
    ```

    !!! success "Result"
        ```python
        assert result == (
            "Hey, at least we showed that this method can produce results! "
            "That's not nothing, right?"
        )
        ```