#AUTOGENERATED! DO NOT EDIT! File to edit: dev/10_layers.ipynb (unless otherwise specified).

__all__ = ['Lambda', 'PartialLayer', 'View', 'ResizeBatch', 'Flatten', 'Debugger', 'sigmoid_range', 'SigmoidRange',
           'PoolFlatten', 'AdaptiveConcatPool2d', 'NormType', 'BatchNorm', 'BatchNorm1dFlat', 'BnDropLin',
           'init_default', 'defaults', 'ConvLayer', 'FlattenedLoss', 'CrossEntropyLossFlat', 'BCEWithLogitsLossFlat',
           'BCELossFlat', 'MSELossFlat', 'trunc_normal_', 'Embedding']

from .imports import *
from .test import *
from .core import *
from torch.nn.utils import weight_norm, spectral_norm

class Lambda(nn.Module):
    "An easy way to create a pytorch layer for a simple `func`"
    def __init__(self, func):
        super().__init__()
        self.func=func

    def forward(self, x): return self.func(x)
    def __repr__(self): return f'{self.__class__.__name__}({self.func})'

class PartialLayer(Lambda):
    "Layer that applies `partial(func, **kwargs)`"
    def __init__(self, func, **kwargs):
        super().__init__(partial(func, **kwargs))
        self.repr = f'{func.__name__}, {kwargs}'

    def forward(self, x): return self.func(x)
    def __repr__(self): return f'{self.__class__.__name__}({self.repr})'

class View(nn.Module):
    "Reshape `x` to `size`"
    def __init__(self, *size):
        super().__init__()
        self.size = size

    def forward(self, x): return x.view(self.size)

class ResizeBatch(nn.Module):
    "Reshape `x` to `size`, keeping batch dim the same size"
    def __init__(self, *size):
        super().__init__()
        self.size = size

    def forward(self, x):
        size = (x.size(0),) + self.size
        return x.view(size)

class Flatten(nn.Module):
    "Flatten `x` to a single dimension, often used at the end of a model. `full` for rank-1 tensor"
    def __init__(self, full=False):
        super().__init__()
        self.full = full

    def forward(self, x):
        return x.view(-1) if self.full else x.view(x.size(0), -1)

class Debugger(nn.Module):
    "A module to debug inside a model."
    def forward(self,x):
        set_trace()
        return x

def sigmoid_range(x, low, high):
    "Sigmoid function with range `(low, high)`"
    return torch.sigmoid(x) * (high - low) + low

class SigmoidRange(nn.Module):
    "Sigmoid module with range `(low, high)`"
    def __init__(self, low, high):
        super().__init__()
        self.low,self.high = low,high

    def forward(self, x): return sigmoid_range(x, self.low, self.high)

class PoolFlatten(nn.Sequential):
    "Combine `nn.AdaptiveAvgPool2d` and `Flatten`."
    def __init__(self): super().__init__(nn.AdaptiveAvgPool2d(1), Flatten())

class AdaptiveConcatPool2d(nn.Module):
    "Layer that concats `AdaptiveAvgPool2d` and `AdaptiveMaxPool2d`"
    def __init__(self, size=None):
        super().__init__()
        self.size = size or 1
        self.ap = nn.AdaptiveAvgPool2d(self.size)
        self.mp = nn.AdaptiveMaxPool2d(self.size)
    def forward(self, x): return torch.cat([self.mp(x), self.ap(x)], 1)

NormType = Enum('NormType', 'Batch BatchZero Weight Spectral')

def BatchNorm(nf, norm_type=NormType.Batch, ndim=2, **kwargs):
    "BatchNorm layer with `nf` features and `ndim` initialized depending on `norm_type`."
    assert 1 <= ndim <= 3
    bn = getattr(nn, f"BatchNorm{ndim}d")(nf, **kwargs)
    bn.bias.data.fill_(1e-3)
    bn.weight.data.fill_(0. if norm_type==NormType.BatchZero else 1.)
    return bn

class BatchNorm1dFlat(nn.BatchNorm1d):
    "`nn.BatchNorm1d`, but first flattens leading dimensions"
    def forward(self, x):
        if x.dim()==2: return super().forward(x)
        *f,l = x.shape
        x = x.contiguous().view(-1,l)
        return super().forward(x).view(*f,l)

class BnDropLin(nn.Sequential):
    "Module grouping `BatchNorm1d`, `Dropout` and `Linear` layers"
    def __init__(self, n_in, n_out, bn=True, p=0., act=None):
        layers = [BatchNorm(n_in, ndim=1)] if bn else []
        if p != 0: layers.append(nn.Dropout(p))
        layers.append(nn.Linear(n_in, n_out))
        if act is not None: layers.append(act)
        super().__init__(*layers)

