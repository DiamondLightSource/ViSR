# https://docs.h5py.org/en/latest/swmr.html
import h5py

f = h5py.File("swmr.h5", "r", libver="latest", swmr=True)
dset = f["data"]
while True:
    dset.id.refresh()
    shape = dset.shape
    print(shape)
