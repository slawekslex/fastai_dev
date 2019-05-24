#AUTOGENERATED! DO NOT EDIT! File to edit: dev/05_data_source.ipynb (unless otherwise specified).

__all__ = ['DataSource']

from ..imports import *
from ..test import *
from ..core import *
from .core import *
from .pipeline import *
from ..notebook.showdoc import show_doc

class DataSource(PipedList):
    "Applies a `Pipeline` of `tfms` to filtered subsets of `items`"
    def __init__(self, items, tfms=None, filts=None):
        if filts is None: filts = [range_of(items)]
        self.filts = listify(mask2idxs(filt) for filt in filts)
        # Create map from item id to filter id
        assert all_disjoint(self.filts)
        self.filt_idx = ListContainer([None]*len(items))
        for i,f in enumerate(self.filts): self.filt_idx[f] = i
        super().__init__(items, tfms)

    def len(self,filt): return len(self.filts[filt])
    def subset(self, i): return _DsrcSubset(self, i)
    def __call__(self, x, filt, **kwargs): return super().__call__(x, filt=filt, **kwargs)
    def decode  (self, x, filt, **kwargs): return super().decode  (x, filt=filt, **kwargs)

    def __getitem__(self, i):
        "Transformed item(s) at `i`"
        its,fts = self.items[i],self.filt_idx[i]
        if is_iter(i): return [self(it,f) for it,f in zip(its,fts)]
        else: return self(its, fts)

DataSource.train,DataSource.valid = add_props(lambda i,x: x.subset(i), 2)

add_docs(
    DataSource,
    len="`len` of subset `filt`",
    subset="Filtered subset `i`",
    decode="Transform decode",
)

class _DsrcSubset:
    def __init__(self, dsrc, filt): self.dsrc,self.filt,self.filts = dsrc,filt,dsrc.filts[filt]
    def __getitem__(self,i): return self.dsrc[self.filts[i]]
    def decode(self, o, **kwargs): return self.dsrc.decode(o, self.filt, **kwargs)
    def decode_at(self, i, **kwargs): return self.decode(self[i], **kwargs)
    def __len__(self): return len(self.filts)
    def __eq__(self,b): return all_equal(b,self)
    def __repr__(self): return coll_repr(self)
    def show_at(self, i, **kwargs): return self.dsrc.show(self.decode_at(i), **kwargs)