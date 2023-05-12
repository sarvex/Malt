from Malt.PipelineParameters import Parameter, Type
import bpy    
from BlenderMalt.MaltNodes.MaltNode import MaltNode


class MaltArrayIndexNode(bpy.types.Node, MaltNode):
    
    bl_label = "Array Index Node"

    def malt_init(self):
        self.setup()
        
    def malt_setup(self, copy=None):
        self.setup_sockets({ 'array' : {'type': '', 'size': 1}, 'index' : {'type': Parameter(0, Type.INT) }},
            {'element' : {'type': ''} }, copy=copy)
        
    def malt_update(self):
        inputs = { 
            'array' : {'type': '', 'size': 1},
            'index' : {'type': 'int', 'meta':{'value':'0'} }
        }
        outputs = { 'element' : {'type': ''} }
        
        linked = self.inputs['array'].get_linked()
        if linked and linked.array_size > 0:
            inputs['array']['type'] = linked.data_type
            inputs['array']['size'] = linked.array_size
            outputs['element']['type'] = linked.data_type

        self.setup_sockets(inputs, outputs)

    def get_source_socket_reference(self, socket):
        return f'{self.get_source_name()}_0_{socket.name}'
    
    def get_source_code(self, transpiler):
        array = self.inputs['array']
        index = self.inputs['index']
        element = self.outputs['element']
        element_reference = index.get_source_global_reference()
        if index.get_linked():
            element_reference = index.get_linked().get_source_reference()
        initialization = (
            f'{array.get_linked().get_source_reference()}[{element_reference}]'
        )
        return transpiler.declaration(element.data_type, element.array_size, element.get_source_reference(), initialization)

    
classes = [
    MaltArrayIndexNode,
]

def register():
    for _class in classes: bpy.utils.register_class(_class)
    
def unregister():
    for _class in reversed(classes): bpy.utils.unregister_class(_class)
