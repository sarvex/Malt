
class PipelineNode():

    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    @staticmethod
    def static_reflect(name, inputs, outputs):
        dictionary = {
            'name' : name,
            'type' : 'void',
            'file' : 'Render',
            'parameters' : []
        }
        for name, input in inputs.items():
            dictionary['parameters'].append({
                'name' : name,
                'type' : input,
                'size' : input.size,
                'io' : 'in',
            })
        for name, output in outputs.items():
            dictionary['parameters'].append({
                'name' : name,
                'type' : output,
                'size' : output.size,
                'io' : 'out',
            })
        return dictionary
    
    @classmethod
    def reflect(cls):
        return cls.static_reflect(cls.__name__, cls.reflect_inputs(), cls.reflect_outputs())

    @classmethod
    def reflect_inputs(cls):
        return {}

    @classmethod
    def reflect_outputs(cls):
        return {}
    
    def execute(self, parameters):
        pass
    

