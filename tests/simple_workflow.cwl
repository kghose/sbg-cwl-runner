class: Workflow
cwlVersion: v1.0
id: simple_workflow
label: simple_workflow
inputs:
  - id: input
    type: File?
outputs:
  - id: output
    outputSource:
      - simple_commandline_1/output
    type: File?
steps:
  - id: simple_commandline
    in:
      - id: input
        source: input
    out:
      - id: output
    run: ./simple_commandline.cwl
    label: simple_commandline
  - id: simple_commandline_1
    in:
      - id: input
        source: simple_commandline/output
    out:
      - id: output
    run: ./simple_commandline.cwl
    label: simple_commandline
requirements: []
