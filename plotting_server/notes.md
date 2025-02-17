# notes

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
