# CWL E. Coyote (AKA Coyote)
*This code is in the planning stage*

CWL E. Coyote (/Kwɪ'li E kaɪˈoʊti/), "Kwɪ'li" for short, is A CWL Runner for the Seven Bridges Genomics cloud platform. Supplies a `cwl-runner` style interface that runs tasks via the Seven Bridges API

## How it works
1. CWL E. reads your credentials (token) and designated project directory from environment variables
2. It uploads the CWL workflow to the platform, first resolving any dependencies
  - If the App already exists in the project it creates a new version
3. It uploads the test files refered to in the job file
  - If the files already exist, they are renamed and the local ones are uploaded
4. It creates a new task based on the job file and runs it
5. It waits until the task is done and retrieves the stderr log and the output object
