"""
Utility functions for LLM completions using litellm.
"""
from typing import List, Optional, Dict, Any, Union, Generator, Iterator, Tuple
from litellm import completion, stream_chunk_builder
from litellm.utils import ModelResponse


def _stream_chunks(response, messages) -> Iterator[Tuple[ModelResponse, ModelResponse]]:
    chunks = []
    for chunk in response:
        chunks.append(chunk)
        yield chunk, stream_chunk_builder(chunks, messages=messages)


def generate_completion(
    model: str,
    messages: List[Dict[str, str]],
    completion_params: Optional[Dict[str, Any]] = None,
    stream: bool = False,
) -> Union[ModelResponse, Dict[str, Any], Iterator[Tuple[ModelResponse, ModelResponse]]]:
    """
    Generate a completion using the specified LLM model via litellm.

    Args:
        model: The model identifier (e.g., "gpt-3.5-turbo", "claude-2")
        messages: List of message dictionaries with 'role' and 'content' keys
        completion_params: Dictionary of parameters to pass to litellm completion
            (e.g., temperature, max_tokens, etc.)
        stream: Whether to stream the response

    Returns:
        If stream=False: ModelResponse or dict containing the completion response
        If stream=True: Iterator yielding (delta, snapshot) pairs where:
            - delta: The new chunk (ModelResponse)
            - snapshot: Complete response up to this point (ModelResponse)

    Raises:
        Exception: If there's an error during completion generation
    """
    try:
        params = {"model": model, "messages": messages, "stream": stream}
        if completion_params:
            params.update(completion_params)
            
        response = completion(**params)
        
        # If streaming is enabled, return streaming iterator
        if stream:
            return _stream_chunks(response, messages)
        
        # For non-streaming responses, return as before
        return response
    except Exception as e:
        # Re-raise the exception with additional context
        raise Exception(f"Error generating completion with model {model}: {str(e)}") from e
