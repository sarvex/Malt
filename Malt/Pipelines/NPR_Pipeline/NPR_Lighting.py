from Malt.GL.GL import *
from Malt.GL.Shader import UBO
from Malt.GL.Texture import TextureArray, CubeMapArray
from Malt.GL.RenderTarget import ArrayLayerTarget, RenderTarget

from Malt.Render import Lighting

class NPR_LightsGroupsBuffer():

    def __init__(self):
        class C_NPR_LightGroupsBuffer(ctypes.Structure):
            _fields_ = [
                ('light_group_index', ctypes.c_int*Lighting.MAX_LIGHTS),
            ]
        self.data = C_NPR_LightGroupsBuffer()
        self.UBO = UBO()
    
    def load(self, scene):
        for i, light in enumerate(scene.lights):
            self.data.light_group_index[i] = light.parameters['Light Group']

        self.UBO.load_data(self.data)

        for material in scene.batches.keys():
            for shader in material.shader.values():
                if 'MATERIAL_LIGHT_GROUPS' in shader.uniforms.keys():
                    shader.uniforms['MATERIAL_LIGHT_GROUPS'].set_value(material.parameters['Light Groups.Light'])

    def shader_callback(self, shader):
        if 'LIGHT_GROUPS' in shader.uniform_blocks:
            self.UBO.bind(shader.uniform_blocks['LIGHT_GROUPS'])    


class NPR_ShadowMaps(Lighting.ShadowMaps):

    def __init__(self):
        super().__init__()
        self.spot_id_t = None
        self.sun_id_t = None
        self.point_id_t = None
    
    def setup(self, create_fbos=True):
        super().setup(False)
        self.spot_id_t = TextureArray((self.spot_resolution, self.spot_resolution), self.max_spots, 
            GL_R16UI, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.sun_id_t = TextureArray((self.sun_resolution, self.sun_resolution), self.max_suns, 
            GL_R16UI, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.point_id_t = CubeMapArray((self.point_resolution, self.point_resolution), self.max_points, 
            GL_R16UI, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)

        if create_fbos:
            self.spot_fbos = []
            self.spot_fbos.extend(
                RenderTarget(
                    [ArrayLayerTarget(self.spot_id_t, i)],
                    ArrayLayerTarget(self.spot_depth_t, i),
                )
                for i in range(self.spot_depth_t.length)
            )
            self.sun_fbos = []
            self.sun_fbos.extend(
                RenderTarget(
                    [ArrayLayerTarget(self.sun_id_t, i)],
                    ArrayLayerTarget(self.sun_depth_t, i),
                )
                for i in range(self.sun_depth_t.length)
            )
            self.point_fbos = []
            self.point_fbos.extend(
                RenderTarget(
                    [ArrayLayerTarget(self.point_id_t, i)],
                    ArrayLayerTarget(self.point_depth_t, i),
                )
                for i in range(self.point_depth_t.length * 6)
            )
    
    def clear(self, spot_count, sun_count, point_count):
        for i in range(spot_count):
            self.spot_fbos[i].clear([0], depth=1)
        for i in range(sun_count):
            self.sun_fbos[i].clear([0], depth=1)
        for i in range(point_count*6):
            self.point_fbos[i].clear([0], depth=1)
    
    def shader_callback(self, shader):
        super().shader_callback(shader)
        shader.textures['SHADOWMAPS_ID_SPOT'] = self.spot_id_t
        shader.textures['SHADOWMAPS_ID_SUN'] = self.sun_id_t
        shader.textures['SHADOWMAPS_ID_POINT'] = self.point_id_t

class NPR_TransparentShadowMaps(NPR_ShadowMaps):

    def __init__(self):
        super().__init__()
        self.spot_color_t = None
        self.sun_color_t = None
        self.point_color_t = None
    
    def setup(self, create_fbos=True):
        super().setup(False)
        self.spot_color_t = TextureArray((self.spot_resolution, self.spot_resolution), self.max_spots, GL_RGB8)
        self.sun_color_t = TextureArray((self.sun_resolution, self.sun_resolution), self.max_suns, GL_RGB8)
        self.point_color_t = CubeMapArray((self.point_resolution, self.point_resolution), self.max_points, GL_RGB8)
        
        if create_fbos:
            self.spot_fbos = []
            for i in range(self.spot_depth_t.length):
                targets = [ArrayLayerTarget(self.spot_id_t, i), ArrayLayerTarget(self.spot_color_t, i)]
                self.spot_fbos.append(RenderTarget(targets, ArrayLayerTarget(self.spot_depth_t, i)))

            self.sun_fbos = []
            for i in range(self.sun_depth_t.length):
                targets = [ArrayLayerTarget(self.sun_id_t, i), ArrayLayerTarget(self.sun_color_t, i)]
                self.sun_fbos.append(RenderTarget(targets, ArrayLayerTarget(self.sun_depth_t, i)))
            
            self.point_fbos = []
            for i in range(self.point_depth_t.length*6):
                targets = [ArrayLayerTarget(self.point_id_t, i), ArrayLayerTarget(self.point_color_t, i)]
                self.point_fbos.append(RenderTarget(targets, ArrayLayerTarget(self.point_depth_t, i)))
    
    def clear(self, spot_count, sun_count, point_count):
        for i in range(spot_count):
            self.spot_fbos[i].clear([0, (0,0,0,0)], depth=1)
        for i in range(sun_count):
            self.sun_fbos[i].clear([0, (0,0,0,0)], depth=1)
        for i in range(point_count*6):
            self.point_fbos[i].clear([0, (0,0,0,0)], depth=1)

    def shader_callback(self, shader):
        shader.textures['TRANSPARENT_SHADOWMAPS_DEPTH_SPOT'] = self.spot_depth_t
        shader.textures['TRANSPARENT_SHADOWMAPS_DEPTH_SUN'] = self.sun_depth_t
        shader.textures['TRANSPARENT_SHADOWMAPS_DEPTH_POINT'] = self.point_depth_t
        shader.textures['TRANSPARENT_SHADOWMAPS_ID_SPOT'] = self.spot_id_t
        shader.textures['TRANSPARENT_SHADOWMAPS_ID_SUN'] = self.sun_id_t
        shader.textures['TRANSPARENT_SHADOWMAPS_ID_POINT'] = self.point_id_t
        shader.textures['TRANSPARENT_SHADOWMAPS_COLOR_SPOT'] = self.spot_color_t
        shader.textures['TRANSPARENT_SHADOWMAPS_COLOR_SUN'] = self.sun_color_t
        shader.textures['TRANSPARENT_SHADOWMAPS_COLOR_POINT'] = self.point_color_t
