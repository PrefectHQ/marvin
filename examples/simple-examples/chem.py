from marvin import ai_fn


@ai_fn()
def chemistry(n: int) -> list[str]:
    """Retuns the electron configuration of the valence electrons
    of an element with {n} protons
    """


print(chemistry(n=36))

# Responses: - none are just the valence electrons, using gpt-3.5.-turbo

# ['1s<sup>2</sup>', '2s<sup>2</sup>', '2p<sup>6</sup>',
# '3s<sup>2</sup>', '3p<sup>6</sup>', '4s<sup>2</sup>',
# '3d<sup>10</sup>', '4p<sup>6</sup>']

# ['[Kr] 5s2 4d10 5p6']

# ['1s2', '2s2', '2p6', '3s2', '3p6', '4s2', '3d10', '4p6']
