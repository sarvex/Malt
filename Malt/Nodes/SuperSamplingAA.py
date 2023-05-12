from Malt.GL.GL import *
from Malt.GL.Texture import Texture
from Malt.GL.RenderTarget import RenderTarget
from Malt.PipelineNode import PipelineNode
from Malt.PipelineParameters import Parameter, Type

class SuperSamplingAA(PipelineNode):

    """
    Performs anti-aliasing by accumulating multiple render samples into a single texture.
    """

    def __init__(self, pipeline):
        PipelineNode.__init__(self, pipeline)
        self.resolution = None
    
    @classmethod
    def reflect_inputs(cls):
        return {'Color': Parameter('', Type.TEXTURE)}
    
    @classmethod
    def reflect_outputs(cls):
        return {'Color': Parameter('', Type.TEXTURE)}
    
    def setup_render_targets(self, resolution):
        self.t_color = Texture(resolution, GL_RGBA16F)
        self.fbo = RenderTarget([self.t_color])

    def execute(self, parameters):
        inputs = parameters['IN']
        outputs = parameters['OUT']

        if self.pipeline.resolution != self.resolution:
            self.setup_render_targets(self.pipeline.resolution)
            self.resolution = self.pipeline.resolution
        
        if self.pipeline.is_new_frame:
            self.fbo.clear([(0,0,0,0)])
        if inputs['Color']:
            self.pipeline.blend_texture(inputs['Color'], self.fbo, 1.0 / (self.pipeline.sample_count + 1))
            outputs['Color'] = self.t_color

NODE = SuperSamplingAA
