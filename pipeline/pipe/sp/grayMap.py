import substance_painter as sp
import substance_painter.layerstack as ls
from substance_painter.layerstack import Stack

def printData(layer, grouppos, rl, stack):
    #ls.insert(layer, grouppos) I wish it was this simple
    print("layer attributes:\n")
    print(dir(layer))
    print("group attributes:\n")
    print(dir(grouppos))   
    print("group attributes:\n")
    print(dir(grouppos.sub_layers))
    print("rl attributes:\n")
    print(dir(rl))
    print("stack attributes:\n")
    print(dir(stack))
    print("ls attributes:\n")
    print(dir(ls))

    print("Using only these attributes, please help me to move an item of type \"layer\" into type \"group\".")
    grouppos.add_mask(layer)

    pass

def groupAllLayersToAnchor(stack:Stack):
    root_layers = ls.get_root_layer_nodes(stack)
    for layer in root_layers:
        if (isinstance(layer, ls.LayerNode)):
            print(layer)  # If output is long, haha fix it.
    toppos = ls.InsertPosition.from_textureset_stack(stack)
    group = ls.insert_group(toppos)
    group.set_name("Anchored Group")
    for layer in root_layers:
        grouppos = ls.InsertPosition.inside_node(group, ls.NodeStack.Substack)
        printData(layer, group, root_layers, stack)  # DOES NOT EXIST: FIND OUT HOW TO DO THIS
    group_content = ls.InsertPosition.inside_node(group, ls.NodeStack.Content)
    anchor = ls.insert_anchor_point_effect(group_content)
    anchor.set_name("Actual Anchor Point")
    pass


def addTopGrayscaleFillLayer(stack:Stack):
    root_layers = ls.get_root_layer_nodes(stack)
    top = root_layers[0]
    above = ls.InsertPosition.above_node(top)
    gradient = ls.insert_fill(above)
    gradient.set_name("Grayscale Gradient Fill")

    gradient_res = None # TODO make it something sp.resource.search("s:? u:? n:?")[0]
    gradient.set_material_source(gradient_res.identifier())

    pos = ls.InsertPosition.inside_node(gradient, ls.NodeStack.Content)
    gsfilter = None # sp.resource.search("s:? u:? n:?")
    ls.insert_filter_effect(pos, gsfilter.identifier())

    pass




def grayMap():
    stack = sp.textureset.get_active_stack()
    groupAllLayersToAnchor(stack=stack)
    addTopGrayscaleFillLayer(stack=stack)
    pass