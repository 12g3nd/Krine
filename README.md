# Krine

Krine is a thought experiment about what an anonymous social platform could look like. It aims to empower users to share thoughts freely while leveraging advanced local AI for content safety and organization.

## Features

*   **Anonymous Posting**: No account registration. Ever. 
*   **Instant Intelligence**: Integrated AI helps maintain a healthy community by:
    *   Analyzes content for safety (filtering harmful content).
    *   Generates emotional/topical tags for every post.
*   **Community Interaction**:
    *   **Reactions**: Session-based "Like" system.
    *   **Comments**: Engage in anonymous discussions.
*   **Smart Discovery**: Sort posts by **Newest**, **Popular**, or **Most Commented**. Filter content by time (Day, Week, Month, Year) or type (Confession, Thought, etc.). 

## Tech Stack

*   **Backend**: Django 6.0
*   **Frontend**: HTML5, Vanilla CSS, JavaScript
*   **AI/ML**: PyTorch, Transformers (Hugging Face)
*   **Database**: SQLite (Default) / PostgreSQL-ready

## AI Setup

The project uses the `deepseek-ai/DeepSeek-V3.2` model via the `transformers` library.
*   **Note**: The first time you run the server or create a post, the model will be downloaded. This requires a stable internet connection and sufficient RAM/VRAM.
*   **Configuration**: Check `core/ai_service.py` to adjust model settings or implementation details.

## License

This project is open source.
