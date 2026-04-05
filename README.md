# DevGenie - AI-Powered Project Ideas & Resources

A Streamlit web application powered by Groq AI and DuckDuckGo Search that helps developers:
1. Generate innovative project ideas based on their tech stack and experience level
2. Discover and read top tech blogs in their field of interest

## Features

- **Smart Idea Generator**: Get 5 personalized project ideas with detailed descriptions, tech stacks, difficulty levels, and timelines
- **Blog Discovery**: Fetch relevant blog posts and articles from top tech platforms (Medium, Dev.to, GeeksforGeeks, etc.)
- **Interactive UI**: Clean, modern interface with clickable tech field and stack buttons
- **Real-time Processing**: Powered by Groq's Llama 3.3 70B model for fast AI responses
- **Experience-Based**: Tailors suggestions to your skill level (Beginner, Intermediate, Advanced)

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
- Copy `.env.example` to `.env`:
  ```bash
  cp .env.example .env
  ```
- Edit `.env` and add your Groq API key:
  ```
  GROQ_API_KEY=your_groq_api_key_here
  ```

### 3. Run the Application
```bash
streamlit run main.py
```

## Usage

1. **Step 1**: Enter or select a tech domain (e.g., "Machine Learning", "Web Development", "AI")
2. **Step 2**: Add your preferred technologies (e.g., "Python", "React", "Node.js") - click the quick-add buttons or type manually
3. **Step 3**: Select your experience level (Beginner, Intermediate, Advanced)
4. **Generate**: Click "✨ Generate Ideas + Blogs" to get personalized results
5. **Explore**: View project ideas and blog resources in separate tabs

## Tech Stack

- **Frontend**: Streamlit
- **AI Framework**: Groq API (Llama 3.3 70B)
- **Search Engine**: DuckDuckGo Search (no API key required)
- **Environment Management**: python-dotenv
- **Async Processing**: asyncio for parallel AI agent execution

## Requirements

- Python 3.8+
- Valid Groq API key (get one at [console.groq.com](https://console.groq.com))
- Internet connection for blog search functionality
