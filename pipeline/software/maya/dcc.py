from __future__ import annotations

import logging
import os
import platform
import shutil

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing

from ..baseclass import DCC
from shared.util import get_rigging_path
from env import Executables

log = logging.getLogger(__name__)


class MayaDCC(DCC):
    """Maya DCC class"""

    shelf_path: str

    def __init__(self, is_python_shell: bool = False) -> None:
        this_path = Path(__file__).resolve()
        pipe_path = this_path.parents[2]

        system = platform.system()

        self.shelf_path = str(
            Path(os.getenv("TMPDIR", os.getenv("TEMP", "tmp"))).resolve() / "shelves"
        )

        env_vars: typing.Mapping[str, int | str | None] | None
        env_vars = {
            "DCC": str(this_path.parent.name),
            "DWPICKER_PROJECT_DIRECTORY": str(get_rigging_path() / "Pickers"),
            "MAYA_SHELF_PATH": self.shelf_path,
            "MAYAUSD_EXPORT_MAP1_AS_PRIMARY_UV_SET": 1,
            "MAYAUSD_IMPORT_PRIMARY_UV_SET_AS_MAP1": 1,
            "PYTHONPATH": os.pathsep.join(
                [
                    str(pipe_path),
                    str(this_path.parent / "scripts"),
                    str(this_path.parent / "scripts/dwpicker_git"),
                    str(this_path.parent / "scripts/maya-timeline-marker_git/scripts"),
                    str(this_path.parent / "scripts/modelChecker_git"),
                    str(this_path.parent / "userSetup"),
                    str(this_path.parent / "scripts/studiolibrary/src"),
                ]
            ),
            "QT_FONT_DPI": os.getenv("MAYA_FONT_DPI") if system == "Linux" else None,
            "QT_PLUGIN_PATH": None,
            # Icons
            "XBMLANGPATH": os.pathsep.join(
                [
                    str(pth) + ("/%B" if system == "Linux" else "")
                    for pth in [
                        this_path.parent
                        / "scripts/studiolibrary/src/studiolibrary/resource/icons",
                        pipe_path / "lib/icon",
                    ]
                ]
            ),
        }

        launch_command = ""
        if is_python_shell:
            launch_command = str(Executables.mayapy)
        else:
            launch_command = str(Executables.maya)

        launch_args: list[str] = []

        super().__init__(
            launch_command, launch_args, env_vars, lambda: self.set_up_shelf_path()
        )

    def set_up_shelf_path(self) -> None:
        prod_dir = str(Path(__file__).parent / "shelves")
        local_dir = self.shelf_path

        shutil.copytree(prod_dir, local_dir, dirs_exist_ok=True)
