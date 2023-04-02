from marvin import ai_fn


@ai_fn
def name_playlist(songs: list[str]) -> str:
    """
    Come up with a short, evocative name for this playlist.
    """


songs = [
    "A.I. - One Republic",
    "Robot Rock - Daft Punk",
    "Robots - Flight of the Conchords",
    "The Girl and the Robot - Röyskopp",
    "The Grid - Daft Punk",
    "Think - Aretha Franklin",
]

name_playlist(songs)  # Robo Rhythms
