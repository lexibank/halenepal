# coding=utf-8
from __future__ import unicode_literals, print_function

from clldutils.misc import slug
from clldutils.path import Path
from pylexibank.dataset import Dataset as BaseDataset

from datatuples import Hale, STEDT


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "haleneapal"

    def cmd_download(self, **kw):
        pass

    def cmd_install(self, **kw):
        hale = []
        stedt = []
        languages, concepts = {}, {}

        for element in self.raw.read_tsv(self.raw / "Hale_raw.tsv"):
            if element:
                hale.append(Hale(*element))

        for element in self.raw.read_tsv(self.raw / "AH-CSDPN.tsv"):
            if element:
                stedt.append(STEDT(*element))

        with self.cldf as ds:
            for concept in self.concepts:
                ds.add_concept(
                    ID=concept["ID"],
                    Name=concept["GLOSS"],
                    Concepticon_ID=concept["CONCEPTICON_ID"],
                    Concepticon_Gloss=concept["CONCEPTICON_GLOSS"],
                )
                concepts[concept["GLOSS"]] = concept["ID"]

            for language in self.languages:
                ds.add_language(
                    ID=slug(language["GLOTTOLOG"]),
                    Glottocode=language["GLOTTOCODE"],
                    Name=language["LANGUAGE"],
                )
                languages[language["LANGUAGE"]] = slug(language["GLOTTOLOG"])

            print(languages)

            for h in hale:
                search = list(filter(lambda x: x.srcid == h.srcid, stedt))

                if search:
                    for result in search:
                        try:
                            ds.add_lexemes(
                                Language_ID=languages[result.language],
                                Parameter_ID=concepts[slug(result.gloss)],
                                Value=result.reflex,
                                Form=result.reflex,
                            )
                        except (KeyError, ValueError):
                            pass
