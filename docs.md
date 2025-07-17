Skip to main content
Block Logo
Quickstart
Docs
Tutorials
MCPs
Blog
Resources
Discord
GitHub

Quickstart
Getting Started

Install Goose
Configure LLM Provider
Using Extensions
Guides

Tutorials

MCP Servers

Architecture Overview

Experimental

Troubleshooting
Getting StartedConfigure LLM Provider
Supported LLM Providers
Goose is compatible with a wide range of LLM providers, allowing you to choose and integrate your preferred model.

Model Selection
Goose relies heavily on tool calling capabilities and currently works best with Anthropic's Claude 3.5 Sonnet and OpenAI's GPT-4o (2024-11-20) model. Berkeley Function-Calling Leaderboard can be a good guide for selecting models.

Available Providers
Provider	Description	Parameters
Amazon Bedrock	Offers a variety of foundation models, including Claude, Jurassic-2, and others. AWS environment variables must be set in advance, not configured through goose configure	AWS_PROFILE, or AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, ...
Amazon SageMaker TGI	Run Text Generation Inference models through Amazon SageMaker endpoints. AWS credentials must be configured in advance.	SAGEMAKER_ENDPOINT_NAME, AWS_REGION (optional), AWS_PROFILE (optional)
Anthropic	Offers Claude, an advanced AI model for natural language tasks.	ANTHROPIC_API_KEY, ANTHROPIC_HOST (optional)
Azure OpenAI	Access Azure-hosted OpenAI models, including GPT-4 and GPT-3.5. Supports both API key and Azure credential chain authentication.	AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_KEY (optional)
Databricks	Unified data analytics and AI platform for building and deploying models.	DATABRICKS_HOST, DATABRICKS_TOKEN
Gemini	Advanced LLMs by Google with multimodal capabilities (text, images).	GOOGLE_API_KEY
GCP Vertex AI	Google Cloud's Vertex AI platform, supporting Gemini and Claude models. Credentials must be configured in advance.	GCP_PROJECT_ID, GCP_LOCATION and optional GCP_MAX_RETRIES (6), GCP_INITIAL_RETRY_INTERVAL_MS (5000), GCP_BACKOFF_MULTIPLIER (2.0), GCP_MAX_RETRY_INTERVAL_MS (320_000).
Groq	High-performance inference hardware and tools for LLMs.	GROQ_API_KEY
Ollama	Local model runner supporting Qwen, Llama, DeepSeek, and other open-source models. Because this provider runs locally, you must first download and run a model.	OLLAMA_HOST
Ramalama	Local model using native OCI container runtimes, CNCF tools, and supporting models as OCI artifacts. Ramalama API an compatible alternative to Ollama and can be used with the Goose Ollama provider. Supports Qwen, Llama, DeepSeek, and other open-source models. Because this provider runs locally, you must first download and run a model.	OLLAMA_HOST
OpenAI	Provides gpt-4o, o1, and other advanced language models. Also supports OpenAI-compatible endpoints (e.g., self-hosted LLaMA, vLLM, KServe). o1-mini and o1-preview are not supported because Goose uses tool calling.	OPENAI_API_KEY, OPENAI_HOST (optional), OPENAI_ORGANIZATION (optional), OPENAI_PROJECT (optional), OPENAI_CUSTOM_HEADERS (optional)
OpenRouter	API gateway for unified access to various models with features like rate-limiting management.	OPENROUTER_API_KEY
Snowflake	Access the latest models using Snowflake Cortex services, including Claude models. Requires a Snowflake account and programmatic access token (PAT).	SNOWFLAKE_HOST, SNOWFLAKE_TOKEN
Venice AI	Provides access to open source models like Llama, Mistral, and Qwen while prioritizing user privacy. Requires an account and an API key.	VENICE_API_KEY, VENICE_HOST (optional), VENICE_BASE_PATH (optional), VENICE_MODELS_PATH (optional)
xAI	Access to xAI's Grok models including grok-3, grok-3-mini, and grok-3-fast with 131,072 token context window.	XAI_API_KEY, XAI_HOST (optional)
CLI Providers
Goose also supports special "pass-through" providers that work with existing CLI tools, allowing you to use your subscriptions instead of paying per token:

