from Malt.GL import GL
from Malt.GL.Texture import Texture
from Malt.GL.RenderTarget import RenderTarget
from Malt.PipelineNode import PipelineNode
from Malt.PipelineParameters import Parameter, Type
from Malt.Scene import TextureShaderResource


class ScreenPass(PipelineNode):
    """
    Renders a full screen shader pass.  
    The node sockets are dynamic, based on the shader selected.  
    If *Normal Depth/ID* is empty, the *PrePass* *Normal Depth/ID* will be used.
    """

    def __init__(self, pipeline):
        PipelineNode.__init__(self, pipeline)
        self.resolution = None
        self.texture_targets = {}
        self.render_target = None
        self.custom_io = []
    
    @staticmethod
    def get_pass_type():
        return 'Screen.SCREEN_SHADER'
    
    @classmethod
    def reflect_inputs(cls):
        inputs = {
            'Layer Only': Parameter(
                True,
                Type.BOOL,
                doc="""
            Draw only on top of the current layer geometry,
            to avoid accidentally covering previous layers.
        """,
            )
        }
        inputs['Scene'] = Parameter('Scene', Type.OTHER)
        inputs['Normal Depth'] = Parameter('', Type.TEXTURE)
        inputs['ID'] = Parameter('', Type.TEXTURE)
        return inputs
    
    def execute(self, parameters):
        inputs = parameters['IN']
        outputs = parameters['OUT']
        material = parameters['PASS_MATERIAL']
        custom_io = parameters['CUSTOM_IO']

        scene = inputs['Scene']
        t_id = inputs['ID']

        shader_resources = scene.shader_resources.copy() if scene else {}
        if t_normal_depth := inputs['Normal Depth']:
            shader_resources['IN_NORMAL_DEPTH'] = TextureShaderResource('IN_NORMAL_DEPTH', t_normal_depth)
        if t_id:
            shader_resources['IN_ID'] = TextureShaderResource('IN_ID', t_id)

        if self.pipeline.resolution != self.resolution or self.custom_io != custom_io:
            self.texture_targets = {}
            for io in custom_io:
                if io['io'] == 'out' and io['type'] == 'Texture':
                    self.texture_targets[io['name']] = Texture(self.pipeline.resolution, GL.GL_RGBA16F)
            self.render_target = RenderTarget([*self.texture_targets.values()])
            self.resolution = self.pipeline.resolution
            self.custom_io = custom_io

        self.render_target.clear([(0,0,0,0)]*len(self.texture_targets))

        if material and material.shader and 'SHADER' in material.shader:
            shader = material.shader['SHADER']
            for io in custom_io:
                if io['io'] == 'in' and io['type'] == 'Texture':
                    from Malt.SourceTranspiler import GLSLTranspiler
                    glsl_name = GLSLTranspiler.custom_io_reference('IN', 'SCREEN_SHADER', io['name'])
                    shader.textures[glsl_name] = inputs[io['name']]
            self.pipeline.common_buffer.bind(shader.uniform_blocks['COMMON_UNIFORMS'])
            for resource in shader_resources.values():
                resource.shader_callback(shader)
            shader.uniforms['RENDER_LAYER_MODE'].set_value(True)
            deferred_mode = inputs['Layer Only']
            shader.uniforms['DEFERRED_MODE'].set_value(deferred_mode)
            self.pipeline.draw_screen_pass(shader, self.render_target)

        for io in custom_io:
            if io['io'] == 'out' and io['type'] == 'Texture':
                outputs[io['name']] = self.texture_targets[io['name']]


NODE = ScreenPass    
