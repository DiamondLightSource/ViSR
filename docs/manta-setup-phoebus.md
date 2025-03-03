# ViSR hdf setup

<!-- todo add more notes from slack messages -->

## openng hte phoebus screens

## configuring the main screen

make trigger mode ON

acquire time for the shutter and acquire period

## configuring the hdf5 plugin screen

the plugin was broken for uknown reasons
need to enable callbacks (turn the plugin on)

file path logic on the right
bluesky does some of that stuff -

add tmp suffix and file tempalte

file mode capture / stream not sure - that is tin the camera itsel

number of images to see how many to save

port names tricky - it's a directed acyclic graphs
D2.CAM port name
every plugin has a port naem

ND array port in the ND ciruclar buffer section
and there open the capture too

wired directly to the camera - raw image, no preorpcessing

buesky sets acquir time and period and file name

it does enable the plugin too

we don't want it to rewrite the plugin chain, that's set up maually
it's checking if all the plugins in the chain are enabled though
