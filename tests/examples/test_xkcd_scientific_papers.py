import fitz
import marvin
import pytest
import requests

PAPER_TYPES = [
    "We put a camera somewhere new",
    (
        "Hey, I found a trove of old records! They don't turn out to be"
        " particularly useful, but still, cool!"
    ),
    "My colleague is wrong and I can finally prove it",
    "The immune system is at it again",
    "We figured out how to make this exotic material, so email us if you need some",
    "What are fish even doing down there",
    "This task I had to do anyway turned out to be hard enough for its own paper",
    (
        "Hey, at least we showed that this method can produce results! That's not"
        " nothing, right?"
    ),
    "Check out this weird thing one of us saw while out for a walk",
    "We are 500 scientists and here's what we've been up to for the last 10 years",
    "Some thoughts on how everyone else is bad at research",
    "We scanned some undergraduates",
]


def extract_text_from_pdf_url(pdf_url: str) -> str:
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


@pytest.mark.flaky(max_runs=3)
def test_extract_labels(gpt_4):
    # extract labels from the comic
    paper_types = marvin.beta.extract(
        data=marvin.beta.Image(
            "https://imgs.xkcd.com/comics/types_of_scientific_paper_2x.png"
        ),
        instructions=(
            "Extract the types of papers from the comic (using sentence casing)"
        ),
    )

    assert paper_types == PAPER_TYPES


def test_classify_paper(gpt_4):
    # classify the paper
    paper_text = extract_text_from_pdf_url("https://arxiv.org/pdf/1706.03762.pdf")
    result = marvin.classify(paper_text, labels=PAPER_TYPES)
    assert (
        result == "Hey, at least we showed that this method can produce results! "
        "That's not nothing, right?"
    )
