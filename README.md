## pyPhotometry

The code is forked from https://github.com/pyPhotometry/code by T. Akam; also refer to the following paper: https://www.nature.com/articles/s41598-019-39724-y.

The pyBoard firmware was originally modified by Andrey Formozov and 
Alexander Dieter to adapt to the CoolLED (see first commits), then most modifications were made by myself.

The code is used on a regular basis in the Wiegert lab: https://simon-wiegert.weebly.com/.

Main modifications include:
- The creation of a new acquisition modes with parallel recordings (through time division) of green and red indicators (with isosbestic) in the same or different sites (i.e., through different fibre optic cannula).
- Compatibility with CoolLED light source.
- A checkbox to enable/disable ambient light correction in order to facilitate debugging and comparison of hardware.
- Display a "NOT RECORDING" warning message on the plots to avoid forgetting to record data when running experiments.