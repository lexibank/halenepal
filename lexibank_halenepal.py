# coding=utf-8
from __future__ import unicode_literals, print_function

from clldutils.misc import slug
from clldutils.path import Path
from pylexibank.dataset import Dataset as NonSplittingDataset
from clldutils.text import strip_brackets, split_text
from csvw import Datatype

from tqdm import tqdm
import re

from collections import namedtuple

# moving this to avoid extra library code
STEDT = namedtuple(
    "STEDT",
    ["rn", "reflex", "gloss", "gfn", "srcabbr", "lgid", "language", "srcid"],
)
Hale = namedtuple("Hale", ["id", "gloss", "srcid"])


class Dataset(NonSplittingDataset):
    dir = Path(__file__).parent
    id = "halenepal"

    def cmd_download(self, **kw):
        pass

    def clean_form(self, item, form):
        if form not in ['*', '---', '-']:
            form = strip_brackets(split_text(form, separators=';,/')[0])
            return form

    def cmd_install(self, **kw):
        hale, stedt = [], []
        languages, concepts = {}, {}

        reps = [
                ('XIII', '13'),
                ('XII', '12'),
                ('A', 'a.'),
                ('B', 'b.'),
                ('C', 'c.'),
                ('D', 'd.')
                ]

        mapper = {
            '01.009': '01.009', 
            'XIIC56': '12c.56', 
            '01.009': '01.009', 
            'XIIC64': '12c.64', 
            'XIID31': '12d.31', 
            'XIID14': '12d.14', 
            '01.009': '01.009',
            }

        hsrcids = set()
        for element in self.raw.read_tsv(self.raw / "Hale_raw.tsv"):
            if element:
                hale.append(Hale(*element))
                hsrcids.add(element[-1])

        missing = set()
        for element in self.raw.read_tsv(self.raw / "AH-CSDPN.tsv"):
            if element:
                if element[-1] in hsrcids:
                    stedt.append(STEDT(*element))
                else:
                    for elm in re.split('[,;]', element[-1]): #.split(';'):
                        for s, t in reps:
                            elm = elm.replace(s, t)
                        elm = mapper.get(elm, elm)
                        if elm:
                            if elm not in hsrcids:
                                missing.add((elm, element[-1], element[2]))
                            else:
                                mapper[element[-1]] = elm
                                stedt.append(STEDT(*[x for x in
                                    element[:-1]]+[elm]))

        for i, y in enumerate(missing):
            print('{0:5} | {1:10} | {2:10} | {3}'.format(
                i+1, y[0],y[1], y[2]))


        with self.cldf as ds:
            self.cldf.tokenize = lambda x, y: self.tokenizer(x, '^'+y+'$',
                    column='IPA').split(' + ')
            
            # add data to cldf
            ds['FormTable', 'Segments'].separator = ' + '
            ds['FormTable', 'Segments'].datatype = Datatype.fromvalue({
                "base": "string",
                "format": "([\\S]+)( [\\S]+)*"
            })

            ds.add_sources(*self.raw.read_bib())
            
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

            for h in tqdm(hale, desc='cldfify'):
                search = list(filter(lambda x: x.srcid == h.srcid, stedt))

                if search:
                    for result in search:
                        if result.gloss in concepts:
                            ds.add_lexemes(
                                Language_ID=languages[result.language],
                                Parameter_ID=concepts[result.gloss],
                                Value=result.reflex,
                                Source=['Hale1973'] 
                            )
