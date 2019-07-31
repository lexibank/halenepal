import re
from collections import namedtuple

from clldutils.misc import slug
from clldutils.path import Path
from clldutils.text import strip_brackets, split_text
from csvw import Datatype
from pylexibank.dataset import Dataset as NonSplittingDataset
from pylexibank.dataset import Language
from tqdm import tqdm
import attr

STEDT = namedtuple(
    "STEDT", ["rn", "reflex", "gloss", "gfn", "srcabbr", "lgid", "language", "srcid"]
)
Hale = namedtuple("Hale", ["id", "gloss", "srcid"])

@attr.s
class HLanguage(Language):
    ChineseName = attr.ib(default=None)
    Population = attr.ib(default=None)
    Latitude = attr.ib(default=None)
    Longitude = attr.ib(default=None)
    SubGroup = attr.ib(default=None)


class Dataset(NonSplittingDataset):
    dir = Path(__file__).parent
    id = "halenepal"
    language_class = HLanguage

    def cmd_download(self, **kw):
        pass

    def clean_form(self, item, form):
        if form not in ["*", "---", "-"]:
            form = strip_brackets(split_text(form, separators=";,/")[0])
            return form

    def cmd_install(self, **kw):
        hale, stedt = [], []
        languages, concepts = {}, {}

        reps = [("XIII", "13"), ("XII", "12"), ("A", "a."), ("B", "b."), ("C", "c."), ("D", "d.")]

        mapper = {
            "01.009": "01.009",
            "XIIC56": "12c.56",
            "XIIC64": "12c.64",
            "XIID31": "12d.31",
            "XIID14": "12d.14",
        }

        # corrected srcids
        fromconcepts = {}
        for element in self.raw.read_tsv(self.raw / "srcids.tsv"):
            if element:
                fromconcepts[element[-1]] = element[-2]

        hsrcids = set()
        for element in self.raw.read_tsv(self.raw / "Hale_raw.tsv"):
            if element:
                hale.append(Hale(*element))
                hsrcids.add(element[-1])

        missing = set()
        for element in self.raw.read_tsv(self.raw / "AH-CSDPN.tsv")[1:]:
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

        with self.cldf as ds:
            self.cldf.tokenize = lambda x, z: " ".join(
                self.tokenizer(x, "^" + z + "$", column="IPA")
            ).split(" + ")

            # add data to cldf
            ds["FormTable", "Segments"].separator = " + "
            ds["FormTable", "Segments"].datatype = Datatype.fromvalue(
                {"base": "string", "format": "([\\S]+)( [\\S]+)*"}
            )

            ds.add_sources(*self.raw.read_bib())

            for concept in self.conceptlist.concepts.values():
                ds.add_concept(
                    ID=concept.id,
                    Name=concept.english,
                    Concepticon_ID=concept.concepticon_id,
                    Concepticon_Gloss=concept.concepticon_gloss,
                )

            concepts = {
                concept.english: concept.id for concept in self.conceptlist.concepts.values()
            }

            for language in self.languages:
                ds.add_language(
                    ID=language["ID"],
                    Glottocode=language["Glottocode"],
                    Name=language["Name"],
                    SubGroup=language['SubGroup'],
                    Family=language['Family']
                )
                languages[language["Name"]] = language["ID"]

            for h in hale:
                concepts[h.srcid] = h.id

            for entry in tqdm(stedt):
                ds.add_lexemes(
                    Local_ID=entry.rn,
                    Language_ID=languages[entry.language],
                    Parameter_ID=concepts[entry.srcid],
                    Value=entry.reflex,
                    Source=["Hale1973"],
                )
