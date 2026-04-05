import streamlit as st
import asyncio
from groq import Groq
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time
from ddgs import DDGS


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ─────────────────────────────────────────────
# 🔧  Shared Groq Agent
# ─────────────────────────────────────────────
class GroqAgent:
    """Thin async wrapper around the Groq chat-completions endpoint."""

    def __init__(self, model: str, system_prompt: str):
        self.client        = Groq(api_key=GROQ_API_KEY)
        self.model         = model
        self.system_prompt = system_prompt

    async def run(self, user_message: str, max_tokens: int = 2048) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._call, user_message, max_tokens
        )

    def _call(self, user_message: str, max_tokens: int) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content


# ─────────────────────────────────────────────
# 🔍  DuckDuckGo Search Tool  (no API key needed)
# ─────────────────────────────────────────────
def _ddg_search(query: str, max_results: int = 4) -> list[dict]:
    """Single DDG query — returns list of {title, url, snippet}."""
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))
            return [
                {"title": r.get("title", ""),
                 "url":   r.get("href", "") or r.get("url", ""),
                 "snippet": r.get("body", "") or r.get("snippet", "")}
                for r in raw if r.get("href") or r.get("url")
            ]
    except Exception:
        return []


def _fetch_all_blogs(field: str, stacks: str) -> list[dict]:
    """
    Runs multiple targeted DDG queries sequentially in one thread
    (parallel threads get rate-limited by DDG).
    """
    topic = f"{field} {stacks}".strip()

    queries = [
        f"{topic} tutorial site:geeksforgeeks.org",
        f"{topic} tutorial site:medium.com",
        f"{topic} tutorial site:dev.to",
        f"{topic} complete guide site:freecodecamp.org",
        f"{topic} tutorial site:hashnode.com",
        f"{topic} tutorial site:towardsdatascience.com",
        f"{topic} beginner guide tutorial",
    ]

    seen, results = set(), []
    for q in queries:
        batch = _ddg_search(q, 3)
        for item in batch:
            if item["url"] and item["url"] not in seen:
                seen.add(item["url"])
                results.append(item)
        time.sleep(0.4)          # small pause to avoid DDG rate limits
        if len(results) >= 12:
            break

    return results[:12]


# ─────────────────────────────────────────────
# 🤖  Agent 1 – Project Idea Generator
# ─────────────────────────────────────────────
async def agent_generate_ideas(field: str, stacks: str, level: str) -> str:
    agent = GroqAgent(
        model="llama-3.3-70b-versatile",
        system_prompt="""
You are a senior software architect and mentor who creates detailed, actionable project ideas.

For every project idea output EXACTLY this markdown structure (repeat for all 5 ideas):

---

### 🚀 Project [N]: [Catchy Title]

**📝 Description**
[2–3 sentences — what it does, who it's for, and why it matters]

**🔄 Workflow**
1. [Step 1 — user/system action]
2. [Step 2]
3. [Step 3]
4. [Continue until complete end-to-end flow]

**🛠️ Tech Stack**
| Technology | Role in Project |
|------------|----------------|
| [Tech 1]   | [Purpose]       |
| [Tech 2]   | [Purpose]       |

**⭐ Key Features**
- [Feature 1]
- [Feature 2]
- [Feature 3]

**📊 Project Details**
- **Difficulty:** [Beginner / Intermediate / Advanced]
- **Estimated Time:** [X weeks / months]
- **What you'll learn:** [2–3 key skills gained]
- **Stretch Goal:** [One way to extend the project further]

---

Make ideas modern, portfolio-worthy, and perfectly matched to the user's level and tech stack.
        """,
    )
    prompt = (
        f"Tech Field: {field}\n"
        f"Preferred Tech Stack / Languages: {stacks or 'Open to suggestions'}\n"
        f"Experience Level: {level}\n\n"
        "Generate 5 project ideas that are creative, practical, and well-suited for this combination."
    )
    return await agent.run(prompt, max_tokens=3000)


