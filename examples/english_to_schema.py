import marvin

Movie = marvin.generate_schema("movie with a title, release year, and a list of actors")
print(marvin.cast("red or blue pill", target=Movie))
