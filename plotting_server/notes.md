# notes

## from the spec meeting

todo add mulitple clients too
<https://fastapi.tiangolo.com/advanced/websockets/#handling-disconnections-and-multiple-clients>

snaking paths, pattern growing on the screen
with a pre-defined sum over rectangular region

so let's pick 3 region

to demonstrate 4 of those pltos at the same time

4th one is the total

bottlenecked on the stage speed - in step scanning
in fly scanning

from streamdatum, from stomp serialization

from run engine serialization of the scan spec

JSON - serialized version of the scan spec
to turn back

summary at the bottom?

button to run again?

also show the raw image

then a faster camera - stages already can fly scanning

probably 5 frames every half a second = 10Hz

the snake frames are 100 by 100 maps likely

10Hz will be the fastest we can see enough light

but thne 10 minute scan?

2 minutes as expected duration

after clicking a button

we see a pixel with intensity

we histogram them in terms of maximum intensity

the initial pixels need to get dimmer

we update live the reference value

davidia - davidia shoudl already do the histogramming

the sum - numpy array?

## pvs

dcam1 or dcam2

<https://gitlab.diamond.ac.uk/controls/containers/beamline/bl01c/-/blob/main/services/bl01c-di-dcam-01/config/ioc.yaml?ref_type=heads>

making aravis camera
and caget
<https://gitlab.diamond.ac.uk/controls/containers/beamline/bl01c/-/blob/main/services/bl01c-di-dcam-02/config/ioc.yaml?ref_type=heads>

pattern detector as argument to the count plan
that will generate stream resource for the data, for the sample
and it will provide something

reading library that uses h5py

we need to use a pattern generator detector

call a reading library with stream resource

### detector data

> > > f['entry']['instrument']['detector']['data'].shape
> > > (4, 1216, 1936)
> > > f['entry']['instrument']['detector']['data'][:2]
> > > array([[[1, 1, 1, ..., 1, 1, 1],

        [1, 1, 1, ..., 1, 1, 1],
        [1, 1, 1, ..., 1, 1, 1],
        ...,
        [1, 1, 1, ..., 1, 1, 1],
        [1, 1, 1, ..., 1, 1, 1],
        [1, 1, 1, ..., 1, 1, 1]],

       [[1, 1, 1, ..., 1, 1, 1],
        [1, 1, 1, ..., 1, 1, 1],
        [1, 1, 1, ..., 1, 1, 1],
        ...,
        [1, 1, 1, ..., 1, 1, 1],
        [1, 1, 1, ..., 1, 1, 1],
        [1, 1, 1, ..., 1, 1, 1]]], shape=(2, 1216, 1936), dtype=uint8)

> > >


## after 7 iterations

started with simple data streaming numpy arrays .

https://docs.h5py.org/en/latest/swmr.html

```python
import h5py

f = h5py.File("swmr.h5", "r", libver="latest", swmr=True)
dset = f["data"]
while True:
    dset.id.refresh()
    shape = dset.shape
    print(shape)
```


also used an outdated 'pyinotify' library to watch for changes in the target file.
Fortunately manta is an AravisDetector which supports swmr mode.
The image 

Then I tried the watchdog library, but looks like listening to bluesky events is a better solution for data update being at the right moment.

Then iteration three was running segments from a dataset


This would likely be a standalone server, kind of like h5grove but more involved. This on its own requires a separate package with python copier template.

The features desired there would be a synthesis of various ideas prototyped so far:
- davidia ws for the data so that it can be displayed
- fake data streaming as part of a scripts directory for testing, inside the src one? or to not export it to be honest
- simple listener too just to listen to events 
- using stateless setup with redis - like number 6
- provide random data too at selected endpoints
- provide simple listener - into websockets to stream just all events, and create a log. 
- provide plan-specific listener that works in collaboration with 'launch demo' endpoint

The only rejected feature would be the use of a watchdog / pyinotify UNLESS we want to preview all the hdf that happened in a directory, not just the new events. 

the UI could like a websockets - to - file tree and then next the hdf tree for a selected file then finally on the right the panel with davidia visualization

Let's for now do per-login data sessions with unique server-assigned IDs - anonymous sessions - however access only restricted to a directory defined in an environment variable.

Need to make tags at api routes to group them.