# ─────────────────────────────────────────────
# 🤖  Agent 2 – Blog / Article Fetcher  (DuckDuckGo)
# ─────────────────────────────────────────────
async def agent_fetch_blogs(field: str, stacks: str) -> list[dict]:
    """Runs all blog searches in a single background thread to avoid DDG rate limits."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_all_blogs, field, stacks)


# ─────────────────────────────────────────────
# ⚡  Parallel Orchestrator
# ─────────────────────────────────────────────
async def run_all_agents(field: str, stacks: str, level: str):
    ideas, blogs = await asyncio.gather(
        agent_generate_ideas(field, stacks, level),
        agent_fetch_blogs(field, stacks),
    )
    return ideas, blogs


# ─────────────────────────────────────────────
# 🔀  Sync wrappers for ThreadPoolExecutor
# ─────────────────────────────────────────────
def _sync_ideas(field: str, stacks: str, level: str) -> str:
    """Run the async ideas agent from a plain thread."""
    return asyncio.run(agent_generate_ideas(field, stacks, level))


def _sync_blogs(field: str, stacks: str) -> list[dict]:
    """Blog fetch is already sync — direct call."""
    return _fetch_all_blogs(field, stacks)


# ═══════════════════════════════════════════════
#  STREAMLIT UI
# ═══════════════════════════════════════════════
st.set_page_config(
    page_title="DevGenie – Project Ideas & Resources",
    page_icon="🚀",
    layout="wide",
)

st.markdown("""
<style>
/* ── General ── */
[data-testid="stAppViewContainer"] { background: #0f1117; }
h1, h2, h3, h4, p, label, .stMarkdown { color: #e8eaf6 !important; }

/* ── Step Cards ── */
.step-card {
    background: #1a1d2e;
    border: 1px solid #2d3154;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
}
.step-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #7c83ff !important;
    text-transform: uppercase;
    margin-bottom: 0.25rem;
}
.step-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: #ffffff !important;
    margin-bottom: 0.6rem;
}
.step-subtitle {
    font-size: 0.85rem;
    color: #8b8fa8 !important;
    margin-bottom: 0.9rem;
}

/* ── Chip Buttons ── */
.stButton > button {
    background: #1e2235 !important;
    border: 1px solid #2d3154 !important;
    color: #c5c8e8 !important;
    border-radius: 999px !important;
    font-size: 0.78rem !important;
    padding: 0.25rem 0.6rem !important;
    transition: all 0.15s;
    height: auto !important;
    min-height: 0 !important;
}
.stButton > button:hover {
    background: #2a2f52 !important;
    border-color: #5c63c0 !important;
    color: #ffffff !important;
}

/* ── Generate Button ── */
[data-testid="baseButton-primary"] > button,
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #5c63c0, #7c43c8) !important;
    border: none !important;
    color: white !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    padding: 0.7rem 2rem !important;
    height: auto !important;
    letter-spacing: 0.03em;
}

/* ── Inputs ── */
.stTextInput > div > div > input {
    background: #1a1d2e !important;
    border: 1px solid #2d3154 !important;
    border-radius: 10px !important;
    color: #e8eaf6 !important;
    font-size: 0.95rem !important;
    padding: 0.6rem 0.9rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #5c63c0 !important;
    box-shadow: 0 0 0 2px rgba(92,99,192,0.25) !important;
}

/* ── Radio ── */
.stRadio > div { flex-direction: row; gap: 0.8rem; }
.stRadio label {
    background: #1a1d2e !important;
    border: 1px solid #2d3154 !important;
    border-radius: 10px !important;
    padding: 0.5rem 1.1rem !important;
    color: #c5c8e8 !important;
    font-size: 0.88rem !important;
    cursor: pointer;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 0.5rem; background: transparent; }
.stTabs [data-baseweb="tab"] {
    background: #1a1d2e !important;
    border-radius: 8px 8px 0 0 !important;
    border: 1px solid #2d3154 !important;
    color: #8b8fa8 !important;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #2a2f52 !important;
    color: #ffffff !important;
    border-bottom-color: transparent !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #1a1d2e !important;
    border: 1px solid #2d3154 !important;
    border-radius: 0 8px 8px 8px !important;
    padding: 1.5rem !important;
}

