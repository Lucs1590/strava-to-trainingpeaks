## 0.7.0 (2024-10-25)

### Feat

- refactor Dockerfile to use multi-stage build for improved efficiency and security

### Refactor

- update Dockerfile commands to use absolute path for docker executable
- improve code formatting and add comments for clarity
- include cx_Freeze and an executable for main.py

## 0.6.1 (2024-10-16)

### Refactor

- removing useless else
- add test for removing null columns in preprocessing function
- preprocessing function to remove null columns

## 0.6.0 (2024-09-27)

### Feat

- improving prompt

### Refactor

- use a conditional expression for constructing the URL

## 0.5.0 (2024-09-27)

### Feat

- removing duplicated methods
- improve error handling for getting the latest downloaded TCX file
- automatically detect and use the latest downloaded TCX file
- add tqdm to euclidian distance calcule
- update params
- allow null path
- change percentage range
- running euclidean distance to remove rows
- Add OpenAI language model for LLM analysis
- Improve LLM analysis prompt in perform_llm_analysis
- Add AI Assistant prompt for LLM analysis
- Add LLM analysis option to validate_tcx_file

### Fix

- model type

### Refactor

- handle FileNotFoundError
- improving error handling and file detection
- renaming df to dataframe
- Convert Time column to Hour:Minute:Second format
- improve ask_file_path function
- output type
- improving euclidian calc performance
- Preprocess trackpoints data in perform_llm_analysis

## 0.4.0 (2024-05-08)

### Feat

- get activity id based in url

## 0.3.0 (2024-04-11)

### BREAKING CHANGE

- initial version

## 0.2.0 (2024-04-11)

### Feat

- add encoding to open module

### Fix

- python version

### Refactor

- pylint advice
- change parser
- codefactor advice
- boolean return
- using path instead of name
- remove useless imports

## 0.1.0 (2024-04-11)

### Feat

- file location handling
- validate TCX file for Bike and Run sports
- add file indentation
- improve script
- remove hardcoded and comments
- swim config
- initial script

### Refactor

- logs language
- Improve TCX file export and formatting
