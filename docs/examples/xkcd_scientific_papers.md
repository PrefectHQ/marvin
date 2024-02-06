# xkcd scientific paper classifier

[![](https://imgs.xkcd.com/comics/types_of_scientific_paper_2x.png){width="550"}](https://xkcd.com/2456/)


!!! example "What kind of paper is 'Attention is All You Need'?"

    The xkcd comic defines 12—and only 12—types of scientific papers. This example extracts those labels and uses them to classify the paper that introduced transformer models, "[Attention is All You Need](https://arxiv.org/abs/1706.03762)."

    ```python
    import marvin


    # extract the types of papers from the xkcd comic
    paper_types = marvin.beta.extract(
        data=marvin.beta.Image(
            "https://imgs.xkcd.com/comics/types_of_scientific_paper_2x.png"
        ), 
        instructions="Extract the types of papers from the comic",
    )

    
    # use them to classify the attention paper
    attention_text = get_text_from_pdf("https://arxiv.org/pdf/1706.03762.pdf")
    attention_type = marvin.classify(attention_text, labels=paper_types)
    ```

    !!! success "Result"
        ```python
        assert attention_type == (
            "Hey, at least we showed that this method can produce results! "
            "That's not nothing, right?"
        )
        ```

In the above example, the `get_text_from_pdf` function may be defined as:
```python
import fitz # pip install PyMuPDF, not included in Marvin's dependencies

def get_text_from_pdf(pdf_url: str) -> str:
    # Fetch the PDF file content from the URL
    response = requests.get(pdf_url)
    response.raise_for_status()  # Ensure the request was successful
    # Open the PDF from the fetched bytes
    pdf_bytes = response.content
    pdf_stream = fitz.open(stream=pdf_bytes, filetype="pdf")
    # Extract text from each page
    text = ""
    for page in pdf_stream:
        text += page.get_text()
    pdf_stream.close()  # Close the PDF stream
    return text
```