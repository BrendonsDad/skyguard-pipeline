from __future__ import annotations

import attrs
import cattrs

from attrs import field

# We need to always import typing for defining the structs
# attrs doesn't support `|` syntax in 3.9
from typing import Any, Optional, Type, TypeVar

from pipe.struct.util import Diffable

_S = TypeVar("_S")

_SG_NAME = "sg_name"
_STRUCT_HOOK = "struct_hook"
_UNSTRUCT_HOOK = "unstruct_hook"
_con = cattrs.Converter()

_con.register_structure_hook_factory(
    attrs.has,
    lambda cls: cattrs.gen.make_dict_structure_fn(
        cls,
        _con,
        **{  # type: ignore[arg-type]
            f.name: cattrs.gen.override(
                rename=f.metadata.get(_SG_NAME, None),
                struct_hook=f.metadata.get(_STRUCT_HOOK, None),
                unstruct_hook=f.metadata.get(_UNSTRUCT_HOOK, None),
            )
            for f in attrs.fields(cls)
        },
    ),
)


@attrs.define
class SGDiffable(Diffable):
    @classmethod
    def from_sg(cls: Type[_S], sg_dict: Optional[dict]) -> _S:
        if not sg_dict:
            raise TypeError(f"Cannot create {cls.__name__} from empty dict")
        return _con.structure(sg_dict, cls)

    @classmethod
    def map_sg_field_names(cls: Type[attrs.AttrsInstance], name: str) -> str:
        """take SG name and map it to the field name on this class"""
        return next(
            (
                f.metadata.get(_SG_NAME, None) or f.name
                for f in attrs.fields(cls)
                if f.name == name
            ),
            "",
        )

    def sg_diff(self) -> dict[str, Any]:
        """Return a dict with changes made to the asset since it was
        initialized, in the form that ShotGrid expects"""
        sg_diff: dict[str, Any] = self.diff()
        for f in attrs.fields(self.__class__):
            if f.name in sg_diff:
                if hk := f.metadata.get(_UNSTRUCT_HOOK, None):
                    sg_diff[f.name] = hk(sg_diff[f.name], None)
                if nname := f.metadata.get(_SG_NAME, None):
                    sg_diff[nname] = sg_diff[f.name]
                    del sg_diff[f.name]
        return sg_diff


@attrs.define
class SGEntity(SGDiffable):
    code: str
    id: int = field(on_setattr=attrs.setters.frozen)
    path: Optional[str] = field(metadata={_SG_NAME: "sg_path"})


@attrs.define
class SGEntityStub(SGDiffable):
    id: int


@attrs.frozen
class AssetStub(SGEntityStub):
    """Represent "stubs" that come from ShotGrid
    Stubs are JSON objects with 3 fields: id, name, and type (which is always Asset in this case)
    """

    disp_name: str = field(metadata={_SG_NAME: "name"})


@attrs.define
class Asset(SGEntity):
    name: str = field(metadata={_SG_NAME: "sg_pipe_name"})
    material_variants: set[str] = field(
        metadata={
            _SG_NAME: "sg_material_variants",
            _STRUCT_HOOK: lambda mv, _: set(mv.split(",") if mv else []),
            _UNSTRUCT_HOOK: lambda mv, _: ",".join(mv) if mv else "",
        }
    )
    parent: Optional[AssetStub] = field(
        metadata={
            _SG_NAME: "parents",
            _STRUCT_HOOK: lambda p, _: AssetStub.from_sg(p[0]) if len(p) else None,
            _UNSTRUCT_HOOK: lambda p, _: [p] if p else [],
        },
        on_setattr=attrs.setters.frozen,
    )
    version = None

    @property
    def disp_name(self) -> str:
        """Alias for code"""
        return self.code or ""

    @property
    def tex_path(self) -> Optional[str]:
        return f"{self.path}/textures/"


@attrs.frozen
class SequenceStub(SGEntityStub):
    """Represent sequence "stubs" that come from ShotGrid"""

    code: str = field(metadata={_SG_NAME: "name"})


@attrs.define
class Sequence(SGEntity):
    code: str = field(on_setattr=attrs.setters.frozen)
    shots: list[ShotStub]


@attrs.frozen
class ShotStub(SGEntityStub):
    """Represent shot "stubs" that come from ShotGrid"""

    code: str = field(metadata={_SG_NAME: "name"})


@attrs.define
class Shot(SGEntity):
    assets: list[AssetStub] = field(
        metadata={_STRUCT_HOOK: lambda aa, _: [AssetStub.from_sg(a) for a in aa]}
    )
    code: str = field(on_setattr=attrs.setters.frozen)
    cut_in: int = field(metadata={_SG_NAME: "sg_cut_in"})
    cut_out: int = field(metadata={_SG_NAME: "sg_cut_out"})
    cut_duration: int = field(metadata={_SG_NAME: "sg_cut_duration"})
    sequence: SequenceStub = field(metadata={_SG_NAME: "sg_sequence"})
