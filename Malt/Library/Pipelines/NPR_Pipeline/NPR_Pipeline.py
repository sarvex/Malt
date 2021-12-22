# Copyright (c) 2020-2021 BNPR, Miguel Pozo and contributors. MIT license.

from os import path

from Malt.Pipeline import *
from Malt.PipelineGraph import *
from Malt.PipelineNode import PipelineNode

from Malt.GL.GL import *

from Malt.Library.Render import Common
from Malt.Library.Render import DepthToCompositeDepth
from Malt.Library.Render import Sampling

from Malt.Library.Pipelines.NPR_Pipeline.NPR_Lighting import NPR_Lighting
from Malt.Library.Pipelines.NPR_Pipeline.NPR_LightShaders import NPR_LightShaders

from Malt.Library.Nodes import Unpack8bitTextures

from Malt.Library.Pipelines.NPR_Pipeline.Nodes import ScreenPass, PrePass, MainPass, CompositeLayers, SSAA, LineRender, RenderLayers

_COMMON_HEADER = '''
#include "NPR_Pipeline.glsl"
#include "Node Utils/node_utils.glsl"
'''

_SCREEN_SHADER_HEADER= _COMMON_HEADER + '''
#ifdef PIXEL_SHADER
void SCREEN_SHADER(vec2 uv);
void main(){ PIXEL_SETUP_INPUT(); SCREEN_SHADER(UV[0]); }
#endif //PIXEL_SHADER
'''

_DEFAULT_SHADER = None

_DEFAULT_SHADER_SRC='''
#include "NPR_Pipeline.glsl"

void PRE_PASS_PIXEL_SHADER(inout PrePassOutput PO){ }

void MAIN_PASS_PIXEL_SHADER() { }
'''

_BLEND_TRANSPARENCY_SHADER = None

_BLEND_TRANSPARENCY_SHADER_SRC='''
#include "Passes/BlendTransparency.glsl"
'''

