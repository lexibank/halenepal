import re
from collections import namedtuple
from pathlib import Path

import attr
import pylexibank
from clldutils.misc import slug
from csvw import Datatype
from pylexibank import Language
from pylexibank.dataset import Dataset as NonSplittingDataset
from pylexibank.util import progressbar

STEDT = namedtuple(
    "STEDT", ["rn", "reflex", "gloss", "gfn", "srcabbr", "lgid", "language", "srcid"]
)
Hale = namedtuple("Hale", ["id", "gloss", "srcid"])


@attr.s
class CustomLanguage(Language):
    ChineseName = attr.ib(default=None)
    Population = attr.ib(default=None)
    SubGroup = attr.ib(default=None)
    Number = attr.ib(default=None)


class Dataset(NonSplittingDataset):
    dir = Path(__file__).parent
    id = "halenepal"
    language_class = CustomLanguage
    form_spec = pylexibank.FormSpec(
        brackets={"(": ")"},
        separators=";/,",
        missing_data=("?", "-", "*", "---"),
        strip_inside_brackets=True,
    )

    def cmd_makecldf(self, args):
        hale, stedt = [], []
        reps = [("XIII", "13"), ("XII", "12"), ("A", "a."), ("B", "b."), ("C", "c."), ("D", "d.")]
        # correct individual errors
        mapper = {
            "01.009": "01.009",
            "XIIC56": "12c.56",
            "XIIC64": "12c.64",
            "XIID31": "12d.31",
            "XIID14": "12d.14",
        }

        # correct srcids
        fromconcepts = {}
        for element in self.raw_dir.read_csv("srcids.tsv", delimiter="\t"):
            if element:
                fromconcepts[element[-1]] = element[-2]

        hsrcids = set()
        for element in self.raw_dir.read_csv("Hale_raw.tsv", delimiter="\t"):
            if element:
                hale.append(Hale(*element))
                hsrcids.add(element[-1])

        missing = set()
        for element in self.raw_dir.read_csv("AH-CSDPN.tsv", delimiter="\t")[1:]:
            if element:
                srcid = fromconcepts.get(element[2], element[-1])
                element[-1] = srcid
                if srcid in hsrcids:
                    stedt.append(STEDT(*element))

                else:
                    for elm in re.split("[,;]", element[-1]):  # .split(';'):
                        for s, t in reps:
                            elm = elm.replace(s, t)
                        elm = mapper.get(elm, elm)
                        if elm:
                            if elm not in hsrcids:
                                missing.add((elm, element[-1], element[2]))
                            else:
                                mapper[element[-1]] = elm
                                stedt.append(STEDT(*[x for x in element[:-1]] + [elm]))

        for i, y in enumerate(missing):
            print("{0:5} | {1:10} | {2:10} | {3}".format(i + 1, y[0], y[1], y[2]))

        args.writer.tokenize = lambda x, z: " ".join(
            self.tokenizer(x, "^" + z + "$", column="IPA")
        ).split(" + ")

        # add data to cldf
        args.writer["FormTable", "Segments"].separator = " + "
        args.writer["FormTable", "Segments"].datatype = Datatype.fromvalue(
            {"base": "string", "format": "([\\S]+)( [\\S]+)*"}
        )

        args.writer.add_sources()

        concept_check = args.writer.add_concepts(
            id_factory=lambda x: x.id.split("-")[-1] + "_" + slug(x.english)
        )
        language_lookup = args.writer.add_languages(lookup_factory="Name")

        concept_lookup = {}
        for h in hale:
            concept_lookup[h.srcid] = h.id.split("-")[-1] + "_" + slug(h.gloss)

        for entry in progressbar(stedt):
            if concept_lookup[entry.srcid] in concept_check:
                args.writer.add_forms_from_value(
                    Local_ID=entry.rn,
                    Language_ID=language_lookup[entry.language],
                    Parameter_ID=concept_lookup[entry.srcid],
                    Value=entry.reflex,
                    Source=["Hale1973"],
                )
