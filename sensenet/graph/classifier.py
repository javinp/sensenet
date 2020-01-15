import sensenet.importers
tf = sensenet.importers.import_tensorflow()

from sensenet.constants import NUMERIC, CATEGORICAL, IMAGE_PATH
from sensenet.accessors import get_output_exposition
from sensenet.graph.preprocess import create_loaders, reorder_inputs
from sensenet.graph.image import image_preprocessor
from sensenet.graph.construct import make_layers
from sensenet.graph.layers.utils import make_tensor
from sensenet.graph.layers.tree import forest_preprocessor

def initialize_variables(model):
    xlen = len(model['preprocess'])
    return {'raw_X': tf.placeholder(tf.float32, (None, xlen))}

def create_preprocessor(model, input_variables):
    variables = {}

    locations, load_vars = create_loaders(model, input_variables)
    variables.update(load_vars)

    if model.get('image_network', None):
        img_net = model['image_network']
        n_images = sum(1 for vtype, _ in locations if vtype == IMAGE_PATH)
        img_vars = image_preprocessor(img_net, n_images)
        variables.update(img_vars)

    preprocessed = reorder_inputs(locations, variables)
    variables['preprocessed_X'] = preprocessed

    if model['trees']:
        embedded_X = forest_preprocessor(model, variables)
        variables['embedded_X'] = embedded_X

    return variables

def create_network(network, variables, output_exposition=None):
    outex = output_exposition or get_output_exposition(network)

    if network['trees']:
        Xin = variables['embedded_X']
    else:
        Xin = variables['preprocessed_X']

    _, outputs = make_layers(Xin, network['layers'], None)

    if outex['type'] == NUMERIC:
        mten = make_tensor(outex['mean'])
        stdten = make_tensor(outex['stdev'])

        return outputs * stdten + mten
    else:
        return outputs

def create_classifier(model):
    variables = initialize_variables(model)
    variables.update(create_preprocessor(model, variables))

    if 'networks' in model:
        outex = get_output_exposition(model)
        mod_preds = []

        for network in model['networks']:
            preds = create_network(network, variables, output_exposition=outex)
            mod_preds.append(preds)

        summed = tf.add_n(mod_preds)
        netslen = make_tensor(len(mod_preds))

        variables['network_outputs'] = summed / netslen
    else:
        variables['network_outputs'] = create_network(model, variables)

    return variables
