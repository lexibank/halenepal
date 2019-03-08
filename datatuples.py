from collections import namedtuple

STEDT = namedtuple(
    "STEDT",
    ["rn", "reflex", "gloss", "gfn", "srcabbr", "lgid", "language", "srcid"],
)
Hale = namedtuple("Hale", ["id", "gloss", "srcid"])
