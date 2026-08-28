# Cleaned FGI-Net architecture from https://github.com/CZ178/FGI-Net
# Import-safe: removed thop profiling that ran at module import.

import math
import copy
from functools import partial
from collections import OrderedDict
from typing import Optional, Callable

import numpy as np
import torch
import torch.nn as nn
import torch.utils.checkpoint as checkpoint
from torch import Tensor
from torch.nn import functional as F


def _make_divisible(ch, divisor=8, min_ch=None):
    if min_ch is None:
        min_ch = divisor
    new_ch = max(min_ch, int(ch + divisor / 2) // divisor * divisor)
    if new_ch < 0.9 * ch:
        new_ch += divisor
    return new_ch

def drop_path(x, drop_prob: float = 0., training: bool = False):
    if drop_prob == 0. or not training:
        return x
    keep_prob = 1 - drop_prob
    shape = (x.shape[0],) + (1,) * (x.ndim - 1)
    random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
    random_tensor.floor_()  #
    output = x.div(keep_prob) * random_tensor
    return output

def drop_path_f(x,drop_prob: float = 0.3,training:bool =False):
    if drop_prob == 0. or not training:
        return x
    keep_prob = 1 - drop_prob
    shape = (x.shape[0],) + (1,) * (x.ndim - 1)
    random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
    random_tensor.floor_()
    output = x.div(keep_prob) * random_tensor
    return output

class DropPath(nn.Module):
    def __init__(self, drop_prob=None):
        super(DropPath, self).__init__()
        self.drop_prob = drop_prob

    def forward(self, x):
        return drop_path(x, self.drop_prob, self.training)

class ChannelAttention(nn.Module):
    def __init__(self, in_planes, ratio=16):
        super(ChannelAttention, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(in_planes, in_planes // ratio, 1, bias=False),
            nn.ReLU(),
            nn.Conv2d(in_planes // ratio, in_planes, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        out = avg_out + max_out
        return self.sigmoid(out)

class SpatialAttention(nn.Module):
    def __init__(self, kernel_size=7):
        super(SpatialAttention, self).__init__()
        self.conv1 = nn.Conv2d(2, 1, kernel_size, padding=kernel_size//2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        x = torch.cat([avg_out, max_out], dim=1)
        x = self.conv1(x)
        return self.sigmoid(x)

class DepthwiseSeparableConv(nn.Module):
    def __init__(self, in_channels, out_channels,kernel_size=3, stride=1, padding=1):
        super(DepthwiseSeparableConv, self).__init__()
        self.depthwise_conv = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, kernel_size=kernel_size, stride=stride, groups=in_channels, padding=padding),
            nn.ReLU(),
            nn.BatchNorm2d(in_channels)
        )
        self.pointwise_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=1),
            nn.ReLU(),
            nn.BatchNorm2d(out_channels)
        )

    def forward(self, x):
        out = self.depthwise_conv(x)
        out = self.pointwise_conv(out)
        return out

class ConvBNActivation(nn.Sequential):
    def __init__(self,
                 in_planes:int,
                 out_planes:int,
                 kernel_size:int=3,
                 stride: int = 1,
                 groups: int = 1,
                 norm_layer: Optional[Callable[..., nn.Module]] = None,
                 activation_layer: Optional[Callable[..., nn.Module]] = None):
        padding = (kernel_size - 1) // 2
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if activation_layer is None:
            activation_layer = nn.SiLU
        super(ConvBNActivation, self).__init__(nn.Conv2d(in_channels=in_planes,
                                                         out_channels=out_planes,
                                                         kernel_size=kernel_size,
                                                         stride=stride,
                                                         padding=padding,
                                                         groups=groups,
                                                         bias=False),
                                               norm_layer(out_planes),
                                               activation_layer()
                                               )

class SqueezeExcitation(nn.Module):
    def __init__(self,input_c:int,
                 expand_c:int,
                 aqueeze_factor:int=4):
        super(SqueezeExcitation, self).__init__()
        squeeze_c = input_c // aqueeze_factor
        self.fc1 = nn.Conv2d(expand_c, squeeze_c, 1)
        self.act1 = nn.SiLU()
        self.fc2 = nn.Conv2d(squeeze_c, expand_c, 1)
        self.act2 = nn.Sigmoid()
    def forward(self,x):
        out = F.adaptive_avg_pool2d(x, output_size=(1, 1))
        out = self.fc1(out)
        out = self.act1(out)
        out = self.fc2(out)
        out = self.act2(out)
        return out * x

class InvertedResidualConfig:
    def __init__(self,
                 kernel:int, # 3 or 5
                 input_c:int,
                 out_c:int,
                 expanded_ratio:int,  # 1 or 6
                 stride:int,          # 1 or 2
                 use_se:bool,         # True
                 drop_rate:float,
                 index:str,
                 width_coefficient: float):
        self.input_c = self.adjust_channels(input_c, width_coefficient)
        self.kernel =kernel
        self.expanded_c = self.input_c * expanded_ratio
        self.out_c = self.adjust_channels(out_c, width_coefficient)
        self.use_se = use_se
        self.stride = stride
        self.drop_rate = drop_rate
        self.index = index

    @staticmethod
    def adjust_channels(channels: int, width_coefficient: float):
        return _make_divisible(channels * width_coefficient ,8)

class InvertedResidual(nn.Module):
    def __init__(self,
                 cnf: InvertedResidualConfig,
                 norm_layer: Callable[..., nn.Module]):
        super(InvertedResidual, self).__init__()

        if cnf.stride not in [1, 2]:
            raise ValueError("illegal stride value.")

        self.use_res_connect = (cnf.stride == 1 and cnf.input_c == cnf.out_c)

        layers = OrderedDict()
        activation_layer = nn.SiLU


        if cnf.expanded_c != cnf.input_c:
            layers.update({"expand_conv": ConvBNActivation(cnf.input_c,
                                                           cnf.expanded_c,
                                                           kernel_size=1,
                                                           norm_layer=norm_layer,
                                                           activation_layer=activation_layer)})

        # depthwise
        layers.update({"dwconv": ConvBNActivation(cnf.expanded_c,
                                                  cnf.expanded_c,
                                                  kernel_size=cnf.kernel,
                                                  stride=cnf.stride,
                                                  groups=cnf.expanded_c,
                                                  norm_layer=norm_layer,
                                                  activation_layer=activation_layer)})

        if cnf.use_se:
            layers.update({"se": SqueezeExcitation(cnf.input_c,
                                                   cnf.expanded_c)})

        # project
        layers.update({"project_conv": ConvBNActivation(cnf.expanded_c,
                                                        cnf.out_c,
                                                        kernel_size=1,
                                                        norm_layer=norm_layer,
                                                        activation_layer=nn.Identity)})

        self.block = nn.Sequential(layers)
        self.out_channels = cnf.out_c
        self.is_strided = cnf.stride > 1

        if self.use_res_connect and cnf.drop_rate > 0:
            self.dropout = DropPath(cnf.drop_rate)
        else:
            self.dropout = nn.Identity()

    def forward(self, x: Tensor) -> Tensor:
        result = self.block(x)
        result = self.dropout(result)
        if self.use_res_connect:
            result += x

        return result

class EfficientNetStage(nn.Module):
    def __init__(self,
                 stage: str = 'stage1',  # 'stage1', 'stage2', or 'stage3'
                 width_coefficient: float = 1.0,
                 depth_coefficient: float = 1.0,
                 drop_connect_rate: float = 0,
                 block: Optional[Callable[..., nn.Module]] = None,
                 norm_layer: Optional[Callable[..., nn.Module]] = None
                 ):
        super(EfficientNetStage, self).__init__()

        # Define configuration for each stage
        stage_configs = {
            'stage1': [
                [3, 32, 16, 1, 1, True, drop_connect_rate, 1],
                [3, 16, 24, 6, 2, True, drop_connect_rate, 2],  # 56
            ],
            'stage2': [
                [5, 24, 40, 6, 2, True, drop_connect_rate, 2],  # 2
            ],
            'stage3': [
                [3, 40, 80, 6, 2, True, drop_connect_rate, 3],
                [5, 80, 112, 6, 1, True, drop_connect_rate, 3],  # 14
            ]
        }

        if stage not in stage_configs:
            raise ValueError(f"Invalid stage '{stage}'. Must be 'stage1', 'stage2', or 'stage3'")

        default_cnf = stage_configs[stage]

        def round_repeats(repeats):
            """Round number of repeats based on depth multiplier."""
            return int(math.ceil(depth_coefficient * repeats))  # Round up

        if block is None:
            block = InvertedResidual

        if norm_layer is None:
            norm_layer = partial(nn.BatchNorm2d, eps=1e-3, momentum=0.1)

        adjust_channels = partial(InvertedResidualConfig.adjust_channels,
                                  width_coefficient=width_coefficient)

        # build inverted_residual_setting
        bneck_conf = partial(InvertedResidualConfig,
                             width_coefficient=width_coefficient)

        b = 0
        num_blocks = float(sum(round_repeats(i[-1]) for i in default_cnf))
        inverted_residual_setting = []
        for stage_idx, args in enumerate(default_cnf):
            cnf = copy.copy(args)
            for i in range(round_repeats(cnf.pop(-1))):
                if i > 0:
                    # strides equal 1 except first cnf
                    cnf[-3] = 1  # strides
                    cnf[1] = cnf[2]  # input_channel equal output_channel

                cnf[-1] = args[-2] * b / num_blocks  # update dropout ratio
                index = str(stage_idx + 1) + chr(i + 97)  # 1a, 2a, 2b, ...
                inverted_residual_setting.append(bneck_conf(*cnf, index))
                b += 1

        # create layers
        layers = OrderedDict()

        # For stage1 only, add the stem_conv
        if stage == 'stage1':
            layers.update({"stem_conv": ConvBNActivation(in_planes=3,
                                                         out_planes=adjust_channels(32),
                                                         kernel_size=3,
                                                         stride=2,
                                                         norm_layer=norm_layer)})

        # building inverted residual blocks
        for cnf in inverted_residual_setting:
            layers.update({cnf.index: block(cnf, norm_layer)})

        self.features = nn.Sequential(layers)


    def forward(self, x: Tensor) -> Tensor:
        return self.features(x)

def window_partiton(x,window_size:int):# Patch_Partition
    B, H, W, C = x.shape
    x = x.view(B,H//window_size,window_size,W//window_size,window_size,C)

    # permute: [B, H//Mh, Mh, W//Mw, Mw, C] -> [B, H//Mh, W//Mh, Mw, Mw, C]   è½¬ç½®
    # view: [B, H//Mh, W//Mw, Mh, Mw, C] -> [B*num_windows, Mh, Mw, C]
    windows = x.permute(0,1,3,2,4,5).contiguous().view(-1,window_size,window_size,C)
    return windows
# x = torch.randn(1,224,224,3)
# out = window_partiton(x,4)
# print("window_partiton:",out.shape)

def window_reverse(windows,window_size:int ,H:int, W:int):
    _ ,_, _, C = windows.shape
    windows = windows.view(-1,H//window_size,W//window_size,window_size,window_size,C)
    windows = windows.permute(0,1,3,2,4,5).contiguous().view(-1,H,W,C)
    return windows
# out = window_reverse(out,4,224,224)
# print("window_reverse",out.shape)


class Patch_Embed(nn.Module): # Linear_Embedding
    """ 2D Image to Patch Embedding """
    def __init__(self,patch_size=4, in_c=3, embed_dim=96,norm_layer=None):
        super(Patch_Embed, self).__init__()
        self.patch_size = (patch_size,patch_size)
        self.in_chans = in_c
        self.embed_dim = embed_dim
        self.proj = nn.Conv2d(in_c,embed_dim,kernel_size=patch_size,stride=patch_size)
        self.norm = norm_layer(embed_dim) if norm_layer else nn.Identity()

    def forward(self,x):
        _,_,H,W = x.shape
        if (H % self.patch_size[0] != 0) or  (W % self.patch_size[1] != 0):
            x = F.pad(x,(0,self.patch_size[1] - W % self.patch_size[1],
                         0,self.patch_size[0] - H % self.patch_size[0],
                         0,0))
        x = self.proj(x)
        _,_,H,W = x.shape
        x = x.flatten(2).transpose(1,2)
        x = self.norm(x)
        return x, H, W
# x = torch.randn(1,3,224,224)
# demo = Patch_Embed()
# x,_,_ = demo(x)
# print("Patch_Embed:",x.shape)



class PatchMerging(nn.Module): # Patch Merging Layer
    """
     dim(int): number of input channels
     norm_layer (nn.Module, optional): Normalization layer.  Default: nn.LayerNorm
    """
    def __init__(self,dim,norm_layer=nn.LayerNorm):
        super(PatchMerging, self).__init__()
        self.dim =dim
        self.norm_layer = nn.LayerNorm(4 * dim)
        self.reduction = nn.Linear(4 * dim, 2 *dim, bias=False)

    def forward(self, x, H, W):
        """
        :param x: B, H*W, C
        """
        B, L, C = x.shape
        assert L == H*W

        x = x.view(B, H, W, C)
        #padding
        if (H % 2 != 0) or (W % 2 != 0):
            # (C_front, C_back, W_left, W_right, H_top, H_bottom)
            x = F.pad(x, (0, 0, 0, W % 2, 0, H % 2))
        x0 = x[:,0::2,0::2,:]  # [B, H/2, W/2, C]
        x1 = x[:,0::2,1::2,:]  # [B, H/2, W/2, C]
        x2 = x[:,1::2,0::2,:]  # [B, H/2, W/2, C]
        x3 = x[:,1::2,1::2,:]  # [B, H/2, W/2, C]
        x = torch.cat([x0,x1,x2,x3],dim=-1)   # [B, H/2, W/2, 4C]
        x = x.view(B, -1, 4 * C)  # [B, H/2*W/2, 4*C]

        x = self.norm_layer(x)
        x = self.reduction(x)

        return x
# # x = torch.randn(1,50176,1)
# # demo = PatchMerging(1)
# # print(demo(x,224,224).shape)

class MLP(nn.Module):
    def __init__(self,in_features,hidden_features=None,out_features=None,act_layer=nn.GELU,drop=0.3):
        super(MLP, self).__init__()
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features

        self.fc1 = nn.Linear(in_features,hidden_features)
        self.act = act_layer()
        self.drop1 = nn.Dropout(drop)
        self.fc2 = nn.Linear(hidden_features,out_features)
        self.drop2 = nn.Dropout(drop)

    def forward(self,x):
        out = self.fc1(x)
        out = self.act(out)
        out = self.drop1(out)
        out = self.fc2(out)
        out = self.drop2(out)
        return out
# x = torch.randn(50,100)
# demo = MLP(100,30,20)
# print(demo(x).shape)

class WindowAttention(nn.Module):
    def __init__(self,dim, window_size, num_heads, qkv_bias=True, attn_drop=0.3, proj_drop=0.3):
        super(WindowAttention,self).__init__()
        self.dim = dim
        self.window_size = window_size  # [Mh, Mw]
        self.num_heads = num_heads
        head_dim = dim // num_heads
        self.scale = head_dim ** -0.5
        self.relative_position_bias_table = nn.Parameter(
            torch.zeros((2 * window_size[0] - 1) * (2 * window_size[1] - 1), num_heads))  # [2*Mh-1 * 2*Mw-1, nH]

        coords_h = torch.arange(self.window_size[0])
        coords_w = torch.arange(self.window_size[1])

        coords = torch.stack(torch.meshgrid([coords_h,coords_w],indexing="ij")) # [2, Mh, Mw]
        coords_flatten = torch.flatten(coords, 1) # [2, Mh*Mw]
        relative_coords = coords_flatten[:, :, None] - coords_flatten[:, None, :]  #
        relative_coords = relative_coords.permute(1, 2, 0).contiguous()
        relative_coords[:, :, 0] += self.window_size[0] - 1
        relative_coords[:, :, 1] += self.window_size[1] - 1
        relative_coords[:, :, 0] *= 2 * self.window_size[1] - 1
        relative_position_index = relative_coords.sum(-1)
        self.register_buffer("relative_position_index", relative_position_index)

        self.qkv = nn.Linear(dim, dim*3,bias=qkv_bias)
        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(dim,dim)
        self.proj_drop = nn.Dropout(proj_drop)

        nn.init.trunc_normal_(self.relative_position_bias_table, std=.02)
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, x, mask: Optional[torch.Tensor] = None):
        B_, N, C = x.shape
        qkv = self.qkv(x).reshape(B_, N, 3, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        q, k, v = qkv.unbind(0)

        q = q * self.scale
        attn = (q @ k.transpose(-2, -1))

        relative_position_bias = self.relative_position_bias_table[self.relative_position_index.view(-1)].view(
            self.window_size[0] * self.window_size[1], self.window_size[0] * self.window_size[1], -1)
        relative_position_bias = relative_position_bias.permute(2, 0, 1).contiguous()  # [nH, Mh*Mw, Mh*Mw]
        attn = attn + relative_position_bias.unsqueeze(0)


        if mask is not None:
            nW = mask.shape[0]  # num_windows
            attn = attn.view(B_ // nW, nW, self.num_heads, N, N) + mask.unsqueeze(1).unsqueeze(0)
            attn = attn.view(-1, self.num_heads, N, N)
            attn = self.softmax(attn)
        else:
            attn = self.softmax(attn)

        attn = self.attn_drop(attn)
        x = (attn @ v).transpose(1, 2).reshape(B_, N, C)
        x = self.proj(x)
        x = self.proj_drop(x)
        return x

class SwinTransformerBlock(nn.Module):
    def __init__(self,dim, num_heads, window_size=7,shift_size=0,
                 mlp_ratio=4., qkv_bias=True, drop=0.3, attn_drop=0.3, drop_path=0.2,
                 act_layer=nn.GELU, norm_layer=nn.LayerNorm):
        super(SwinTransformerBlock, self).__init__()
        self.dim = dim
        self.num_heads = num_heads
        self.window_size = window_size
        self.shift_size = shift_size
        self.mlp_ratio = mlp_ratio
        assert 0 <= self.shift_size <= self.window_size, "shift_size must in 0-window_size"
        self.norm1 = norm_layer(dim)
        self.attn = WindowAttention(dim,window_size=(self.window_size,self.window_size),num_heads=num_heads,
                                    qkv_bias=qkv_bias,attn_drop=attn_drop,proj_drop=drop)

        self.drop_path = DropPath(drop_path) if drop_path > 0. else nn.Identity()
        self.norm2 = norm_layer(dim)
        mlp_hideen_dim = int(dim * mlp_ratio)
        self.mlp = MLP(in_features=dim,hidden_features=mlp_hideen_dim,act_layer=act_layer,drop=drop)


    def forward(self,x,attn_mask):

        H, W = self.H, self.W
        B, L, C = x.shape

        shortcut = x
        x = self.norm1(x)
        x = x.view(B,H,W,C)

        pad_l = pad_t = 0
        pad_r = (self.window_size - W % self.window_size) % self.window_size
        pad_b = (self.window_size - H % self.window_size) % self.window_size
        x = F.pad(x, (0, 0, pad_l, pad_r, pad_t, pad_b))
        _, Hp, Wp, _ = x.shape


        if self.shift_size > 0:
            shifted_x = torch.roll(x, shifts=(-self.shift_size, -self.shift_size), dims=(1, 2))
        else:
            shifted_x = x
            attn_mask = None

        # partition windos
        x_windows = window_partiton(shifted_x,self.window_size)   #[nW*B, Mh, Mw, C]
        x_windows = x_windows.view(-1,self.window_size * self.window_size,C) #[nW*B, Mh*Mw, C]

        # W-MSA / SW-MSA
        attn_windows = self.attn(x_windows,mask=attn_mask)  #[nW*B, Mh*Mw, C]

        # merge windows
        attn_windows = attn_windows.view(-1,self.window_size, self.window_size,C) #[nW*B, Mh, Mw, C]
        shifted_x = window_reverse(attn_windows,self.window_size,Hp,Wp)

        # reverse cyclic shift
        if self.shift_size > 0:
            x = torch.roll(x, shifts=(self.shift_size, self.shift_size), dims=(1, 2))
        else:
            x = shifted_x

        if pad_r > 0 or pad_b > 0:
            x = x[:, :H, :W, :].contiguous()

        x = x.view(B, H * W, C)

        #FFN
        x = shortcut + self.drop_path(x)
        x = x + self.drop_path(self.mlp(self.norm2(x)))

        return x

class BasicLayer(nn.Module):
    def __init__(self, dim, depth, num_heads, window_size,
                 mlp_ratio=4., qkv_bias=True, drop=0.3, attn_drop=0.3,
                 drop_path=0.2, norm_layer=nn.LayerNorm, downsample=None, use_checkpoint=False):
        super().__init__()
        self.dim = dim
        self.depth = depth
        self.window_size = window_size
        self.use_checkpoint = use_checkpoint
        self.shift_size = window_size // 2

        # build blocks
        self.blocks = nn.ModuleList([
            SwinTransformerBlock(
                dim=dim,
                num_heads=num_heads,
                window_size=window_size,
                shift_size=0 if (i % 2 == 0) else self.shift_size,   #iè¡¨ç¤ºå±‚æ•°ï¼ŒSwinTransformerBlockæ˜¯æˆå¯¹ä½¿ç”¨
                mlp_ratio=mlp_ratio,
                qkv_bias=qkv_bias,
                drop=drop,
                attn_drop=attn_drop,
                drop_path=drop_path[i] if isinstance(drop_path, list) else drop_path,
                norm_layer=norm_layer)
            for i in range(depth)])

        # patch merging layer
        if downsample is not None:
            self.downsample = downsample(dim=dim, norm_layer=norm_layer)
        else:
            self.downsample = None

    def create_mask(self, x, H, W):
        Hp = int(np.ceil(H / self.window_size)) * self.window_size
        Wp = int(np.ceil(W / self.window_size)) * self.window_size
        img_mask = torch.zeros((1, Hp, Wp, 1), device=x.device)  # [1, Hp, Wp, 1]
        h_slices = (slice(0, -self.window_size),
                    slice(-self.window_size, -self.shift_size),
                    slice(-self.shift_size, None))
        w_slices = (slice(0, -self.window_size),
                    slice(-self.window_size, -self.shift_size),
                    slice(-self.shift_size, None))
        cnt = 0
        for h in h_slices:
            for w in w_slices:
                img_mask[:, h, w, :] = cnt
                cnt += 1

        mask_windows = window_partiton(img_mask, self.window_size)  # [nW, Mh, Mw, 1]
        mask_windows = mask_windows.view(-1, self.window_size * self.window_size)  # [nW, Mh*Mw]
        attn_mask = mask_windows.unsqueeze(1) - mask_windows.unsqueeze(2)  # [nW, 1, Mh*Mw] - [nW, Mh*Mw, 1]
        # [nW, Mh*Mw, Mh*Mw]
        attn_mask = attn_mask.masked_fill(attn_mask != 0, float(-100.0)).masked_fill(attn_mask == 0, float(0.0))
        return attn_mask

    def forward(self, x, H, W):
        attn_mask = self.create_mask(x, H, W)  # [nW, Mh*Mw, Mh*Mw]
        for blk in self.blocks:
            blk.H, blk.W = H, W
            if not torch.jit.is_scripting() and self.use_checkpoint:
                x = checkpoint.checkpoint(blk, x, attn_mask)
            else:
                x = blk(x, attn_mask)
        if self.downsample is not None:
            x = self.downsample(x, H, W)
            H, W = (H + 1) // 2, (W + 1) // 2

        return x, H, W

class FGI(nn.Module):
    def __init__(self, num_classes=2,
                 depths=[(2,), (2,), (2,)],
                 embed_dim=[24, 40, 112],
                 num_heads=[(2,), (4,), (8,)],
                 window_size=7, mlp_ratio=4., qkv_bias=True,
                 drop_rate=0., drop_rate1=0.,drop_rate2=0.,
                 attn_drop_rate=0., drop_path_rate=0.,
                 norm_layer=nn.LayerNorm, patch_norm=True,
                 use_checkpoint=False, **kwargs):
        super(FGI, self).__init__()
        self.mlp_ratio = mlp_ratio
        self.num_classes = num_classes

        self.EfficientNet_b0_stage1 = EfficientNetStage(stage='stage1')
        self.num_layers = len(depths[0])
        self.num_features = int(embed_dim[0] * 2 ** (self.num_layers - 1))
        self.pos_drop = nn.Dropout(p=drop_rate)
        dpr = [x.item() for x in torch.linspace(0, drop_path_rate, sum(depths[0]))]
        self.layers = nn.ModuleList()
        for i_layer in range(self.num_layers):
            layers = BasicLayer(dim=int(embed_dim[0] * 2 ** i_layer),
                                depth=depths[0][i_layer],
                                num_heads=num_heads[0][i_layer],
                                window_size=window_size,
                                mlp_ratio=self.mlp_ratio,
                                qkv_bias=qkv_bias,
                                drop=drop_rate,
                                attn_drop=attn_drop_rate,
                                drop_path=dpr[sum(depths[0][:i_layer]):sum(depths[0][:i_layer + 1])],
                                norm_layer=norm_layer,
                                downsample=PatchMerging if (i_layer < self.num_layers - 1) else None,
                                use_checkpoint=use_checkpoint)
            self.layers.append(layers)
        self.norm = norm_layer(self.num_features)

        self.EfficientNet_b0_stage2 = EfficientNetStage(stage='stage2')
        self.num_layers1 = len(depths[1])
        self.num_features1 = int(embed_dim[1] * 2 ** (self.num_layers1 - 1))
        self.pos_drop1 = nn.Dropout(p=drop_rate1)
        dpr1 = [x.item() for x in torch.linspace(0, drop_path_rate, sum(depths[1]))]
        self.layers1 = nn.ModuleList()
        for i_layer in range(self.num_layers1):
            layers1 = BasicLayer(dim=int(embed_dim[1] * 2 ** i_layer),
                                 depth=depths[1][i_layer],
                                 num_heads=num_heads[1][i_layer],
                                 window_size=window_size,
                                 mlp_ratio=self.mlp_ratio,
                                 qkv_bias=qkv_bias,
                                 drop=drop_rate1,
                                 attn_drop=attn_drop_rate,
                                 drop_path=dpr1[sum(depths[1][:i_layer]):sum(depths[1][:i_layer + 1])],
                                 norm_layer=norm_layer,
                                 downsample=PatchMerging if (i_layer < self.num_layers1 - 1) else None,
                                 use_checkpoint=use_checkpoint)
            self.layers1.append(layers1)
        self.norm1 = norm_layer(self.num_features1)

        self.EfficientNet_b0_stage3 = EfficientNetStage(stage='stage3')
        self.num_layers2 = len(depths[2])
        self.num_features2 = int(embed_dim[2] * 2 ** (self.num_layers2 - 1))
        self.pos_drop2 = nn.Dropout(p=drop_rate2)
        dpr2 = [x.item() for x in torch.linspace(0, drop_path_rate, sum(depths[2]))]
        self.patch_norm = patch_norm
        self.layers2 = nn.ModuleList()
        for i_layer in range(self.num_layers2):
            layers2 = BasicLayer(dim=int(embed_dim[2] * 2 ** i_layer),
                                 depth=depths[2][i_layer],
                                 num_heads=num_heads[2][i_layer],
                                 window_size=window_size,
                                 mlp_ratio=self.mlp_ratio,
                                 qkv_bias=qkv_bias,
                                 drop=drop_rate2,
                                 attn_drop=attn_drop_rate,
                                 drop_path=dpr2[sum(depths[2][:i_layer]):sum(depths[2][:i_layer + 1])],
                                 norm_layer=norm_layer,
                                 downsample=PatchMerging if (i_layer < self.num_layers2 - 1) else None,
                                 use_checkpoint=use_checkpoint)
            self.layers2.append(layers2)
        self.norm2 = norm_layer(self.num_features2)


        self.conv = nn.Sequential(
            nn.Conv2d(112, 96, kernel_size=3, stride=1, padding=1,bias=False),
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2, padding=0),
        )

        self.conv2d = nn.Sequential(
            DepthwiseSeparableConv(96, 1280, stride=1, padding=0),###
            nn.BatchNorm2d(1280),
            nn.ReLU(inplace=True),
            DepthwiseSeparableConv(1280, 96, stride=1, padding=0),
            nn.BatchNorm2d(96),
        )
        self.conv2d_res = DepthwiseSeparableConv(96, 96, stride=2, padding=0)
        self.ca = ChannelAttention(96)
        self.sa = SpatialAttention()

        self.avgpool = nn.AdaptiveAvgPool1d(1)



        self.head = nn.Sequential(
            nn.Linear(self.num_features2, 32) if num_classes > 0 else nn.Identity(),
            nn.ReLU(inplace=True),
            nn.Linear(32, num_classes)
        )
        self.loss_op = nn.L1Loss()
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.trunc_normal_(m.weight, std=.02)
            if isinstance(m, nn.Linear) and m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.bias, 0)
            nn.init.constant_(m.weight, 1.0)

    def forward(self, x):
        # x = x["face"].cuda()
        x = self.EfficientNet_b0_stage1(x)
        res1 = x
        C, H, W = x.shape[1], x.shape[2], x.shape[3]
        x = x.view(-1, C, H*W).transpose(1, 2).contiguous()
        x = self.pos_drop(x)
        for layer in self.layers:
            x, H, W = layer(x, H, W)
        x = self.norm(x)
        x = x.transpose(1, 2).contiguous().reshape([-1, C, H, W])
        x = x + res1


        x = self.EfficientNet_b0_stage2(x)
        res2 = x
        C, H, W = x.shape[1], x.shape[2], x.shape[3]
        x = x.view(-1, C, H*W).transpose(1, 2).contiguous()
        x = self.pos_drop1(x)
        for layer in self.layers1:
            x, H, W = layer(x, H, W)
        x = self.norm1(x)
        x = x.transpose(1, 2).contiguous().reshape([-1, C, H, W])
        x = x + res2


        x = self.EfficientNet_b0_stage3(x)
        x = self.conv(x)
        res3 = x
        C, H, W = x.shape[1], x.shape[2], x.shape[3]
        x = x.view(-1, C, H * W).transpose(1, 2).contiguous()
        x = self.pos_drop2(x)
        for layer in self.layers2:
            x, H, W = layer(x, H, W)
        x = self.norm2(x)
        x = x.transpose(1, 2).contiguous().reshape([-1, C, H, W])
        x = x + res3

        residual = self.conv2d_res(x)
        x = self.conv2d(x)
        x = self.ca(x) * x
        x = self.sa(x) * x
        x = x + residual

        x = x.reshape([-1, 96, 9])
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        gaze = self.head(x)
        return gaze


    def loss(self, x_in, label):
        gaze = self.forward(x_in)
        loss = self.loss_op(gaze, label)
        return loss

def FGI_Net(num_classes: int = 2, **kwargs):
    model = FGI(in_chans=3,
                depths=[(2,), (2,), (2,)],
                embed_dim = [24,40,96],
                num_heads=[(2,), (4,), (8,)],
                num_classes=num_classes,
                **kwargs)
    return model

