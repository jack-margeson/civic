# CIVIC

Central Intelligence Virtualization Instruction Cluster

## Team Information

**Jack Margeson**

MEng Computer Science Student (grad. 2025)

- e: [margesji@mail.uc.edu](mailto:margesji@mail.uc.edu)
- l: [linkedin.com/in/jack-margeson/](https://www.linkedin.com/in/jack-margeson/)
- w: [marg.es/on](https://marg.es/on)

**Dr. William Hawkins III**

Asst Professor, Project Advisor

- e: [hawkinwh@ucmail.uc.edu](mailto:hawkinwh@ucmail.uc.edu)
- w: [researchdirectory.uc.edu/p/hawkinwh](https://researchdirectory.uc.edu/p/hawkinwh)

## Problem Statement

There is no user-friendly distributed computing framework that incorporates virtualization for client machines.

### Issues identified in existing solutions

- BOINC
  - Key problem: every instructional program must be–
    1. written in C/C++
    2. _be compiled for each targeted architecture_
    3. have custom made assimilators/validators
  - Several features outdated or not well documented
  - Perl front end, registration tied to a forum, unneeded
  - Admin web portal is nice, but forced to use command line for most actions
  - Testing programs is a nightmare (see: manually staging input files for download)

### Proposed flow

- First, central server sends out virtualization instructions instead of programs and files to client machines
  - Docker, Kubernetes, containerd?
- Client machine configures the virtualization size based on how many resources it's willing to allocate to the project, then spins up an instance
- Central server communicates directly with virtualization through REST calls
- Executable (note, of any type) already packaged with the virtualization instructions
- Central server sends work units to virtualization(s), receives back results of execution
- Stores result in database for future project analysis
  - Look into highest throughput databasing software... which flavour SQL?

### Benefits

- Architecture independent
- More possibilities for researchers
  - No longer have to write your code in just C/C++
  - No requirement to include framework specific headers in code
  - Utilize existing code with no to minimal changes

## Project Outline

### Abstract

CIVIC (Central Intelligence Virtualization Instruction Cluster) provides distributed computing services by leveraging virtualization technologies to create a user-friendly framework for both researchers and participants. The overall goal of this project aims to address the limitations of current frameworks and opens new possibilities for research and development. Unlike existing solutions that require specific programming languages or hardware architectures, CIVIC provides a flexible, architecture-independent platform. This is achieved through the creation of models, a set of instructions that can be used by client machines to create virtualizations called citizens, i.e. virtual containers capable of receiving fractions of input data called duties and executing code to generate output. Researchers can utilize their existing code with minimal changes, while participants can easily contribute computational resources. The CIVIC Server manages model distribution, communication with citizens, and processing incoming duty results--ensuring efficient and scalable distributed computing by minimizing required human interaction.

### Terminology

- CIVIC Server: the central intelligence of the computing cluster. Responsible for connecting to client machines, sending instructions, serving input content, storing responses, and more.
- Duty/duties: a unit of work, i.e. a portion of input data given by the CIVIC Server to execute a program on (for example, calculating if there are any prime numbers between two bounds)
- Model: virtualization instructions generated server-side by the researcher. Models contain information that tell client machines running CIVIC how to build the virtual environment where duties will be performed.
- Citizen: a virtualized machine built based on a given model, responsible for connecting to the CIVIC Server and executing programs upon receiving a duty.

### CIVIC CLI

- Command line application, written in Python
  - Available as a works-out-of-the-box Docker image
- Two main use cases: developer/researcher and participant
  - As a developer/researcher:
    - Initial server setup
      - Partitioning disk space for database
      - Initializing networking for communication through REST API
    - Model creation
      - Define how citizens created from this model should run your executable(s), input and output, set validation thresholds, etc.
    - Input data segmentation
      - Configure input dataset(s) into smaller, manageable chunks
  - As a participant:
    - Connect to a server
    - Download all available models hosted for the project, choose one to contribute to
    - Configure resource allocation for virtualizations
    - Create citizens in order to process duties received from the server

## Design diagram

![Design diagram](project_planning\civic.drawio.png)
