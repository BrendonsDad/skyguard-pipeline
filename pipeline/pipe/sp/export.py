from __future__ import annotations

import substance_painter as sp

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
# from PIL import Image

if TYPE_CHECKING:
    import typing

    RT = typing.TypeVar("RT")  # return type

from pipe.sp.local import get_main_qt_window
from pipe.db import DB
from pipe.struct.db import Asset
from pipe.struct.material import (
    DisplacementSource,
    NormalSource,
    NormalType,
    TexSetInfo,
    MaterialInfo,
)
from pipe.glui.dialogs import MessageDialog
from shared.util import get_production_path, resolve_mapped_path
from env_sg import DB_Config


lib_path = resolve_mapped_path(Path(__file__).parents[1] / "lib")
log = logging.getLogger(__name__)


@dataclass
class TexSetExportSettings:
    tex_set: sp.textureset.TextureSet
    extra_channels: set[sp.textureset.Channel]
    resolution: int
    displacement_source: DisplacementSource
    normal_type: NormalType
    normal_source: NormalSource
    export_emission: bool


# TODO: remove renderman export settings



# Note: All 4 of the inputs for this one are meant to be 2-dimensional arrays with their associated values ranging from 1 to 255. (preferred, though I suppose larger values could be used. It just spikes the filesize if you choose to save it) 
# HOW TO USE OUTPUT: It is a numpy array. Slicing, slicing, slicing. output[:,:,0] is metal, 1 is occlusion, 2 is roughness, 3 is a gradient mask

