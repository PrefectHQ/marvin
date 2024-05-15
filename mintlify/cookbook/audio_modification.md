# Modifying user audio

By combining a few Marvin tools, you can quickly record a user, transcribe their speech, modify it, and play it back.

!!! info "Audio extra"
    This example requires the `audio` extra to be installed in order to record and play sound:

    ```bash
    pip install marvin[audio]
    ```


!!! example "Modifying user audio"
    ```python
    import marvin
    import marvin.audio

    # record the user
    user_audio = marvin.audio.record_phrase()

    # transcribe the text
    user_text = marvin.transcribe(user_audio)

    # cast the language to a more formal style
    ai_text = marvin.cast(
        user_text, 
        instructions="Make the language ridiculously formal",
    )

    # generate AI speech
    ai_audio = marvin.speak(ai_text)

    # play the result
    ai_audio.play()
    ```

    !!! quote "User audio"
        "This is a test."
        
        <audio controls>
            <source src="/assets/audio/this_is_a_test.mp3" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
        

    !!! success "Marvin audio"
        "This constitutes an examination."
        
        <audio controls>
            <source src="/assets/audio/this_is_a_test_2.mp3" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
