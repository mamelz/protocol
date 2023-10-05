# protocol
Simple workflow management system for numeric quantum calculations.

The purpose of this package is to implement an easy to use, backend-agnostic tool that can automate the creation of runfiles for various calculations, minimizing the risk for bugs. The basic idea is the following:

Any quantum mechanical calculation (and any calculation in general, for that matter) is a sequence of function calls - I call them routines - that do certain things like calculate observables or propagate the state under some hamiltonian.
This sequence, called schedule, of routines can be defined by the user in a configuration file in YAML format that specifies all details of the calculation like propagation time, time resolution, which observables to calculate, when to calculate them, etc.
The configuration file references routines with the 'routine_name' keyword which contains the name. The routines are implemented by the user and made available with the PROTOCOL_FUNCTIONS_PATH environment variable. Together with a user-defined
propagation method, they form the building blocks for any calculation. The results of all routine evaluations are stored under user-defined keys and can be assessed after the sequence is completed.

In short, the user needs to:
- implement the backend-dependent functions relevant for the calculation in some module /path/to/functions.py
  - positional-only parameters, i.e. all function parameters preceding a '/', are used in the function definitions to pass the quantum state 'psi' and any external dependencies, for example the size of a spin system
  - if a routine needs the state, it must be passed as first positional argument, like:
    
        def foo(psi, external_args, /, *more_args, **kwargs):
            phi = my_backend.operation(psi, external_args, *more_args)
            return my_backend.measure(phi, **kwargs)
  - cachable functions should be cached for best performance
- set the environment variable: PROTOCOL_FUNCTIONS_PATH=/path/to/functions.py
- if time evolution is needed, provide a propagator: a callable with signature (psi, time, timestep) -> psi
- define a sequence of routines (a schedule) with a YAML file, here also the args and kwargs for each routine are specified
- perform the schedule.

An actual documentation will follow in due time...
