# Nextflow Workflow Generator Agent

### Problem Statement
Bioinformatics and data science pipelines often require complex orchestration using tools like Nextflow. Setting up a new Nextflow project involves a significant amount of boilerplate code: creating a standard directory structure, defining processes, writing configuration files, and setting up testing frameworks. This repetitive setup process is prone to errors and takes valuable time away from the actual logic implementation. Automating the generation of a robust, testable Nextflow project structure from a simple natural language description is a valuable tool for developers and scientists.

### Why agents?
Generating a complete software project is a multi-step process that requires "reasoning" at different levels of abstraction.
1.  **Context Understanding:** An agent needs to understand the high-level goal (e.g., "create a fastqc pipeline") to derive project names and requirements.
2.  **Sequential Dependencies:** The creation of test files depends on the logic defined in the main process. The configuration depends on the resources required by the process.
3.  **Tool Use:** Agents can actively interact with the file system to create folders and write files, rather than just outputting text.

A sequential chain of specialized agents allows us to break down this complex task into manageable units (Planning -> Structure -> Testing -> Configuration -> Assembly), ensuring high-quality output for each component.

### What you created
I built a **Sequential Agent Pipeline** using the **Google Agent Development Kit (ADK)**. The architecture consists of a linear chain of five specialized agents, orchestrated by a root `SequentialAgent`.

**The Agent Pipeline:**
1.  **TodoAgent:** Analyzes the user prompt and input files to extract project metadata (Project Name, Process Name) and creates an implementation plan.
2.  **StructureAgent:** Sets up the physical directory structure and generates the core module code (`main.nf`).
3.  **TestAgent:** Generates `nf-test` files to ensure the module works as expected.
4.  **ConfigAgent:** Creates the `nextflow.config` file with appropriate profiles (docker, conda, etc.).
5.  **WorkflowAgent:** Generates the root `main.nf` workflow file that connects the modules.

**Key Technical Features:**
*   **Google ADK `App` Architecture:** Wraps the agent pipeline in an `App` structure for robust state management.
*   **Session Management:** Uses `InMemoryRunner` and `InMemorySessionService` to maintain context across the agent chain.
*   **Context Compaction:** Implements `EventsCompactionConfig` to optimize the context window by summarizing past events, allowing for longer, more complex generation tasks without hitting token limits.
*   **Custom Tools:** A `create_path` tool allows agents to directly manipulate the file system.

### Demo

**1. Run the Generator**
Execute the main script from the project root:

```bash
python nextflow_generator/main.py
```

**2. Execution Flow**
The **Sequential Agent Pipeline** activates, passing context from one agent to the next:

*   **Step 1: TodoAgent** analyzes `prompt.txt` (e.g., "Create a FASTQC pipeline").
    *   *Output:* Identifies `Project Name: fastqc_pipeline` and creates a todo list.
*   **Step 2: StructureAgent** builds the module architecture.
    *   *Action:* Creates directory `fastqc_pipeline/modules/fastqc/`.
    *   *Action:* Writes `main.nf` with the Nextflow process definition.
*   **Step 3: TestAgent** adds reliability.
    *   *Action:* Generates `main.nf.test` using the `nf-test` framework to validate the module.
*   **Step 4: ConfigAgent** configures the environment.
    *   *Action:* Writes `nextflow.config` with Docker/Singularity profiles and default parameters.
*   **Step 5: WorkflowAgent** assembles the pipeline.
    *   *Action:* Creates the root `main.nf` workflow that imports and runs the module.

**3. Final Output**
The agent automatically generates a production-ready folder structure:

```text
fastqc_pipeline/
├── main.nf                 # Entry point workflow
├── nextflow.config         # Configuration profiles
└── modules/
    └── fastqc/
        ├── main.nf         # Module logic
        └── tests/
            └── main.nf.test # Unit tests
```

### The Build
This project was built using:
*   **Python 3.13**
*   **Google Agent Development Kit (ADK):** For defining agents, tools, and the runner architecture.
*   **Google GenAI SDK:** Accessing the **Gemini 2.5 Flash Lite** model.
*   **VS Code:** Development environment.

The core logic is encapsulated in `nextflow_generator/main.py`, which defines the agent factories and the sequential pipeline.

### If I had more time, this is what I'd do
*   **Agent Evaluation & Loops:** Implement a feedback loop where the agent runs the generated code using `nextflow run` or `nf-test`, evaluates the output, and self-corrects errors (Loop Agents).
*   **Observability:** Add comprehensive **Logging and Tracing** to visualize the decision-making process of the sequential chain and identify bottlenecks.
*   **A2A Protocol:** Enable communication with other specialized agents (e.g., a cloud infrastructure agent) using the Agent-to-Agent protocol.
*   **Deployment:** Deploy the agent as a scalable service rather than a local script.