/* ── Blog Card ── */
.blog-card {
    background: #1e2235;
    border: 1px solid #2d3154;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
    transition: border-color 0.15s;
}
.blog-card:hover { border-color: #5c63c0; }
.blog-title { font-size: 0.97rem; font-weight: 600; color: #7c83ff !important; }
.blog-snippet { font-size: 0.82rem; color: #8b8fa8 !important; margin-top: 0.3rem; }
.blog-url { font-size: 0.75rem; color: #525780 !important; margin-top: 0.25rem; }

/* ── Video Card ── */
.video-card {
    background: #1e2235;
    border: 1px solid #2d3154;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 1rem;
}
.video-meta { padding: 0.7rem 0.9rem; }
.video-title { font-size: 0.88rem; font-weight: 600; color: #e8eaf6 !important; }
.video-channel { font-size: 0.76rem; color: #8b8fa8 !important; margin-top: 0.2rem; }

/* ── Summary Bar ── */
.summary-bar {
    background: #1a1d2e;
    border: 1px solid #2d3154;
    border-radius: 10px;
    padding: 0.7rem 1.2rem;
    display: flex;
    gap: 1.5rem;
    margin-bottom: 1.2rem;
    flex-wrap: wrap;
}
.summary-tag { font-size: 0.82rem; color: #c5c8e8 !important; }
.summary-tag span { color: #7c83ff !important; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────
st.markdown("# 🚀 DevGenie")
st.markdown("*AI-powered project ideas & curated blog resources — all in one place*")
st.markdown("---")


# ── Session State Init ──────────────────────────
defaults = {
    "field": "", "stacks": "", "level": "🌱 Beginner",
    "results": None, "generated": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ════════════════════════════════════════════════
#  STEP 1 — Tech Field
# ════════════════════════════════════════════════
st.markdown('<p class="step-label">Step 1 of 3</p>', unsafe_allow_html=True)
st.markdown('<p class="step-title">🎯 What tech domain are you exploring?</p>', unsafe_allow_html=True)
st.markdown('<p class="step-subtitle">Type below or pick a popular field to get started</p>', unsafe_allow_html=True)

typed_field = st.text_input(
    "Tech Field", placeholder="e.g. Machine Learning, Web Dev, Blockchain…",
    value=st.session_state.field, label_visibility="collapsed"
)
st.session_state.field = typed_field

popular_fields = [
    "Artificial Intelligence", "Machine Learning", "Web Development",
    "Blockchain", "Cloud Computing", "Cybersecurity", "DevOps",
    "Data Science", "Mobile Development", "IoT", "Game Development",
    "AR / VR", "Robotics", "FinTech", "HealthTech",
]
cols = st.columns(5)
for i, f in enumerate(popular_fields):
    with cols[i % 5]:
        if st.button(f, key=f"pf_{i}", use_container_width=True):
            st.session_state.field = f
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  STEP 2 — Tech Stack / Language
# ════════════════════════════════════════════════
st.markdown('<p class="step-label">Step 2 of 3</p>', unsafe_allow_html=True)
st.markdown('<p class="step-title">🛠️ Which technologies do you want to build with?</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="step-subtitle">Add the languages, frameworks, or tools you\'re learning or want to use — '
    'we\'ll tailor every idea and resource around your stack</p>',
    unsafe_allow_html=True,
)

typed_stacks = st.text_input(
    "Tech Stack", placeholder="e.g. Python, React, Node.js, TensorFlow, Docker…",
    value=st.session_state.stacks, label_visibility="collapsed"
)
st.session_state.stacks = typed_stacks

st.markdown("**⚡ Quick-add popular technologies:**")

popular_stacks = [
    "Python", "JavaScript", "TypeScript", "React", "Next.js",
    "Node.js", "FastAPI", "Django", "Flutter", "Swift",
    "Go", "Rust", "Docker", "Kubernetes", "PostgreSQL",
    "MongoDB", "Redis", "TensorFlow", "PyTorch", "LangChain",
]
cols2 = st.columns(5)
for i, s in enumerate(popular_stacks):
    with cols2[i % 5]:
        if st.button(s, key=f"ps_{i}", use_container_width=True):
            current = st.session_state.stacks
            if s not in current:
                new_val = f"{current}, {s}".lstrip(", ") if current else s
                st.session_state.stacks = new_val
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  STEP 3 — Experience Level
# ════════════════════════════════════════════════
LEVEL_MAP = {
    "🌱 Beginner":     "Beginner (0–1 year of experience)",
    "🚀 Intermediate": "Intermediate (2–3 years of experience)",
    "⚡ Advanced":     "Advanced (3+ years of experience)",
}

st.markdown('<p class="step-label">Step 3 of 3</p>', unsafe_allow_html=True)
st.markdown('<p class="step-title">📊 What\'s your current experience level?</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="step-subtitle">This helps us pitch the right complexity, suggest appropriate tools, '
    'and estimate realistic timelines for your projects</p>',
    unsafe_allow_html=True,
)

level_key = st.radio(
    "Level", options=list(LEVEL_MAP.keys()),
    index=list(LEVEL_MAP.keys()).index(st.session_state.level),
    horizontal=True, label_visibility="collapsed",
)
st.session_state.level = level_key

level_descriptions = {
    "🌱 Beginner":     "📌 Projects will use straightforward concepts, well-documented tools, and step-by-step guides.",
    "🚀 Intermediate": "📌 Projects will involve real-world integrations, APIs, and moderate architectural decisions.",
    "⚡ Advanced":     "📌 Projects will tackle system design, performance, scalability, and complex architectures.",
}
st.caption(level_descriptions[level_key])
st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  GENERATE BUTTON
# ════════════════════════════════════════════════
field  = st.session_state.field.strip()
stacks = st.session_state.stacks.strip()
level  = LEVEL_MAP[st.session_state.level]

if field:
    st.markdown(
        f'<div class="summary-bar">'
        f'<span class="summary-tag">🎯 Field: <span>{field}</span></span>'
        f'<span class="summary-tag">🛠️ Stack: <span>{stacks or "Open to suggestions"}</span></span>'
        f'<span class="summary-tag">📊 Level: <span>{level}</span></span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    clicked = st.button(
        "✨ Generate Ideas + Blogs", type="primary", use_container_width=True
    )
    if clicked:
        # Create progress bar and status
        progress_bar = st.progress(0, text="🤖 Starting AI agents...")
        status_text = st.empty()
        
        async def run_with_progress():
            try:
                # Start both agents in parallel
                status_text.text("🚀 Stay Tuned...")
                progress_bar.progress(10, text="🤖 Generating Ideas & Gathering Blogs...")
                
                ideas_task = asyncio.create_task(agent_generate_ideas(field, stacks, level))
                blogs_task = asyncio.create_task(agent_fetch_blogs(field, stacks))
                
                # Track progress as they complete
                ideas_done = False
                blogs_done = False
                ideas_result = None
                blogs_result = None
                
                while not (ideas_done and blogs_done):
                    # Check if ideas are done
                    if not ideas_done and ideas_task.done():
                        ideas_done = True
                        ideas_result = ideas_task.result()
                        progress_bar.progress(60, text="✅ Project ideas generated!")
                        status_text.text("💡 Ideas ready! Waiting for blogs...")
                        # Store ideas immediately
                        st.session_state.ideas_ready = ideas_result
                    
                    # Check if blogs are done  
                    if not blogs_done and blogs_task.done():
                        blogs_done = True
                        blogs_result = blogs_task.result()
                        progress_bar.progress(60, text="✅ Blog search completed!")
                        status_text.text("📚 Blogs ready! Waiting for ideas...")
                        # Store blogs immediately
                        st.session_state.blogs_ready = blogs_result
                    
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.1)
                
                # Get final results
                if not ideas_result:
                    ideas_result = ideas_task.result()
                if not blogs_result:
                    blogs_result = blogs_task.result()
                
                # Complete
                progress_bar.progress(100, text="✅ Done! Both agents completed successfully")
                status_text.text("🎉 All results ready!")
                
                # Store final results
                st.session_state.results = (ideas_result, blogs_result)
                st.session_state.generated = True
                st.session_state.ideas_ready = ideas_result
                st.session_state.blogs_ready = blogs_result
                
                # Clear progress indicators after a short delay
                await asyncio.sleep(1)
                progress_bar.empty()
                status_text.empty()
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Something went wrong: {e}")
        
        # Run the async function
        asyncio.run(run_with_progress())
else:
    st.info("👆 Fill in at least Step 1 (tech field) to unlock the generate button.")


# ════════════════════════════════════════════════
#  RESULTS
# ════════════════════════════════════════════════
if st.session_state.generated and st.session_state.results:
    ideas, blogs = st.session_state.results

    st.markdown("---")
    st.markdown("## 📦 Your Personalised Results")

    tab_ideas, tab_blogs = st.tabs([
        "💡 Project Ideas (5)",
        f"📚 Blogs & Articles ({len(blogs) if blogs else 0})",
    ])

    # ── Tab 1: Ideas ────────────────────────────
    with tab_ideas:
        if hasattr(st.session_state, 'ideas_ready') and st.session_state.ideas_ready:
            st.markdown(st.session_state.ideas_ready)
        elif hasattr(st.session_state, 'blogs_ready') and st.session_state.blogs_ready and not hasattr(st.session_state, 'ideas_ready'):
            # Ideas still loading, show progress bar
            st.progress(50, text="💡 Project ideas loading...")
            st.info("🤖 AI Agent 1 is still generating your project ideas...")
        else:
            st.info("🤖 Generating project ideas...")

    # ── Tab 2: Blogs ────────────────────────────
    with tab_blogs:
        if hasattr(st.session_state, 'blogs_ready') and st.session_state.blogs_ready:
            if st.session_state.blogs_ready:
                # source badge colour map
                SOURCE_COLORS = {
                    "medium.com":       ("#1a1a1a", "#ffffff"),
                    "dev.to":           ("#0a0a0a", "#ffffff"),
                    "geeksforgeeks.org":("#2f8d46", "#ffffff"),
                    "freecodecamp.org": ("#006400", "#ffffff"),
                    "hashnode.com":     ("#2962ff", "#ffffff"),
                    "towardsdatascience.com": ("#1a1a2e", "#e8eaf6"),
                }
                DEFAULT_COLOR = ("#2d3154", "#c5c8e8")

                for b in st.session_state.blogs_ready:
                    # extract readable domain for badge
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(b["url"]).netloc.replace("www.", "")
                    except Exception:
                        domain = ""
                    bg, fg = next(
                        (v for k, v in SOURCE_COLORS.items() if k in domain),
                        DEFAULT_COLOR
                    )
                    badge = (
                        f'<span style="background:{bg};color:{fg};font-size:0.68rem;'
                        f'font-weight:600;padding:2px 8px;border-radius:999px;'
                        f'border:1px solid rgba(255,255,255,0.15);margin-bottom:6px;'
                        f'display:inline-block;">{domain}</span>'
                    )
                    st.markdown(
                        f'<div class="blog-card">'
                        f'{badge}'
                        f'<a href="{b["url"]}" target="_blank" style="text-decoration:none;">'
                        f'<p class="blog-title">🔗 {b["title"]}</p></a>'
                        f'<p class="blog-snippet">{b["snippet"]}</p>'
                        f'<p class="blog-url">{b["url"]}</p>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.warning("No blogs found. Please try again or rephrase your tech field/stack.")
        elif hasattr(st.session_state, 'ideas_ready') and st.session_state.ideas_ready and not hasattr(st.session_state, 'blogs_ready'):
            # Blogs still loading, show progress bar
            st.progress(50, text="📚 Searching for blogs...")
            st.info("🤖 AI Agent 2 is still finding relevant blogs...")
        else:
            st.info("🤖 Searching for blogs...")

# ── Footer ───────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#525780; font-size:0.8rem;">'
    "✨ Powered by Groq (Llama 3.3 70B) · DuckDuckGo Search"
    "</p>",
    unsafe_allow_html=True,
)