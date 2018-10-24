class: CommandLineTool
cwlVersion: v1.0
id: simple_commandline
baseCommand:
  - echo
inputs:
  - id: input
    type: File?
    inputBinding:
      position: 0
outputs:
  - id: output
    type: File?
    outputBinding:
      glob: '*.txt'
label: simple_commandline
requirements:
  - class: DockerRequirement
    dockerPull: alpine
stdout: output.txt
