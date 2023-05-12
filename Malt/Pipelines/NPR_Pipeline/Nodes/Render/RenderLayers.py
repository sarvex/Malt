from Malt.GL import GL
from Malt.GL.Texture import Texture
from Malt.GL.RenderTarget import RenderTarget
from Malt.PipelineNode import PipelineNode
from Malt.PipelineParameters import Parameter, Type

_BLEND_TRANSPARENCY_SHADER = None

class RenderLayers(PipelineNode):
    """
    Renders the scene geometry, using multiple *depth peeling* layers for transparent objects.  
    The node sockets are dynamic, based on the graph selected.  
    """

    def __init__(self, pipeline):
        PipelineNode.__init__(self, pipeline)
        self.resolution = None
        self.texture_targets = {}
        self.render_target = None
        self.custom_io = []
    
    @staticmethod
    def get_pass_type():
        return 'Render Layer.Render Layer'
    
    @classmethod
    def reflect_inputs(cls):
        inputs = {'Scene': Parameter('Scene', Type.OTHER)}
        inputs['Transparent Layers'] = Parameter(4, Type.INT, doc="""
            The maximum number of overlapping transparency layers.  
            Incresing this values lowers performance.
        """)
        inputs['Transparent Layers @ Preview'] = Parameter(2, Type.INT)
        return inputs
    
    @classmethod
    def reflect_outputs(cls):
        return {}
    
    def setup_render_targets(self, resolution, custom_io):
        self.opaque_targets = {}
        self.transparent_targets = {}
        self.color_targets = {}
        
        for io in custom_io:
            if io['io'] == 'out' and io['type'] == 'Texture':#TODO
                self.opaque_targets[io['name']] = Texture(resolution, GL.GL_RGBA16F)
                self.transparent_targets[io['name']] = Texture(resolution, GL.GL_RGBA16F)
                self.color_targets[io['name']] = Texture(resolution, GL.GL_RGBA16F)
        
        self.fbo_opaque = RenderTarget([*self.opaque_targets.values()])
        self.fbo_transparent = RenderTarget([*self.transparent_targets.values()])
        self.fbo_color = RenderTarget([*self.color_targets.values()])
    
    def blend_transparency(self, back_textures, front_textures, fbo):
        global _BLEND_TRANSPARENCY_SHADER
        if _BLEND_TRANSPARENCY_SHADER is None:
            _BLEND_TRANSPARENCY_SHADER = self.pipeline.compile_shader_from_source('#include "Passes/BlendTransparency.glsl"')
        for i in range(len(fbo.targets)):
            _BLEND_TRANSPARENCY_SHADER.textures[f'IN_BACK[{str(i)}]'] = back_textures[i]
            _BLEND_TRANSPARENCY_SHADER.textures[f'IN_FRONT[{str(i)}]'] = front_textures[i]
        self.pipeline.draw_screen_pass(_BLEND_TRANSPARENCY_SHADER, fbo)
    
    def execute(self, parameters):
        inputs = parameters['IN']
        outputs = parameters['OUT']
        custom_io = parameters['CUSTOM_IO']
        graph = parameters['PASS_GRAPH']
        scene = inputs['Scene']
        if scene and graph:
            if self.pipeline.resolution != self.resolution or self.custom_io != custom_io:
                self.setup_render_targets(self.pipeline.resolution, custom_io)
                self.resolution = self.pipeline.resolution
                self.custom_io = custom_io

            self.fbo_color.clear([(0,0,0,0)]*len(self.fbo_color.targets))
            self.fbo_transparent.clear([(0,0,0,0)]*len(self.fbo_transparent.targets))

            self.layer_index = 0
            self.layer_count = inputs['Transparent Layers'] + 1
            graph['parameters']['__RENDER_LAYERS__'] = self
            for i in range(self.layer_count):
                graph['parameters']['__LAYER_INDEX__'] = self.layer_index
                graph['parameters']['__LAYER_COUNT__'] = self.layer_count
                self.pipeline.graphs['Render Layer'].run_source(self.pipeline, graph['source'], graph['parameters'], inputs, outputs)
                results = [
                    outputs[io['name']]
                    for io in self.custom_io
                    if io['io'] == 'out' and io['type'] == 'Texture'
                ]
                if i == 0:
                    self.pipeline.copy_textures(self.fbo_opaque, results)
                else:
                    self.blend_transparency(results, self.fbo_transparent.targets, self.fbo_color)
                    self.pipeline.copy_textures(self.fbo_transparent, self.fbo_color.targets)
                self.layer_index += 1     

            self.blend_transparency(self.fbo_opaque.targets, self.fbo_transparent.targets, self.fbo_color)
            outputs.update(self.color_targets)


NODE = RenderLayers  