Provider	Description	Requirements
Claude Code (claude-code)	Uses Anthropic's Claude CLI tool with your Claude Code subscription. Provides access to Claude with 200K context limit.	Claude CLI installed and authenticated, active Claude Code subscription
Gemini CLI (gemini-cli)	Uses Google's Gemini CLI tool with your Google AI subscription. Provides access to Gemini with 1M context limit.	Gemini CLI installed and authenticated
CLI Providers
CLI providers are cost-effective alternatives that use your existing subscriptions. They work differently from API providers as they execute CLI commands and integrate with the tools' native capabilities. See the CLI Providers guide for detailed setup instructions.

Configure Provider
To configure your chosen provider or see available options, run goose configure in the CLI or visit the Settings page in the Goose Desktop.

Goose Desktop
Goose CLI
To update your LLM provider and API key:

Click the gear on the Goose Desktop toolbar
Click Advanced Settings
Under Models, click Configure provider
Click Configure on the LLM provider to update
Add additional configurations (API key, host, etc) then press submit
To change provider model

Click the gear on the Goose Desktop toolbar
Click Advanced Settings
Under Models, click Switch models
Select a Provider from drop down menu
Select a model from drop down menu
Press Select Model
You can explore more models by selecting a provider name under Browse by Provider. A link will appear, directing you to the provider's website. Once you've found the model you want, return to step 6 and paste the model name.

Using Custom OpenAI Endpoints
Goose supports using custom OpenAI-compatible endpoints, which is particularly useful for:

Self-hosted LLMs (e.g., LLaMA, Mistral) using vLLM or KServe
Private OpenAI-compatible API servers
Enterprise deployments requiring data governance and security compliance
OpenAI API proxies or gateways
Configuration Parameters
Parameter	Required	Description
OPENAI_API_KEY	Yes	Authentication key for the API
OPENAI_HOST	No	Custom endpoint URL (defaults to api.openai.com)
OPENAI_ORGANIZATION	No	Organization ID for usage tracking and governance
OPENAI_PROJECT	No	Project identifier for resource management
OPENAI_CUSTOM_HEADERS	No	Additional headers to include in the request. Can be set via environment variable, configuration file, or CLI, in the format HEADER_A=VALUE_A,HEADER_B=VALUE_B.
Example Configurations
vLLM Self-Hosted
KServe Deployment
Enterprise OpenAI
Custom Headers
For OpenAI-compatible endpoints that require custom headers:

OPENAI_API_KEY=your-api-key
OPENAI_ORGANIZATION=org-id123
OPENAI_PROJECT=compliance-approved
OPENAI_CUSTOM_HEADERS="X-Header-A=abc,X-Header-B=def"

Setup Instructions
Goose Desktop
Goose CLI
Click ... in the upper right corner
Click Advanced Settings
Next to Models, click the browse link
Click the configure link in the upper right corner
Press the + button next to OpenAI
Fill in your configuration details:
API Key (required)
Host URL (for custom endpoints)
Organization ID (for usage tracking)
Project (for resource management)
Press submit
Enterprise Deployment
For enterprise deployments, you can pre-configure these values using environment variables or configuration files to ensure consistent governance across your organization.

Using Goose for Free
Goose is a free and open source AI agent that you can start using right away, but not all supported LLM Providers provide a free tier.

Below, we outline a couple of free options and how to get started with them.

Limitations
These free options are a great way to get started with Goose and explore its capabilities. However, you may need to upgrade your LLM for better performance.

Google Gemini
Google Gemini provides a free tier. To start using the Gemini API with Goose, you need an API Key from Google AI studio.

To set up Google Gemini with Goose, follow these steps:

Goose Desktop
Goose CLI
To update your LLM provider and API key:

Click on the three dots in the top-right corner.
Select Provider Settings from the menu.
Choose Google Gemini as provider from the list.
Click Edit, enter your API key, and click Set as Active.
Local LLMs
Ollama and Ramalama are both options to provide local LLMs, each which requires a bit more set up before you can use one of them with Goose.

Ollama
Download Ollama.
Run any model supporting tool-calling:
Limited Support for models without tool calling
Goose extensively uses tool calling, so models without it (e.g. DeepSeek-r1) can only do chat completion. If using models without tool calling, all Goose extensions must be disabled. As an alternative, you can use a custom DeepSeek-r1 model we've made specifically for Goose.

Example:

ollama run qwen2.5

In a separate terminal window, configure with Goose:
goose configure

