from Malt.GL.GL import *
from Malt.GL.Texture import Texture
from Malt.GL.RenderTarget import RenderTarget
from Malt.PipelineNode import PipelineNode
from Malt.PipelineParameters import Parameter, Type
from Malt.Scene import TextureShaderResource

class MainPass(PipelineNode):
    """
    Renders the scene geometry using the *Mesh Main Pass*.  
    The node sockets are dynamic, based on the *Main Pass Custom IO*.  
    If *Normal Depth/ID* is empty, the *Pre Pass* *Normal Depth/ID* will be used.
    """

    def __init__(self, pipeline):
        PipelineNode.__init__(self, pipeline)
        self.resolution = None
        self.t_depth = None
    
    @staticmethod
    def get_pass_type():
        return 'Mesh.MAIN_PASS_PIXEL_SHADER'
    
    @classmethod
    def reflect_inputs(cls):
        inputs = {'Scene': Parameter('Scene', Type.OTHER)}
        inputs['Normal Depth'] = Parameter('', Type.TEXTURE)
        inputs['ID'] = Parameter('', Type.TEXTURE)
        return inputs
    
    @classmethod
    def reflect_outputs(cls):
        return {}
    
    def setup_render_targets(self, resolution, t_depth, custom_io):
        self.custom_targets = {}
        for io in custom_io:
            if io['io'] == 'out' and io['type'] == 'Texture':#TODO
                formats = {
                    'float' : GL.GL_R16F,
                    'vec2' : GL.GL_RG16F,
                    'vec3' : GL.GL_RGB16F,
                    'vec4' : GL.GL_RGBA16F,
                }
                self.custom_targets[io['name']] = Texture(resolution, formats[io['subtype']])
        self.t_depth = t_depth
        self.fbo = RenderTarget([*self.custom_targets.values()], self.t_depth)

    def execute(self, parameters):
        inputs = parameters['IN']
        outputs = parameters['OUT']
        custom_io = parameters['CUSTOM_IO']

        scene = inputs['Scene']
        if scene is None:
            return
        t_id = inputs['ID']

        shader_resources = scene.shader_resources.copy()
        if t_normal_depth := inputs['Normal Depth']:
            shader_resources['IN_NORMAL_DEPTH'] = TextureShaderResource('IN_NORMAL_DEPTH', t_normal_depth)
        if t_id:
            shader_resources['IN_ID'] = TextureShaderResource('IN_ID', t_id)

        t_depth = shader_resources['T_DEPTH'].texture
        if self.pipeline.resolution != self.resolution or self.custom_io != custom_io or t_depth != self.t_depth:
            self.setup_render_targets(self.pipeline.resolution, t_depth, custom_io)
            self.resolution = self.pipeline.resolution
            self.custom_io = custom_io

        for io in custom_io:
            if io['io'] == 'in' and io['type'] == 'Texture':
                from Malt.SourceTranspiler import GLSLTranspiler
                glsl_name = GLSLTranspiler.custom_io_reference('IN', 'MAIN_PASS_PIXEL_SHADER', io['name'])
                shader_resources[f'CUSTOM_IO{glsl_name}'] = TextureShaderResource(
                    glsl_name, inputs[io['name']]
                )

        self.fbo.clear([(0,0,0,0)] * len(self.fbo.targets))
        self.pipeline.draw_scene_pass(self.fbo, scene.batches, 'MAIN_PASS', self.pipeline.default_shader['MAIN_PASS'], 
            shader_resources, GL_EQUAL)

        outputs.update(self.custom_targets)

NODE = MainPass
