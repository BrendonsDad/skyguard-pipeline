from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import hou
import json

import pipe
from pipe.db import DB
from pipe.struct import Asset
from pipe.glui.dialogs import MessageDialog

from env import SG_Config

MATLIB_NAME = "Material_Library"


# https://github.com/Student-Accomplice-Pipeline-Team/accomplice_pipe/blob/prod/pipe/accomplice/software/houdini/pipe/tools/shading/edit_shader.py
class MatlibManager:
    _conn: DB

    def __init__(self) -> None:
        self._conn = DB(SG_Config)

    @property
    def _asset(self) -> Asset:
        """Get asset based off of the path of the current hipfile"""
        a = self._conn.get_asset_by_attr("sg_pipe_name", self._hip.name)
        assert a is not None
        return a

    @property
    def _hip(self) -> Path:
        """Get $HIP variable as a Path object"""
        return Path(hou.hscriptExpression("$HIP"))

    @property
    def _hsite(self) -> Path:
        """Get $HSITE variable as a Path object"""
        return Path(hou.hscriptExpression("$HSITE"))

    @property
    def mat_info(self) -> Optional[List[Dict[str, Any]]]:
        """Attempt to get mat.json file for selected variant"""
        try:
            variant = self._conn.get_asset_by_id(self.variant_id)
            assert variant is not None

            if not (variant_name := variant.variant_name):
                variant_name = "main"
            
            with open(self._hip / "tex" / variant_name / "mat.json", "r") as f:
                return json.load(f)
        except:
            return None

    @property
    def matlib(self) -> hou.LopNode:
        """Get Material Library node inside of current node"""
        return hou.node(f"./{MATLIB_NAME}")

    @property
    def node(self) -> hou.LopNode:
        """Get current node (the HDA)"""
        return hou.node("./")

    @property
    def variant_id(self) -> int:
        """Get the id of the current variant"""
        if (node_val := self.node.parm("variant_id").evalAsInt()) == -1:
            ## if it hasn't been set yet, set it to the default value
            default = int(self.get_variant_list()[0])
            self.node.parm("variant_id").set(default)
            return default
        return node_val

    @variant_id.setter
    def variant_id(self, id: int) -> None:
        """Set the variant ID and update the variant name"""
        self.node.parm("variant_id").set(id)
        asset = self._conn.get_asset_by_id(id)
        assert asset is not None
        if self._asset.variants:
            self.node.parm("variant_name").set(asset.variant_name)
        else:
            self.node.parm("variant_name").set("main")

    @property
    def variant_name(self) -> str:
        if (node_val := self.node.parm("variant_name").evalAsString()) == "none":
            variants = self._asset.variants
            variant_name: str
            if variants:
                var1 = self._conn.get_asset_by_stub(variants[0])
                assert var1 is not None
                variant_name = var1.variant_name
            else:
                variant_name = "main"
            self.node.parm("variant_name").set(variant_name)
            return var1.variant_name
        return node_val

    def _load_items_from_file(
        self, dest_node: hou.LopNode, file_path: str
    ) -> List[hou.NetworkMovableItem]:
        """Loads a VOP network into a LOP node. Returns list of added items"""
        before = dest_node.allItems()
        dest_node.loadItemsFromFile(file_path)
        after = dest_node.allItems()

        return list(set(after) - set(before))

    def _rename_matnet(
        self,
        new_items: Iterable[hou.NetworkMovableItem],
        name: str,
        name_placeholder: str = "matname",
    ) -> None:
        # iterate over new nodes and swap placeholder names for the shading group name
        for item in new_items:
            if item.networkItemType() == hou.networkItemType.Node:
                new_name = item.name().replace(name_placeholder, name)
                item.setName(new_name)

                # update "Shading Group Name" on control null
                if new_name == f"CONTROLS_{name}":
                    node = hou.node(item.path())
                    node.parm("name").set(name)

    def get_variant_list(self) -> List[str]:
        """Gets list of variants in the way that the HDA interface expects:
        [id1, label1, id2, label2, ...]"""
        if len(self._asset.variants):
            return [s for v in self._asset.variants for s in (str(v.id), v.disp_name)]
        else:
            return [str(self._asset.id), "Main"]

    def import_matnets(self) -> None:
        """Import a material network for each shading group in the export"""
        if not (mat_info := self.mat_info):
            MessageDialog(
                pipe.local.get_main_qt_window(),
                "Error! Could not get material info. Make sure that textures have been exported for the currently selected variant.",
            ).exec_()
            return

        for shading_group in mat_info:
            name = shading_group["name"]
            nodes = self._load_items_from_file(
                self.matlib, str(self._hsite / "matl/general.matl")
            )
            self._rename_matnet(nodes, name)

    def init_hda(self, node: hou.LopNode) -> None:
        """Initialize values on the HDA instance.
        Note that self.node does not work before initialization, so
        node is passed in as an arg"""
        variants = self._asset.variants
        if not variants:
            node.parm("variant_name").set("main")
            node.parm("variant_id").set(self._asset.id)
            return
        
        var2 = self._conn.get_asset_by_stub(self._asset.variants[0])
        assert var2 is not None
        node.parm("variant_name").set(var2.variant_name)
        node.parm("variant_id").set(var2.id)
