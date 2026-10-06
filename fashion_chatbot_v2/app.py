import streamlit as st
from rag_engine import RAGEngine
from outfit_recommender import OutfitRecommender

st.set_page_config(
    page_title="AI Fashion Consultant",
    page_icon="🛍️",
    layout="wide"
)
st.title("🛍️ Chuyên viên tư vấn thời trang")


@st.cache_resource
def load_engine():
    rag = RAGEngine()
    return rag, OutfitRecommender(rag)


rag, outfit_rec = load_engine()

# ============ CHAT CHÍNH ============
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Xin chào! Mình là trợ lý thời trang 👗👔\n\n"
                       "Mình có thể giúp bạn:\n"
                       "- 🧮 Tư vấn size dựa trên chiều cao, cân nặng\n"
                       "- 👗 Gợi ý phối đồ theo dịp (đi làm, đi chơi, dự tiệc, cafe...)\n"
                       "- 🔍 Tìm sản phẩm theo ngân sách, màu sắc, mùa\n"
                       "- 💬 So sánh sản phẩm\n\n"
                       "Bạn cần tìm trang phục gì hôm nay? 😊"
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_input := st.chat_input("Ví dụ: Tôi cao 1m70 nặng 60kg, muốn tìm đầm đi cafe..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    history_text = "\n".join([
        f"{m['role']}: {m['content']}"
        for m in st.session_state.messages[:-1]
    ])

    with st.chat_message("assistant"):
        with st.spinner("AI đang suy nghĩ..."):
            response = rag.generate_response(user_input, history_text)
            st.write(response)

    st.session_state.messages.append({"role": "assistant", "content": response})