Choose to Configure Providers
┌   goose-configure 
│
◆  What would you like to configure?
│  ● Configure Providers (Change provider or update credentials)
│  ○ Toggle Extensions 
│  ○ Add Extension 
└  

Choose Ollama as the model provider
┌   goose-configure 
│
◇  What would you like to configure?
│  Configure Providers 
│
◆  Which model provider should we use?
│  ○ Anthropic 
│  ○ Databricks 
│  ○ Google Gemini 
│  ○ Groq 
│  ● Ollama (Local open source models)
│  ○ OpenAI 
│  ○ OpenRouter 
└  

Enter the host where your model is running
Endpoint
For Ollama, if you don't provide a host, we set it to localhost:11434. When constructing the URL, we prepend http:// if the scheme is not http or https. If you're running Ollama on a different server, you'll have to set OLLAMA_HOST=http://{host}:{port}.

┌   goose-configure 
│
◇  What would you like to configure?
│  Configure Providers 
│
◇  Which model provider should we use?
│  Ollama 
│
◆  Provider Ollama requires OLLAMA_HOST, please enter a value
│  http://localhost:11434
└

Enter the model you have running
┌   goose-configure 
│
◇  What would you like to configure?
│  Configure Providers 
│
◇  Which model provider should we use?
│  Ollama 
│
◇  Provider Ollama requires OLLAMA_HOST, please enter a value
│  http://localhost:11434
│
◇  Enter a model from that provider:
│  qwen2.5
│
◇  Welcome! You're all set to explore and utilize my capabilities. Let's get started on solving your problems together!
│
└  Configuration saved successfully

Ramalama
Download Ramalama.
Run any Ollama model supporting tool-calling or GGUF format HuggingFace Model :
Limited Support for models without tool calling
Goose extensively uses tool calling, so models without it (e.g. DeepSeek-r1) can only do chat completion. If using models without tool calling, all Goose extensions must be disabled. As an alternative, you can use a custom DeepSeek-r1 model we've made specifically for Goose.

Example:

# NOTE: the --runtime-args="--jinja" flag is required for Ramalama to work with the Goose Ollama provider.
ramalama serve --runtime-args="--jinja" ollama://qwen2.5

In a separate terminal window, configure with Goose:
goose configure

Choose to Configure Providers
┌   goose-configure
│
◆  What would you like to configure?
│  ● Configure Providers (Change provider or update credentials)
│  ○ Toggle Extensions
│  ○ Add Extension
└

Choose Ollama as the model provider since Ramalama is API compatible and can use the Goose Ollama provider
┌   goose-configure
│
◇  What would you like to configure?
│  Configure Providers
│
◆  Which model provider should we use?
│  ○ Anthropic
│  ○ Databricks
│  ○ Google Gemini
│  ○ Groq
│  ● Ollama (Local open source models)
│  ○ OpenAI
│  ○ OpenRouter
└

Enter the host where your model is running
Endpoint
For the Ollama provider, if you don't provide a host, we set it to localhost:11434. When constructing the URL, we preprend http:// if the scheme is not http or https. Since Ramalama's default port to serve on is 8080, we set OLLAMA_HOST=http://0.0.0.0:8080

┌   goose-configure
│
◇  What would you like to configure?
│  Configure Providers
│
◇  Which model provider should we use?
│  Ollama
│
◆  Provider Ollama requires OLLAMA_HOST, please enter a value
│  http://0.0.0.0:8080
└

Enter the model you have running
┌   goose-configure
│
◇  What would you like to configure?
│  Configure Providers
│
◇  Which model provider should we use?
│  Ollama
│
◇  Provider Ollama requires OLLAMA_HOST, please enter a value
│  http://0.0.0.0:8080
│
◇  Enter a model from that provider:
│  qwen2.5
│
◇  Welcome! You're all set to explore and utilize my capabilities. Let's get started on solving your problems together!
│
└  Configuration saved successfully

DeepSeek-R1
Ollama provides open source LLMs, such as DeepSeek-r1, that you can install and run locally. Note that the native DeepSeek-r1 model doesn't support tool calling, however, we have a custom model you can use with Goose.

warning
Note that this is a 70B model size and requires a powerful device to run smoothly.

Download and install Ollama from ollama.com.
In a terminal window, run the following command to install the custom DeepSeek-r1 model:
ollama run michaelneale/deepseek-r1-goose

