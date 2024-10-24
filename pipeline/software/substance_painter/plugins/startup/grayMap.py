from __future__ import annotations

from Qt import QtWidgets

import substance_painter as sp

import pipe.sp
from pipe.sp.grayMap import grayMap


plugin_widgets: list[QtWidgets.QWidget] = []


def start_plugin():
    # Create text widget for menu
    action = QtWidgets.QAction("GrayScale Mapping")
    action.triggered.connect(grayMap)

    # Add widget to the File menu
    sp.ui.add_action(sp.ui.ApplicationMenu.Edit, action)

    # Store the widget for proper cleanup later
    plugin_widgets.append(action)


def close_plugin():
    for widget in plugin_widgets:
        sp.ui.delete_ui_element(widget)

    plugin_widgets.clear()


if __name__ == "__main__":
    window = start_plugin()