class NPR_Pipeline(Pipeline):

    def __init__(self):
        super().__init__()

        shader_dir = path.join(path.dirname(__file__), 'Shaders')
        if shader_dir not in self.SHADER_INCLUDE_PATHS:
            self.SHADER_INCLUDE_PATHS.append(shader_dir)

        self.sampling_grid_size = 2
        self.samples = None

        self.parameters.world['Background.Color'] = Parameter((0.5,0.5,0.5,1), Type.FLOAT, 4)
        
        self.parameters.world['Samples.Grid Size'] = Parameter(8, Type.INT)
        self.parameters.world['Samples.Grid Size @ Preview'] = Parameter(4, Type.INT)
        self.parameters.world['Samples.Width'] = Parameter(1.0, Type.FLOAT)
        
        self.parameters.world['Transparency.Layers'] = Parameter(4, Type.INT)
        self.parameters.world['Transparency.Layers @ Preview'] = Parameter(1, Type.INT)
        
        default_material_path = os.path.join(os.path.dirname(__file__), 'default.mesh.glsl')
        self.parameters.world['Material.Default'] = MaterialParameter(default_material_path, '.mesh.glsl')
        
        self.parameters.world['Render'] = Parameter('Render', Type.GRAPH)
        self.render_layer_nodes = {}

        self.common_buffer = Common.CommonBuffer()
        self.npr_lighting = NPR_Lighting(self.parameters)
        self.npr_light_shaders = NPR_LightShaders(self.parameters)
        
        self.composite_depth = DepthToCompositeDepth.CompositeDepth()

        self.layer_query = DrawQuery()
        
        self.setup_graphs()
        
        global _DEFAULT_SHADER
        if _DEFAULT_SHADER is None: _DEFAULT_SHADER = self.compile_material_from_source('Mesh', _DEFAULT_SHADER_SRC)
        self.default_shader = _DEFAULT_SHADER

        global _BLEND_TRANSPARENCY_SHADER
        if _BLEND_TRANSPARENCY_SHADER is None: _BLEND_TRANSPARENCY_SHADER = self.compile_shader_from_source(_BLEND_TRANSPARENCY_SHADER_SRC)
        self.blend_transparency_shader = _BLEND_TRANSPARENCY_SHADER

    def get_mesh_shader_custom_outputs(self):
        return {
            'Line Color' : GL_RGBA16F,
            'Line Width' : GL_R16F,
        }
    
    def get_samples(self):
        if self.samples is None:
            self.samples = Sampling.get_RGSS_samples(self.sampling_grid_size, 1.0)
        return self.samples
    
    def get_sample(self, width):
        w, h = self.get_samples()[self.sample_count]
        w*=width
        h*=width
        return w, h
    
    def setup_graphs(self):
        mesh = GLSLPipelineGraph(
            name='Mesh',
            graph_type=GLSLPipelineGraph.SCENE_GRAPH,
            default_global_scope=_COMMON_HEADER,
            shaders=['PRE_PASS', 'MAIN_PASS', 'SHADOW_PASS'],
            graph_io=[
                GLSLGraphIO(
                    name='PRE_PASS_PIXEL_SHADER',
                    define='CUSTOM_PRE_PASS',
                    shader_type='PIXEL_SHADER',
                    dynamic_output_types=GLSLGraphIO.COMMON_OUTPUT_TYPES,
                    custom_output_start_index=2,
                ),
                GLSLGraphIO(
                    name='MAIN_PASS_PIXEL_SHADER',
                    shader_type='MAIN_PASS',
                    dynamic_input_types=GLSLGraphIO.COMMON_INPUT_TYPES,
                    dynamic_output_types=GLSLGraphIO.COMMON_OUTPUT_TYPES,
                ),
                GLSLGraphIO(
                    name='VERTEX_DISPLACEMENT_SHADER',
                    define='CUSTOM_VERTEX_DISPLACEMENT',
                    shader_type='VERTEX_SHADER'
                ),
                GLSLGraphIO(
                    name='COMMON_VERTEX_SHADER',
                    define='CUSTOM_VERTEX_SHADER',
                    shader_type='VERTEX_SHADER',
                ),
            ]
        )
        mesh.setup_reflection(self, _DEFAULT_SHADER_SRC)

        screen = GLSLPipelineGraph(
            name='Screen',
            graph_type=GLSLPipelineGraph.GLOBAL_GRAPH,
            default_global_scope=_SCREEN_SHADER_HEADER,
            graph_io=[ 
                GLSLGraphIO(
                    name='SCREEN_SHADER',
                    dynamic_input_types= GLSLGraphIO.COMMON_INPUT_TYPES,
                    dynamic_output_types= GLSLGraphIO.COMMON_OUTPUT_TYPES,
                    shader_type='PIXEL_SHADER',
                )
            ]
        )
        screen.setup_reflection(self, "void SCREEN_SHADER(vec2 uv){ }")
        
        MainPass.NODE.get_custom_outputs = self.get_mesh_shader_custom_outputs

        render_layer = PythonPipelineGraph(
            name='Render Layer',
            nodes = [ScreenPass.NODE, PrePass.NODE, MainPass.NODE, Unpack8bitTextures.NODE, CompositeLayers.NODE, LineRender.NODE],
            graph_io = [
                PythonGraphIO(
                    name = 'Render Layer',
                    dynamic_input_types= PythonGraphIO.COMMON_IO_TYPES,
                    dynamic_output_types= PythonGraphIO.COMMON_IO_TYPES,
                    function = PipelineNode.static_reflect(
                        name = 'Render Layer',
                        inputs = {
                            'Scene' : Parameter('Scene', Type.OTHER),
                        },
                        outputs = {
                            'Color' : Parameter('', Type.TEXTURE),
                        },
                    )
                )
            ]
        )

        render = PythonPipelineGraph(
            name='Render',
            nodes = [ScreenPass.NODE, RenderLayers.NODE, Unpack8bitTextures.NODE, SSAA.NODE, LineRender.NODE],
            graph_io = [
                PythonGraphIO(
                    name = 'Render',
                    dynamic_output_types= PythonGraphIO.COMMON_IO_TYPES,
                    function = PipelineNode.static_reflect(
                        name = 'Render',
                        inputs = {
                            'Scene' : Parameter('Scene', Type.OTHER),
                        },
                        outputs = {
                            'Color' : Parameter('', Type.TEXTURE),
                        },
                    )
                )
            ]
        )
        
        self.graphs |= {e.name : e for e in [mesh, screen, render_layer, render]}

        self.npr_light_shaders.setup_graphs(self, self.graphs)
    
    def get_scene_batches(self, scene):
        opaque_batches = {}
        transparent_batches = {}
        for material, meshes in scene.batches.items():
            if material and material.shader:
                if material.shader['PRE_PASS'].uniforms['Settings.Transparency'].value[0] == True:
                    transparent_batches[material] = meshes
                    continue
            opaque_batches[material] = meshes
        return opaque_batches, transparent_batches

    def do_render(self, resolution, scene, is_final_render, is_new_frame):
        #SETUP SAMPLING
        if self.sampling_grid_size != scene.world_parameters['Samples.Grid Size']:
            self.sampling_grid_size = scene.world_parameters['Samples.Grid Size']
            self.samples = None
        
        self.is_new_frame = is_new_frame
        
        sample_offset = self.get_sample(scene.world_parameters['Samples.Width'])

        opaque_batches, transparent_batches = self.get_scene_batches(scene)
        
        self.npr_lighting.load(self, scene, opaque_batches, transparent_batches, sample_offset, self.sample_count)

        self.common_buffer.load(scene, resolution, sample_offset, self.sample_count)
        
        result = None
        graph = scene.world_parameters['Render']
        if graph:
            IN = {'Scene' : scene}
            OUT = {'Color' : None}
            self.graphs['Render'].run_source(self, graph['source'], graph['parameters'], IN, OUT)
            result = OUT['Color']

        #COMPOSITE DEPTH
        composite_depth = None
        if is_final_render:
            composite_depth = self.composite_depth.render(self, self.common_buffer, self.t_opaque_depth)
        
        return {
            'COLOR' : result,
            'DEPTH' : composite_depth,
        }


PIPELINE = NPR_Pipeline