Goose Desktop
Goose CLI
Click ... in the top-right corner.
Navigate to Advanced Settings -> Browse Models -> and select Ollama from the list.
Enter michaelneale/deepseek-r1-goose for the model name.
Azure OpenAI Credential Chain
Goose supports two authentication methods for Azure OpenAI:

API Key Authentication - Uses the AZURE_OPENAI_API_KEY for direct authentication
Azure Credential Chain - Uses Azure CLI credentials automatically without requiring an API key
To use the Azure Credential Chain:

Ensure you're logged in with az login
Have appropriate Azure role assignments for the Azure OpenAI service
Configure with goose configure and select Azure OpenAI, leaving the API key field empty
This method simplifies authentication and enhances security for enterprise environments.

If you have any questions or need help with a specific provider, feel free to reach out to us on Discord or on the Goose repo.

Previous
Install Goose
Next
Using Extensions
Available Providers
CLI Providers
Configure Provider
Using Custom OpenAI Endpoints
Configuration Parameters
Example Configurations
Setup Instructions
Using Goose for Free
Google Gemini
Local LLMs
DeepSeek-R1
Azure OpenAI Credential Chain
Quick Links
Install Goose
Extensions
Community
Spotlight
Discord
YouTube
LinkedIn
Twitter / X
BlueSky
Nostr
More
Blog
GitHub
Copyright © 2025 Block, Inc.


Environment Variables
Goose supports various environment variables that allow you to customize its behavior. This guide provides a comprehensive list of available environment variables grouped by their functionality.

Model Configuration
These variables control the language models and their behavior.

Basic Provider Configuration
These are the minimum required variables to get started with Goose.

Variable	Purpose	Values	Default
GOOSE_PROVIDER	Specifies the LLM provider to use	See available providers	None (must be configured)
GOOSE_MODEL	Specifies which model to use from the provider	Model name (e.g., "gpt-4", "claude-3.5-sonnet")	None (must be configured)
GOOSE_TEMPERATURE	Sets the temperature for model responses	Float between 0.0 and 1.0	Model-specific default
Examples

# Basic model configuration
export GOOSE_PROVIDER="anthropic"
export GOOSE_MODEL="claude-3.5-sonnet"
export GOOSE_TEMPERATURE=0.7

Advanced Provider Configuration
These variables are needed when using custom endpoints, enterprise deployments, or specific provider implementations.

Variable	Purpose	Values	Default
GOOSE_PROVIDER__TYPE	The specific type/implementation of the provider	See available providers	Derived from GOOSE_PROVIDER
GOOSE_PROVIDER__HOST	Custom API endpoint for the provider	URL (e.g., "https://api.openai.com")	Provider-specific default
GOOSE_PROVIDER__API_KEY	Authentication key for the provider	API key string	None
Examples

# Advanced provider configuration
export GOOSE_PROVIDER__TYPE="anthropic"
export GOOSE_PROVIDER__HOST="https://api.anthropic.com"
export GOOSE_PROVIDER__API_KEY="your-api-key-here"

Lead/Worker Model Configuration
These variables configure a lead/worker model pattern where a powerful lead model handles initial planning and complex reasoning, then switches to a faster/cheaper worker model for execution. The switch happens automatically based on your settings.

Variable	Purpose	Values	Default
GOOSE_LEAD_MODEL	Required to enable lead mode. Name of the lead model	Model name (e.g., "gpt-4o", "claude-3.5-sonnet")	None
GOOSE_LEAD_PROVIDER	Provider for the lead model	See available providers	Falls back to GOOSE_PROVIDER
GOOSE_LEAD_TURNS	Number of initial turns using the lead model before switching to the worker model	Integer	3
GOOSE_LEAD_FAILURE_THRESHOLD	Consecutive failures before fallback to the lead model	Integer	2
GOOSE_LEAD_FALLBACK_TURNS	Number of turns to use the lead model in fallback mode	Integer	2
A turn is one complete prompt-response interaction. Here's how it works with the default settings:

Use the lead model for the first 3 turns
Use the worker model starting on the 4th turn
Fallback to the lead model if the worker model struggles for 2 consecutive turns
Use the lead model for 2 turns and then switch back to the worker model
The lead model and worker model names are displayed at the start of the Goose CLI session. If you don't export a GOOSE_MODEL for your session, the worker model defaults to the GOOSE_MODEL in your configuration file.

Examples

# Basic lead/worker setup
export GOOSE_LEAD_MODEL="o4"

