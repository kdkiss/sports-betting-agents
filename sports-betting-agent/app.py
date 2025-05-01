import streamlit as st
from bobby_bets_agent import ask_bobby, manage_memory
import json
import uuid
import logging
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(page_title="Bobby Bets Sports Analysis", page_icon="⚽🏀", layout="wide")

# Initialize session state for user ID
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user_{uuid.uuid4().hex[:8]}"

# Main app
def muchacho():
    st.title("⚽🏀 Bobby Bets Sports Analysis 🏀⚽")
    st.markdown("""
    Ask about any two NBA or football teams for data-driven betting insights!  
    Select the sport, enter your question, and manage your analysis history with memory commands.
    """)

    # User ID input
    user_id = st.text_input("Enter your username (or use default):", value=st.session_state.user_id)
    if user_id != st.session_state.user_id:
        st.session_state.user_id = user_id
    st.write(f"Using user ID: **{st.session_state.user_id}**")

    # Sport selection
    sport = st.selectbox("Select sport:", ["NBA", "Football"], index=0)
    sport_lower = sport.lower()

    # Query input
    question = st.text_input(f"Your {sport} question (e.g., 'How do {'Lakers and Warriors' if sport == 'NBA' else 'Manchester United and Athletic Club'} match up for their game on 2025-05-01?'):")

    # Submit query button
    if st.button("Analyze"):
        if not question:
            st.error("Please enter a question.")
        else:
            with st.spinner("Analyzing... (this may take a moment)"):
                try:
                    response = asyncio.run(ask_bobby(question, user_id=st.session_state.user_id, sport=sport_lower))
                    st.markdown("### Analysis")
                    st.write(response["output"])
                except Exception as e:
                    logger.error(f"Error during analysis: {str(e)}")
                    st.error(f"Sorry, an error occurred during analysis: {str(e)}.")

    # Memory management buttons
    st.markdown("### Memory Commands")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("List Memory", key="list_memory"):
            if "list_memory_processing" not in st.session_state:
                st.session_state.list_memory_processing = False
            if not st.session_state.list_memory_processing:
                st.session_state.list_memory_processing = True
                try:
                    input_dict = {"action": "search", "user_id": st.session_state.user_id}
                    memories_json = manage_memory.invoke(input_dict)
                    memories = json.loads(memories_json)
                    if not memories:
                        st.info(f"No memories found for user {st.session_state.user_id}.")
                    else:
                        st.markdown(f"**Memories for user {st.session_state.user_id}:**")
                        for mem in memories[:10]:
                            st.write(f"- {mem['memory']}")
                        if len(memories) > 10:
                            st.write(f"... and {len(memories) - 10} more")
                except Exception as e:
                    logger.error(f"Error listing memories: {str(e)}")
                    st.error(f"Error listing memories: {str(e)}")
                finally:
                    st.session_state.list_memory_processing = False
    
    with col2:
        if st.button("Count Memory", key="count_memory"):
            try:
                input_dict = {"action": "count", "user_id": st.session_state.user_id}
                result = manage_memory.invoke(input_dict)
                st.info(result)
            except Exception as e:
                logger.error(f"Error counting memories: {str(e)}")
                st.error(f"Error counting memories: {str(e)}")
    
    with col3:
        if st.button("Clear Memory", key="clear_memory"):
            try:
                input_dict = {"action": "clear", "user_id": st.session_state.user_id}
                result = manage_memory.invoke(input_dict)
                st.success(result)
            except Exception as e:
                logger.error(f"Error clearing memories: {str(e)}")
                st.error(f"Error clearing memories: {str(e)}")

if __name__ == "__main__":
    muchacho()