class Exporter:
    """Class to manage exporting and converting textures"""

    _asset: Asset
    _conn: DB
    _out_path: Path
    _config_path: Path

    def __init__(self) -> None:
        self._conn = DB.Get(DB_Config)
        id = sp.project.Metadata(
            "LnD"
        ).get(
            "asset_id"
        )  # TODO: talk to Scott about what the project.Metadata is and if I need to configure my own
        assert (a := self._conn.get_asset_by_id(id)) is not None
        self._asset = a

    def _init_paths(self, mat_var: str) -> None:
        # initialize paths, pulling from SG database
        assert self._asset.tex_path is not None
        base_path = get_production_path() / self._asset.tex_path

        self._out_path = resolve_mapped_path(base_path)
        self._config_path = self._out_path / "mat_config"

        # create paths if not exist
        self._out_path.mkdir(parents=True, exist_ok=True)
        self._config_path.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        exp_setting_arr: typing.Sequence[TexSetExportSettings],
        mat_var: str,
    ) -> bool:
        """Export all the textures of the given Texture Sets"""
        self._init_paths(mat_var)

        try:
            [tss.tex_set.get_stack() for tss in exp_setting_arr]
        except ValueError:
            MessageDialog(
                get_main_qt_window(),
                "Warning! Exporter could not get stack! You are doing something cool with material layering. Please show this to Scott so he can fix it.",
            ).exec_()
            return False

        config = Exporter._generate_config(self._out_path, exp_setting_arr)
        log.debug(config)

        # NOTE: This needs to be left in in order for anything to actually export
        export_result: sp.export.TextureExportResult
        try:
            export_result = sp.export.export_project_textures(config)
        except Exception as e:
            print(e)
            return False
        log.debug(export_result)  # added so ruff doesn't get mad at me

        self.write_mat_info(exp_setting_arr)

        return True

    

    def write_mat_info(
        self, export_settings_arr: typing.Iterable[TexSetExportSettings]
    ) -> bool:
        """Write out JSON file with information about the texturesets"""
        mat_info_path = self._config_path / "mat.json"
        old_mat_info: MaterialInfo
        if mat_info_path.exists():
            with open(mat_info_path, "r") as f:
                old_mat_info = MaterialInfo.from_json(f.read())
        else:
            old_mat_info = MaterialInfo()

        all_tex_sets = [ts.name() for ts in sp.textureset.all_texture_sets()]
        for tex_set in list(old_mat_info.tex_sets.keys()):
            if tex_set not in all_tex_sets:
                del old_mat_info.tex_sets[tex_set]

        new_mat_info = MaterialInfo(
            {
                **old_mat_info.tex_sets,
                **{
                    export_settings.tex_set.name(): TexSetInfo(
                        displacement_source=export_settings.displacement_source,
                        has_udims=export_settings.tex_set.has_uv_tiles(),
                        normal_source=export_settings.normal_source,
                        normal_type=export_settings.normal_type,
                    )
                    for export_settings in export_settings_arr
                },
            }
        )
        with open(str(self._config_path / "mat.json"), "w", encoding="utf-8") as f:
            f.write(new_mat_info.to_json())
        return True

    @staticmethod
    def _generate_config(
        asset_path: Path, export_settings_arr: typing.Iterable[TexSetExportSettings]
    ) -> dict:
        return {
            "exportPath": str(asset_path),
            "exportShaderParams": True,
            "exportPresets": [
                {
                    "name": export_settings.tex_set.name(),
                    "maps": [
                        # Preview Surface
                        *Exporter._preview_surface_maps(
                            export_settings.export_emission
                        ),
                    ],
                }
                for export_settings in export_settings_arr
            ],
            "exportList": [
                {
                    "rootPath": str(export_settings.tex_set.get_stack()),
                    "exportPreset": export_settings.tex_set.name(),
                }
                for export_settings in export_settings_arr
            ],
            "exportParameters": [
                {
                    "parameters": {
                        "dithering": False,
                        "paddingAlgorithm": "color",
                        "dilationDistance": 24,
                    }
                }
            ],
        }

    @staticmethod
    def _shader_maps(export_settings: TexSetExportSettings) -> list:
        maps = [
            {
                "fileName": "$textureSet_BaseColor(_$colorSpace)(.$udim)",
                "channels": [
                    {
                        "destChannel": ch,
                        "srcChannel": ch,
                        "srcMapType": "documentMap",
                        "srcMapName": "baseColor",
                    }
                    for ch in "RGB"
                ],
                "parameters": {
                    "bitDepth": "16",
                    "fileFormat": "png",
                    "sizeLog2": export_settings.resolution,
                },
            },
            {
                "fileName": "$textureSet_Metallic(_$colorSpace)(.$udim)",
                "channels": [
                    {
                        "destChannel": "L",
                        "srcChannel": "L",
                        "srcMapType": "documentMap",
                        "srcMapName": "metallic",
                    },
                ],
                "parameters": {
                    "bitDepth": "8",
                    "fileFormat": "png",
                    "sizeLog2": export_settings.resolution,
                },
            },
            {
                "fileName": "$textureSet_IOR(_$colorSpace)(.$udim)",
                "channels": [
                    {
                        "destChannel": "L",
                        "srcChannel": "L",
                        "srcMapType": "documentMap",
                        "srcMapName": "specular",
                    },
                ],
                "parameters": {
                    "bitDepth": "8",
                    "fileFormat": "png",
                    "sizeLog2": export_settings.resolution,
                },
            },
            {
                "fileName": "$textureSet_SpecularRoughness(_$colorSpace)(.$udim)",
                "channels": [
                    {
                        "destChannel": "L",
                        "srcChannel": "L",
                        "srcMapType": "documentMap",
                        "srcMapName": "roughness",
                    },
                ],
                "parameters": {
                    "bitDepth": "8",
                    "fileFormat": "png",
                    "sizeLog2": export_settings.resolution,
                },
            },
            {
                "fileName": "$textureSet_Emissive(_$colorSpace)(.$udim)",
                "channels": [
                    {
                        "destChannel": ch,
                        "srcChannel": ch,
                        "srcMapType": "documentMap",
                        "srcMapName": "emissive",
                    }
                    for ch in "RGB"
                ],
                "parameters": {
                    "bitDepth": "16",
                    "fileFormat": "png",
                    "sizeLog2": export_settings.resolution,
                },
            },
            {
                "fileName": "$textureSet_Presence(_$colorSpace)(.$udim)",
                "channels": [
                    {
                        "destChannel": "L",
                        "srcChannel": "L",
                        "srcMapType": "documentMap",
                        "srcMapName": "opacity",
                    },
                ],
                "parameters": {
                    "bitDepth": "8",
                    "fileFormat": "png",
                    "sizeLog2": export_settings.resolution,
                },
            },
            {
                "fileName": f"$textureSet_Normal(_$colorSpace)(.$udim){'.pre-b2r' if export_settings.normal_type == NormalType.BUMP_ROUGHNESS else ''}",
                "channels": [
                    {
                        "destChannel": ch,
                        "srcChannel": ch,
                        **(
                            {
                                "srcMapType": "virtualMap",
                                "srcMapName": "Normal_OpenGL",
                            }
                            if export_settings.normal_source
                            is NormalSource.NORMAL_HEIGHT
                            else {
                                "srcMapType": "documentMap",
                                "srcMapName": "normal",
                            }
                        ),
                    }
                    for ch in "RGB"
                ],
                "parameters": {
                    **(
                        {
                            "bitDepth": "16f",
                            "fileFormat": "exr",
                        }
                        if export_settings.normal_type is NormalType.BUMP_ROUGHNESS
                        else {
                            "bitDepth": "16",
                            "fileFormat": "png",
                        }
                    ),
                    "sizeLog2": export_settings.resolution,
                },
            },
        ]

        if export_settings.displacement_source is not DisplacementSource.NONE:
            maps += [
                {
                    "fileName": "$textureSet_Displacement(_$colorSpace)(.$udim)",
                    "channels": [
                        {
                            "destChannel": "L",
                            "srcChannel": "L",
                            "srcMapType": "documentMap",
                            "srcMapName": (
                                "height"
                                if export_settings.displacement_source
                                == DisplacementSource.HEIGHT
                                else "displacement"
                            ),
                        },
                    ],
                    "parameters": {
                        "bitDepth": "16",
                        "fileFormat": "png",
                        "sizeLog2": export_settings.resolution,
                    },
                }
            ]

        return maps

    @staticmethod
    def _preview_surface_maps(should_export_emission: bool) -> list:
        surface_maps = [
            {
                "fileName": "T_$textureSet_BaseColor(.$udim)",
                "channels": [
                    {
                        "destChannel": ch,
                        "srcChannel": ch,
                        "srcMapType": "documentMap",
                        "srcMapName": "baseColor",
                    }
                    for ch in "RGB"
                ],
                "parameters": {
                    "bitDepth": "8",
                    "dithering": True,
                    "fileFormat": "png",
                },
            },
            {
                "fileName": "T_$textureSet_ORM(.$udim)",
                "channels": [
                    {
                        "destChannel": "R",
                        "srcChannel": "R",
                        "srcMapType": "documentMap",
                        "srcMapName": "opacity",
                    },
                    {
                        "destChannel": "G",
                        "srcChannel": "G",
                        "srcMapType": "documentMap",
                        "srcMapName": "roughness",
                    },
                    {
                        "destChannel": "B",
                        "srcChannel": "B",
                        "srcMapType": "documentMap",
                        "srcMapName": "metallic",
                    },
                ],
                "parameters": {
                    "bitDepth": "8",
                    "fileFormat": "png",
                },
            },
            {
                "fileName": "T_$textureSet_Normal(.$udim)",
                "channels": [
                    {
                        "destChannel": ch,
                        "srcChannel": ch,
                        "srcMapType": "virtualMap",
                        "srcMapName": "Normal_DirectX",
                    }
                    for ch in "RGB"
                ],
                "parameters": {
                    "bitDepth": "8",
                    "fileFormat": "png",
                },
            },
        ]
        if should_export_emission:
            surface_maps.append(
                {
                    "fileName": "T_$textureSet_Emissive(.$udim)",
                    "channels": [
                        {
                            "destChannel": ch,
                            "srcChannel": ch,
                            "srcMapType": "documentMap",
                            "srcMapName": "emissive",
                        }
                        for ch in "RGB"
                    ],
                    "parameters": {
                        "bitDepth": "8",
                        "dithering": True,
                        "fileFormat": "png",
                    },
                },
            )
        return surface_maps
