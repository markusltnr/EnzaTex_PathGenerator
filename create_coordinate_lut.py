import h5py
from path_generator import pixel2world
import numpy as np
import yaml

with open("calibration_matrix.yaml", "r") as f:
        camera_dict = yaml.safe_load(f)

pixel_coord = np.zeros((2448,2048,2))
for i in range(2448):
    for j in range(2048):
        pixel_coord[i,j,0] = i
        pixel_coord[i,j,1] = j

world_coord = pixel2world(pixel_coord.reshape(2448*2048,2), camera_dict).reshape((2448,2048,2))
with h5py.File("coordinate_lut.hdf5", 'w') as f:
    dset = f.create_dataset("LUT", data=world_coord)
