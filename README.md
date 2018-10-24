# SBG CWL runner AKA CWL E. Coyote AKA Coyote
*This code is in the planning stage*

CWL E. Coyote (/Kwɪ'li E kaɪˈoʊti/), "Coyote" for short, is A CWL Runner for the 
Seven Bridges Genomics cloud platform. It supplies a `cwl-runner` style interface 
that runs tasks via the Seven Bridges API

*What's in a name?: [Wile E. Coyote](https://en.wikipedia.org/wiki/Wile_E._Coyote_and_the_Road_Runner)*

# Dependencies
- `sevenbridges-python` for API access to SBG Platform

# Run the cwl conformance tests

(Check the [language website][cwl-web] for details on setting up the conformance tests.
Use `./run_test.sh --help` to get more detailed usage information about the conformance test manager.)

[cwl-web]: https://github.com/common-workflow-language/cwl-v1.1#running-the-cwl-conformance-tests

To run conformance tests with the SBG platform and `sbg-cwl-runner` do:
```
cd cwl-language-directory
./run_test.sh -j100 RUNNER=sbg-cwl-runner EXTRA=--project="my-cwl-test-project"
```


## How it works
1. Wiley old CWL E. uploads the supplied CWL workflow (if needed) to the platform, first resolving any dependencies
2. It uploads the test files refered to in the job file
3. It creates a new task based on the job file and runs it
4. It waits until the task is done and retrieves the stderr log and the output object
