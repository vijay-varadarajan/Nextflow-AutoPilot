from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search
from google.genai import types
import os, asyncio
from pathlib import Path
from google.adk.apps.app import App, EventsCompactionConfig
from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

retry_config=types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1, # Initial delay before first retry (in seconds)
    http_status_codes=[429, 500, 503, 504] # Retry on these HTTP errors
)

def create_path(path: str, content: str = None) -> str:
    """
    Creates a folder or file at the specified path. If content is provided, creates a file with that content.
    If content is None, creates a folder. Automatically creates parent directories as needed.
    
    Args:
        path: The path where the folder or file should be created
        content: Optional content for file creation. If None, creates a folder instead.
        
    Returns:
        A message indicating success or failure
    """
    try:
        path_obj = Path(path)
        if content is None:
            # Create folder
            path_obj.mkdir(parents=True, exist_ok=True)
            return f"Successfully created folder: {path}"
        else:
            # Create file with content
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(path_obj, 'w') as f:
                f.write(content)
            return f"Successfully created file: {path}"
    except Exception as e:
        return f"Error creating path: {str(e)}"

async def ask(runner, question: str):
    response = await runner.run_debug(question, verbose=True)
    return response


def create_todo_agent():
    """Creates and returns the TodoAgent for analyzing prompts and extracting metadata."""
    return Agent(
        name="TodoAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        description="Analyzes prompts and extracts project metadata for Nextflow workflow generation.",
        instruction="""You are a project analyzer for Nextflow workflows. Based on the prompt and input data files, extract and provide:

1. PROJECT_NAME: A suitable name for the Nextflow project (snake_case, descriptive)
2. PROCESS_NAME: The main process name for the Nextflow module (snake_case)
3. A brief ordered todo list (maximum 6 items) for implementing the workflow

Format your response EXACTLY as follows:
PROJECT_NAME: <project_name>
PROCESS_NAME: <process_name>

TODO LIST:
1. <todo item 1>
2. <todo item 2>
...

Be specific and extract these names from the context provided.""",
        output_key="project_metadata",
    )


def create_structure_agent():
    """Creates and returns the StructureAgent for creating project structure and main.nf."""
    return Agent(
        name="StructureAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        description="Creates Nextflow project structure with modules folder and main.nf.",
        instruction="""Based on the project metadata: {project_metadata}

Extract the PROJECT_NAME and PROCESS_NAME, then create:
1. Folder: PROJECT_NAME/modules/PROCESS_NAME/
2. File: PROJECT_NAME/modules/PROCESS_NAME/main.nf with:
   - process PROCESSNAME (uppercase)
   - container directive (use appropriate Docker image)
   - publishDir directive with mode parameter
   - input block
   - output block
   - script block

Use create_path tool. After creating, provide a summary of the main.nf content.""",
        tools=[create_path],
        output_key="main_nf_summary",
    )


def create_test_agent():
    """Creates and returns the TestAgent for creating test files."""
    return Agent(
        name="TestAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        description="Creates Nextflow test file for the module.",
        instruction="""Based on the project metadata: {project_metadata}
And the main.nf summary: {main_nf_summary}

Extract PROJECT_NAME and PROCESS_NAME, then create:
1. Folder: PROJECT_NAME/modules/PROCESS_NAME/tests/
2. File: PROJECT_NAME/modules/PROCESS_NAME/tests/main.nf.test with:
   - name field
   - script location: "../main.nf"
   - PROCESSNAME reference
   - Multiple test() blocks with setup {}, when {}, then {}

Use create_path tool. After creating, provide a summary of the test file.""",
        tools=[create_path],
        output_key="test_summary",
    )


def create_config_agent():
    """Creates and returns the ConfigAgent for creating nextflow.config."""
    return Agent(
        name="ConfigAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        description="Creates nextflow.config with profiles and default params.",
        instruction="""Based on the project metadata: {project_metadata}

Extract PROJECT_NAME and create:
File: PROJECT_NAME/nextflow.config with:
- profiles block (standard, docker, conda, etc.)
- params block with default parameters
- process configuration

Use create_path tool. 
IMPORTANT: After creating the file, you MUST provide a text summary of the config content. This summary is required for the next step. Do not stop after the tool call.""",
        tools=[create_path],
        output_key="config_summary",
    )


def create_workflow_agent():
    """Creates and returns the WorkflowAgent for creating the main workflow file."""
    return Agent(
        name="WorkflowAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
        description="Creates main workflow file.",
        instruction="""Based on all previous outputs:
Project metadata: {project_metadata}
Main.nf: {main_nf_summary}
Tests: {test_summary}
Config: {config_summary}

Extract PROJECT_NAME and PROCESS_NAME, then create:
File: PROJECT_NAME/main.nf with:
- include statement for the module
- workflow block that uses the process
- input channel creation
- process invocation

Use create_path tool. After creating, provide a complete summary of the entire project.""",
        tools=[create_path],
        output_key="workflow_summary",
    )


def main():
    # Read prompt.txt and input data files
    base_dir = Path(__file__).parent
    input_data_dir = base_dir.parent / 'input_data'
    input_files = os.listdir(input_data_dir)
    prompt_file = base_dir.parent / 'prompt.txt'
    with open(prompt_file, 'r') as pf:
        prompt_content = pf.read()
    
    # Create all agents using modular functions
    todo_agent = create_todo_agent()
    structure_agent = create_structure_agent()
    test_agent = create_test_agent()
    config_agent = create_config_agent()
    workflow_agent = create_workflow_agent()

    print("✅ All agents created.")

    # Create Sequential Agent Pipeline
    root_agent = SequentialAgent(
        name="NextflowGeneratorPipeline",
        sub_agents=[todo_agent, structure_agent, test_agent, config_agent, workflow_agent],
    )

    print("✅ Sequential Agent Pipeline created.")

    # Create App with session management and context compaction
    app = App(
        name="NextflowGeneratorApp",
        root_agent=root_agent,
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=5,
            overlap_size=2
        )
    )
    
    # Create Runner
    runner = InMemoryRunner(app=app)
    
    # Run the pipeline
    query = f"Generate Nextflow workflow based on:\n\nPrompt: {prompt_content}\n\nInput files: {input_files}"
    response = asyncio.run(ask(runner, query))
    
    print("\n" + "="*60)
    print("NEXTFLOW PROJECT GENERATION COMPLETE")
    print("="*60)
    print(response)
    print("\n✅ Nextflow project generation completed!")



if __name__ == "__main__":
    main()