# Advanced lead/worker configuration
export GOOSE_LEAD_MODEL="claude4-opus"
export GOOSE_LEAD_PROVIDER="anthropic"
export GOOSE_LEAD_TURNS=5
export GOOSE_LEAD_FAILURE_THRESHOLD=3
export GOOSE_LEAD_FALLBACK_TURNS=2

Planning Mode Configuration
These variables control Goose's planning functionality.

Variable	Purpose	Values	Default
GOOSE_PLANNER_PROVIDER	Specifies which provider to use for planning mode	See available providers	Falls back to GOOSE_PROVIDER
GOOSE_PLANNER_MODEL	Specifies which model to use for planning mode	Model name (e.g., "gpt-4", "claude-3.5-sonnet")	Falls back to GOOSE_MODEL
Examples

# Planning mode with different model
export GOOSE_PLANNER_PROVIDER="openai"
export GOOSE_PLANNER_MODEL="gpt-4"

Session Management
These variables control how Goose manages conversation sessions and context.

Variable	Purpose	Values	Default
GOOSE_CONTEXT_STRATEGY	Controls how Goose handles context limit exceeded situations	"summarize", "truncate", "clear", "prompt"	"prompt" (interactive), "summarize" (headless)
GOOSE_MAX_TURNS	Maximum number of turns allowed without user input	Integer (e.g., 10, 50, 100)	1000
Examples

# Automatically summarize when context limit is reached
export GOOSE_CONTEXT_STRATEGY=summarize

# Always prompt user to choose (default for interactive mode)
export GOOSE_CONTEXT_STRATEGY=prompt

# Set a low limit for step-by-step control
export GOOSE_MAX_TURNS=5

# Set a moderate limit for controlled automation
export GOOSE_MAX_TURNS=25

# Set a reasonable limit for production
export GOOSE_MAX_TURNS=100

Context Limit Configuration
These variables allow you to override the default context window size (token limit) for your models. This is particularly useful when using LiteLLM proxies or custom models that don't match Goose's predefined model patterns.

Variable	Purpose	Values	Default
GOOSE_CONTEXT_LIMIT	Override context limit for the main model	Integer (number of tokens)	Model-specific default or 128,000
GOOSE_LEAD_CONTEXT_LIMIT	Override context limit for the lead model in lead/worker mode	Integer (number of tokens)	Falls back to GOOSE_CONTEXT_LIMIT or model default
GOOSE_WORKER_CONTEXT_LIMIT	Override context limit for the worker model in lead/worker mode	Integer (number of tokens)	Falls back to GOOSE_CONTEXT_LIMIT or model default
GOOSE_PLANNER_CONTEXT_LIMIT	Override context limit for the planner model	Integer (number of tokens)	Falls back to GOOSE_CONTEXT_LIMIT or model default
Examples

# Set context limit for main model (useful for LiteLLM proxies)
export GOOSE_CONTEXT_LIMIT=200000

# Set different context limits for lead/worker models
export GOOSE_LEAD_CONTEXT_LIMIT=500000   # Large context for planning
export GOOSE_WORKER_CONTEXT_LIMIT=128000 # Smaller context for execution

# Set context limit for planner
export GOOSE_PLANNER_CONTEXT_LIMIT=1000000

Tool Configuration
These variables control how Goose handles tool permissions and their execution.

Variable	Purpose	Values	Default
GOOSE_MODE	Controls how Goose handles tool execution	"auto", "approve", "chat", "smart_approve"	"smart_approve"
GOOSE_TOOLSHIM	Enables/disables tool call interpretation	"1", "true" (case insensitive) to enable	false
GOOSE_TOOLSHIM_OLLAMA_MODEL	Specifies the model for tool call interpretation	Model name (e.g. llama3.2, qwen2.5)	System default
GOOSE_CLI_MIN_PRIORITY	Controls verbosity of tool output	Float between 0.0 and 1.0	0.0
GOOSE_CLI_TOOL_PARAMS_TRUNCATION_MAX_LENGTH	Maximum length for tool parameter values before truncation in CLI output (not in debug mode)	Integer	40
GOOSE_CLI_SHOW_COST	Toggles display of model cost estimates in CLI output	"true", "1" (case insensitive) to enable	false
Examples

