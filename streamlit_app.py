import streamlit as st
from research_agent import ResearchAgent
import json
import io


st.set_page_config(page_title="Research Agent", layout="wide")

st.markdown("""
<style>
body { font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }
.stApp { background-color: #f8fafc; }
.top-row { display:flex; gap:8px; align-items:center; }
/* Improve Markdown and code readability across themes */
.stMarkdown, .stMarkdown span, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
    color: #0f172a !important;
}
/* Make code blocks more readable */
.stCodeBlock, pre, code {
    color: #e6eef8 !important;
    background: #0b1220 !important;
}
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown("# 🔬 Research Agent — Streamlit Edition")

    # Top input row
    with st.form(key='research_form'):
        cols = st.columns([6, 1, 1])
        question = cols[0].text_input("Research question", value="", placeholder="What are the latest advances in artificial intelligence?", key='question')
        max_sources = cols[1].number_input("Max sources", min_value=1, max_value=50, value=10, step=1)
        submit = cols[2].form_submit_button("🚀 Start")

    if 'agent' not in st.session_state:
        st.session_state.agent = ResearchAgent()

    agent: ResearchAgent = st.session_state.agent

    if submit:
        if not question.strip():
            st.error("Please enter a research question.")
            return

        # Run research with a spinner
        placeholder = st.empty()
        progress_bar = st.progress(0)
        with placeholder.container():
            st.info("Starting research — this may take a minute depending on API calls...")

        # We will approximate progress since ResearchAgent runs synchronously
        try:
            with st.spinner('Running research pipeline...'):
                # Run the research synchronously; show coarse progress updates
                progress_bar.progress(5)
                output = agent.research(question, verbose=False)
                progress_bar.progress(80)

                # Format output (heavy string generation)
                formatted = agent.format_output(output)
                progress_bar.progress(100)

        except Exception as e:
            st.error(f"Research failed: {e}")
            return

        # Clear placeholders
        placeholder.empty()

        # Render results in two columns: essay (left) and report (right)
        left, right = st.columns([2, 3])

        with left:
            st.subheader("Essay")
            if output.essay:
                st.markdown(output.essay)
            else:
                st.info("Essay was not generated or is empty.")

            # Download essay
            essay_bytes = output.essay.encode('utf-8') if output.essay else b''
            st.download_button("Download Essay (txt)", data=essay_bytes, file_name="essay.txt")

        with right:
            st.subheader("Full Report")
            st.write(f"**Question:** {output.question}")
            st.write(f"**Generated:** {output.timestamp}")
            st.write(f"**Sources analyzed:** {len(agent.memory.notes)}")
            st.markdown("---")
            st.code(formatted, language='text')
            
            # Render individual sources with titles and links for visibility
            if agent.memory.notes:
                st.markdown("**Sources (click to open):**")
                for note in agent.memory.notes:
                    try:
                        title = note.source_title or note.source_url
                        url = note.source_url
                        st.markdown(f"- [{title}]({url})")
                    except Exception:
                        pass

            # Download JSON and TXT
            json_data = json.dumps({
                'question': output.question,
                'overview': output.overview,
                'key_findings': output.key_findings,
                'challenges': output.challenges,
                'conclusion': output.conclusion,
                'sources': output.sources,
                'essay': output.essay,
                'timestamp': output.timestamp
            }, indent=2, ensure_ascii=False)

            st.download_button("Download JSON", data=json_data.encode('utf-8'), file_name='research_output.json')
            st.download_button("Download Report (txt)", data=formatted.encode('utf-8'), file_name='full_report.txt')

    # If there's a previous result, show quick access
    if hasattr(st.session_state, 'agent') and st.session_state.agent.memory.notes:
        st.sidebar.header("Last run stats")
        st.sidebar.write(f"Notes stored: {len(st.session_state.agent.memory.notes)}")
        try:
            quota = st.session_state.agent.llm_client.get_quota_status()
            st.sidebar.write(f"Quota: {quota.get('requests_used',0)}/{quota.get('requests_limit',0)}")
        except Exception:
            pass


if __name__ == '__main__':
    main()
