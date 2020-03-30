from collections import defaultdict
from pathlib import Path

import attr
import pylexibank
from clldutils.misc import slug
from csvw import Datatype
from pylexibank import Language, Concept
from pylexibank.dataset import Dataset as NonSplittingDataset
from pylexibank.util import progressbar


@attr.s
class CustomLanguage(Language):
    ChineseName = attr.ib(default=None)
    Population = attr.ib(default=None)
    SubGroup = attr.ib(default=None)
    Number = attr.ib(default=None)


@attr.s
class CustomConcept(Concept):
    Number = attr.ib(default=None)


class Dataset(NonSplittingDataset):
    dir = Path(__file__).parent
    id = "halenepal"
    language_class = CustomLanguage
    concept_class = CustomConcept
    form_spec = pylexibank.FormSpec(
        brackets={"(": ")"},
        separators=";/,",
        missing_data=("?", "-", "*", "---"),
        strip_inside_brackets=True,
    )

    def cmd_makecldf(self, args):
        # due to bad concept ids in STEDT, we need to load them from file
        converter = defaultdict(set)
        for row in self.raw_dir.read_csv("srcids.tsv", delimiter="\t", dicts=True):
            converter[row["CORRECTED"]].add(row["IDINSTEDT"])

        concept_lookup = {}
        for concept in self.conceptlists[0].concepts.values():
            idx = concept.id.split("-")[-1] + "_" + slug(concept.english)
            args.writer.add_concept(
                ID=idx,
                Name=concept.english,
                Concepticon_ID=concept.concepticon_id,
                Concepticon_Gloss=concept.concepticon_gloss,
                Number=concept.number,
            )
            concept_lookup[concept.number] = idx
            for id_in_source in converter[concept.number]:
                concept_lookup[id_in_source] = idx

        language_lookup = args.writer.add_languages(lookup_factory="Name")
        args.writer.add_sources()

        # account for segmented data
        args.writer.tokenize = lambda x, z: " ".join(
            self.tokenizer(x, "^" + z + "$", column="IPA")
        ).split(" + ")
        args.writer["FormTable", "Segments"].separator = " + "
        args.writer["FormTable", "Segments"].datatype = Datatype.fromvalue(
            {"base": "string", "format": "([\\S]+)( [\\S]+)*"}
        )
        for row in progressbar(self.raw_dir.read_csv("AH-CSDPN.tsv", delimiter="\t")[1:]):
            args.writer.add_forms_from_value(
                Local_ID=row[0],
                Language_ID=language_lookup[row[6]],
                Parameter_ID=concept_lookup[row[7]],
                Value=row[1],
                Source=["Hale1973"],
            )
