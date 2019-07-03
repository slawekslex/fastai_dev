#AUTOGENERATED! DO NOT EDIT! File to edit: dev/09_data_block.ipynb (unless otherwise specified).

__all__ = ['DataBlock']

@docs
class DataBlock():
    "Generic container to quickly build `DataSource` and `DataBunch`"
    default_dl_tfms = Cuda
    def __init__(self, types=None, get_items=None, splitter=None, labeller=None):
        if types is not None:     self.types = types
        if get_items is not None: self.get_items = get_items
        if splitter is not None:  self.splitter = splitter
        if labeller is not None:  self.labeller = labeller

    def get_items(self, source): pass
    def splitter(self, items): pass
    def labeller(self, item): pass

    def datasource(self, source, tfms=None, tuple_tfms=None):
        items = self.get_items(source)
        splits = self.splitter(items)
        if tfms is None: tfms = [L() for t in self.types]
        tfms = L(getattr(t, 'default_tfms', L()) + L(tfm) for (t,tfm) in zip(self.types, tfms))
        tfms = [tfms[0]] + [self.labeller + tfm for tfm in tfms[1:]]
        tfms = L(L(t() if isinstance(t, type) else t for t in tfm) for tfm in tfms)
        tuple_tfms = sum([getattr(t, 'default_tuple_tfms', L()) for t in self.types], L()) + L(tuple_tfms)
        tuple_tfms = L(t() if isinstance(t, type) else t for t in tuple_tfms)
        return DataSource(items, tfms=tfms, tuple_tfms=tuple_tfms, filts=splits)

    def databunch(self, source, tfms=None, tuple_tfms=None, dl_tfms=None, bs=16, **kwargs):
        dsrc = self.datasource(source, tfms=tfms, tuple_tfms=tuple_tfms)
        dl_tfms = sum([getattr(t, 'default_dl_tfms', L()) for t in self+L(self.types)], L()) + L(dl_tfms)
        dl_tfms = L(t() if isinstance(t, type) else t for t in dl_tfms)
        return dsrc.databunch(tfms=tfms, bs=bs, **kwargs)

    _docs = dict(get_items="Pass at init or implement how to get your raw items from a `source`",
                 splitter="Pass at init or implement how to split your `items`",
                 labeller="Pass at init or implement how to label a raw `item`",
                 datasource="Create a `Datasource` from `source` with `tfms` and `tuple_tfms`",
                 databunch="Create a `DataBunch` from `source` with `tfms`")