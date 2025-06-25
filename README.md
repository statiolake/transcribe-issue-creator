# Transcribe Issue Creator

Morning meeting transcription tool that automatically creates meeting minutes and generates GitHub Issues.

## Features

- 🎤 **Voice Transcription**: Real-time speech recognition using Amazon Transcribe
- 📝 **Automatic Minutes**: AI-powered meeting minutes generation using Claude
- 📋 **Task Extraction**: Automatic task extraction from conversations for Issue creation
- ✏️ **Issue Editing**: Edit Issues in your editor before creation
- 👥 **Assignment**: Auto-detect or manually specify assignees
- 📊 **Project Integration**: Automatic addition to GitHub projects
- ⚙️ **Custom Instructions**: Customize AI behavior with `.custom-instructions` file

## Prerequisites

- Python 3.10 or higher  
- [GitHub CLI](https://cli.github.com/) installed and authenticated
- AWS account with Bedrock and Amazon Transcribe access
- `pyaudio` for voice input (optional)

## Installation

```bash
# Clone the project
git clone <repository-url>
cd transcribe-issue-creator

# Install dependencies
uv sync

# For voice input (optional)
uv add pyaudio
```

## Usage

### Basic Usage

```bash
# Microphone input
python main.py --repo owner/repository

# Text file input
cat meeting_notes.txt | python main.py --repo owner/repository

# Direct stdin input
echo "Meeting content..." | python main.py --repo owner/repository
```

### Voice Input Controls

1. Run the program to start voice input
2. Spoken content is transcribed in real-time
3. Press `Ctrl+D` to stop recording

### Issue Editing

Extracted tasks automatically open in your editor (default: nvim):

```markdown
# [Today] Complete API testing @statiolake

## Background
- About Tanaka-san's API implementation

## Assignee
- statiolake

## Tasks
- Complete testing for API modifications

---

# [Tomorrow] Review new feature design

## Background
- About new feature design

## Tasks
- Review design document
```

#### Editor Usage

- **Delete Issues**: Remove entire Issue blocks you don't need
- **Assign Users**: Add `@username` to title end (e.g., `@statiolake`)
- **Edit Content**: Freely modify titles and content
- **Separators**: Issues are separated by `---`

## Custom Instructions

Create a `.custom-instructions` file to customize AI behavior:

```
# Example .custom-instructions
- Team members: @alice (Frontend), @bob (Backend), @charlie (Infrastructure)
- Project name: "Sprint 2024-Q1"
- Deadline format: Add "tentatively" for internal tasks
- Always add priority labels when creating Issues
```

This content is automatically added to AI prompts for better Issue generation.

## Environment Variables

```bash
# Editor specification (default: nvim)
export EDITOR=vim

# AWS configuration
export AWS_DEFAULT_REGION=ap-northeast-1
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

## Output Examples

### Meeting Minutes (for Slack)

```
• Member A's progress is going well, with API implementation 80% complete.
• Discussed new feature X design direction and agreed on microservices approach.
• Performance issues occurred, requiring database query optimization.
```

### GitHub Issues

Created Issues automatically include:

- **Title**: Clear title with deadline
- **Body**: Structured content (Background, Assignee, Tasks)
- **Assignment**: Specified assignees
- **Project**: Automatic addition to specified projects

## Troubleshooting

### When pyaudio is unavailable

```bash
# Use text input instead
echo "Meeting content here" | python main.py --repo owner/repo
```

### GitHub CLI authentication error

```bash
# Authenticate GitHub CLI
gh auth login
```

### AWS authentication error

```bash
# Configure AWS CLI
aws configure
```

## Development

```bash
# Install development dependencies
uv sync --group dev

# Type checking
mypy main.py

# Linting
ruff check main.py
```

## License

This project is published under the [MIT License](LICENSE).