def init_default(m, func=nn.init.kaiming_normal_):
    "Initialize `m` weights with `func` and set `bias` to 0."
    if func:
        if hasattr(m, 'weight'): func(m.weight)
        if hasattr(m, 'bias') and hasattr(m.bias, 'data'): m.bias.data.fill_(0.)
    return m

def _relu(inplace:bool=False, leaky:float=None):
    "Return a relu activation, maybe `leaky` and `inplace`."
    return nn.LeakyReLU(inplace=inplace, negative_slope=leaky) if leaky is not None else nn.ReLU(inplace=inplace)

def _conv_func(ndim=2, transpose=False):
    "Return the proper conv `ndim` function, potentially `transposed`."
    assert 1 <= ndim <=3
    return getattr(nn, f'Conv{"Transpose" if transpose else ""}{ndim}d')

defaults = SimpleNamespace(activation=nn.ReLU)

class ConvLayer(nn.Sequential):
    "Create a sequence of convolutional (`ni` to `nf`), ReLU (if `use_activ`) and `norm_type` layers."
    def __init__(self, ni, nf, ks=3, stride=1, padding=None, bias=None, ndim=2, norm_type=NormType.Batch,
                 act_cls=defaults.activation, transpose=False, init=nn.init.kaiming_normal_, xtra=None):
        if padding is None: padding = ((ks-1)//2 if not transpose else 0)
        bn = norm_type in (NormType.Batch, NormType.BatchZero)
        if bias is None: bias = not bn
        conv_func = _conv_func(ndim, transpose=transpose)
        conv = init_default(conv_func(ni, nf, kernel_size=ks, bias=bias, stride=stride, padding=padding), init)
        if   norm_type==NormType.Weight:   conv = weight_norm(conv)
        elif norm_type==NormType.Spectral: conv = spectral_norm(conv)
        layers = [conv]
        if act_cls is not None: layers.append(act_cls())
        if bn: layers.append(BatchNorm(nf, norm_type=norm_type, ndim=ndim))
        if xtra: layers.append(xtra)
        super().__init__(*layers)

class FlattenedLoss():
    "Same as `loss_cls`, but flattens input and target."
    def __init__(self, loss_cls, *args, axis=-1, floatify=False, is_2d=True, **kwargs):
        self.func,self.axis,self.floatify,self.is_2d = loss_cls(*args,**kwargs),axis,floatify,is_2d
        functools.update_wrapper(self, self.func)

    def __repr__(self): return f"FlattenedLoss of {self.func}"
    @property
    def reduction(self): return self.func.reduction
    @reduction.setter
    def reduction(self, v): self.func.reduction = v

    def __call__(self, input, target, **kwargs):
        input  = input .transpose(self.axis,-1).contiguous()
        target = target.transpose(self.axis,-1).contiguous()
        if self.floatify: target = target.float()
        input = input.view(-1,input.shape[-1]) if self.is_2d else input.view(-1)
        return self.func.__call__(input, target.view(-1), **kwargs)

def CrossEntropyLossFlat(*args, axis:int=-1, **kwargs):
    "Same as `nn.CrossEntropyLoss`, but flattens input and target."
    return FlattenedLoss(nn.CrossEntropyLoss, *args, axis=axis, **kwargs)

def BCEWithLogitsLossFlat(*args, axis:int=-1, floatify:bool=True, **kwargs):
    "Same as `nn.BCEWithLogitsLoss`, but flattens input and target."
    return FlattenedLoss(nn.BCEWithLogitsLoss, *args, axis=axis, floatify=floatify, is_2d=False, **kwargs)

def BCELossFlat(*args, axis:int=-1, floatify:bool=True, **kwargs):
    "Same as `nn.BCELoss`, but flattens input and target."
    return FlattenedLoss(nn.BCELoss, *args, axis=axis, floatify=floatify, is_2d=False, **kwargs)

def MSELossFlat(*args, axis:int=-1, floatify:bool=True, **kwargs):
    "Same as `nn.MSELoss`, but flattens input and target."
    return FlattenedLoss(nn.MSELoss, *args, axis=axis, floatify=floatify, is_2d=False, **kwargs)

def trunc_normal_(x, mean=0., std=1.):
    "Truncated normal initialization (approximation)"
    # From https://discuss.pytorch.org/t/implementing-truncated-normal-initializer/4778/12
    return x.normal_().fmod_(2).mul_(std).add_(mean)

class Embedding(nn.Embedding):
    "Embedding layer with truncated normal initialization"
    def __init__(self, ni, nf):
        super().__init__(ni, nf)
        trunc_normal_(self.weight.data, std=0.01)