# Enable tool interpretation
export GOOSE_TOOLSHIM=true
export GOOSE_TOOLSHIM_OLLAMA_MODEL=llama3.2
export GOOSE_MODE="auto"
export GOOSE_CLI_MIN_PRIORITY=0.2  # Show only medium and high importance output
export GOOSE_CLI_TOOL_PARAMS_MAX_LENGTH=100  # Show up to 100 characters for tool parameters in CLI output

# Enable model cost display in CLI
export GOOSE_CLI_SHOW_COST=true

Enhanced Code Editing
These variables configure AI-powered code editing for the Developer extension's str_replace tool. All three variables must be set and non-empty for the feature to activate.

Variable	Purpose	Values	Default
GOOSE_EDITOR_API_KEY	API key for the code editing model	API key string	None
GOOSE_EDITOR_HOST	API endpoint for the code editing model	URL (e.g., "https://api.openai.com/v1")	None
GOOSE_EDITOR_MODEL	Model to use for code editing	Model name (e.g., "gpt-4o", "claude-3-5-sonnet")	None
Examples

This feature works with any OpenAI-compatible API endpoint, for example:

# OpenAI configuration
export GOOSE_EDITOR_API_KEY="sk-..."
export GOOSE_EDITOR_HOST="https://api.openai.com/v1"
export GOOSE_EDITOR_MODEL="gpt-4o"

# Anthropic configuration (via OpenAI-compatible proxy)
export GOOSE_EDITOR_API_KEY="sk-ant-..."
export GOOSE_EDITOR_HOST="https://api.anthropic.com/v1"
export GOOSE_EDITOR_MODEL="claude-3-5-sonnet-20241022"

# Local model configuration
export GOOSE_EDITOR_API_KEY="your-key"
export GOOSE_EDITOR_HOST="http://localhost:8000/v1"
export GOOSE_EDITOR_MODEL="your-model"

Tool Selection Strategy
These variables configure the tool selection strategy.

Variable	Purpose	Values	Default
GOOSE_ROUTER_TOOL_SELECTION_STRATEGY	The tool selection strategy to use	"default", "vector", "llm"	"default"
GOOSE_EMBEDDING_MODEL_PROVIDER	The provider to use for generating embeddings for the "vector" strategy	See available providers (must support embeddings)	"openai"
GOOSE_EMBEDDING_MODEL	The model to use for generating embeddings for the "vector" strategy	Model name (provider-specific)	"text-embedding-3-small"
Examples

# Use vector-based tool selection with custom settings
export GOOSE_ROUTER_TOOL_SELECTION_STRATEGY=vector
export GOOSE_EMBEDDING_MODEL_PROVIDER=ollama
export GOOSE_EMBEDDING_MODEL=nomic-embed-text

# Or use LLM-based selection
export GOOSE_ROUTER_TOOL_SELECTION_STRATEGY=llm

Embedding Provider Support

The default embedding provider is OpenAI. If using a different provider:

Ensure the provider supports embeddings
Specify an appropriate embedding model for that provider
Ensure the provider is properly configured with necessary credentials
Security Configuration
These variables control security related features.

Variable	Purpose	Values	Default
GOOSE_ALLOWLIST	Controls which extensions can be loaded	URL for allowed extensions list	Unset
GOOSE_DISABLE_KEYRING	Disables the system keyring for secret storage	Set to any value (e.g., "1", "true", "yes") to disable. The actual value doesn't matter, only whether the variable is set.	Unset (keyring enabled)
tip
When the keyring is disabled, secrets are stored here:

macOS/Linux: ~/.config/goose/secrets.yaml
Windows: %APPDATA%\Block\goose\config\secrets.yaml
Langfuse Integration
These variables configure the Langfuse integration for observability.

Variable	Purpose	Values	Default
LANGFUSE_PUBLIC_KEY	Public key for Langfuse integration	String	None
LANGFUSE_SECRET_KEY	Secret key for Langfuse integration	String	None
LANGFUSE_URL	Custom URL for Langfuse service	URL String	Default Langfuse URL
LANGFUSE_INIT_PROJECT_PUBLIC_KEY	Alternative public key for Langfuse	String	None
LANGFUSE_INIT_PROJECT_SECRET_KEY	Alternative secret key for Langfuse	String	None
Notes
Environment variables take precedence over configuration files.
For security-sensitive variables (like API keys), consider using the system keyring instead of environment variables.
Some variables may require restarting Goose to take effect.
When using the planning mode, if planner-specific variables are not set, Goose will fall back to the main model configuration.