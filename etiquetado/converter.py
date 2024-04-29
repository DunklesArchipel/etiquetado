from echemdbconverters.eclabloader import ECLabLoader, CSVloader
from biologic import biologic_fields, biologic_fields_alt_names, preferred_fields
from unitpackage.entry import Entry
from pathlib import Path
import yaml
import shutil
import pandas as pd

class BiologicMPT:

    def __init__(self, filename, encoding='ANSI'):
        self.filename = filename
        self.encoding = encoding

    @property
    def loader(self):

        with open(self.filename, 'r', encoding=self.encoding) as f:
            mpt = ECLabLoader(f)
        return mpt

    @property
    def df_modified(self):
        df = self.loader.df.copy()
        exsisting = []
        for column in df.columns:
            if column in preferred_fields:
                exsisting.append(column)
        df_preferred = df[exsisting].copy()
        df_renamed = df_preferred.rename(columns=biologic_fields_alt_names).copy()
        # for column in df.columns:
        #     if 'Unnamed' in column:
        #         unnamed_column = column
        # df_dropped = df_renamed.drop(columns=[unnamed_column])

        return df_renamed

    @classmethod
    def modify_fields(cls, original, alternative, keep_original_name=True):
        r"""Updates in a list of fields (original) the field names with those
        provided in a dictionary. The original name of the fields is kept with
        the name `original` in the updated fields.

        EXAMPLES::

            >>> fields = [{'name': '<E>', 'unit':'mV'},{'name': 'I', 'unit':'mA'}]
            >>> alt_fields = {'<E>':'E'}
            >>> BilogicPeisMPT.modify_fields(fields, alt_fields)
            [{'name': 'E', 'unit': 'mV', 'original': '<E>'}, {'name': 'I', 'unit': 'mA'}]

        """
        for field in original:
            for key in alternative.keys():
                if field['name'] == key:
                    if keep_original_name:
                        field.setdefault('original', key)
                    field['name'] = alternative[key]

        return original


    @property
    def _metadata(self):
        with open(Path(self.filename).with_suffix('.mpt.yaml')) as f:
            metadata = yaml.load(f, Loader=yaml.SafeLoader)
        return metadata

    @property
    def eln(self):
        with open(Path(self.filename).with_suffix('.md')) as f:
            lines = f.readlines()
        return lines


    @property
    def metadata(self):
        metadata = self._metadata
        metadata.setdefault("csv header", self.loader.header)
        metadata['eln'].setdefault("description", self.eln)
        return metadata


    @property
    def new_fields(self):
        return self.modify_fields(biologic_fields, biologic_fields_alt_names)


    @property
    def entry(self):
        return Entry.from_df(df=self.df_modified, metadata=self.metadata, fields=self.new_fields, basename=Path(self.filename).stem)

    def convert(self, *, outdir):
        self.entry.save(outdir=outdir)
        shutil.copy2(Path(self.filename).with_suffix('.md'), outdir)


class PlasmaCSV:

    def __init__(self, filename, encoding='ANSI'):
        self.filename = filename
        self.encoding = encoding

    @property
    def loader(self):

        with open(self.filename, 'r', encoding=self.encoding) as f:
            df_csv = CSVloader(f)
        return df_csv

    #metadata
    @property
    def _metadata(self):
        with open(Path(self.filename).with_suffix('.csv.yaml')) as f:
            metadata = yaml.load(f, Loader=yaml.SafeLoader)
        return metadata
    #markdon
    @property
    def eln(self):
        with open(Path(self.filename).with_suffix('.md')) as f:
            lines = f.readlines()
        return lines

    #metadata
    @property
    def metadata(self):
        metadata = self._metadata
        metadata.setdefault("csv header", self.loader.header)
        metadata['eln'].setdefault("description", self.eln)
        return metadata


    #mpt
    @property
    def entry(self):
        return Entry.from_df(df=self.loader.df, metadata=self.metadata, basename=Path(self.filename).stem)

    #markdown
    def convert(self, *, outdir):
        self.entry.save(outdir=outdir)
        shutil.copy2(Path(self.filename).with_suffix('.md'), outdir)
