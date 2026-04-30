import streamlit as st


st.set_page_config(page_title="Calculadora Streamlit", page_icon="📱", layout="centered")


st.markdown("""
    <style>
    .stApp { background-color: #000000; }
    .block-container { max-width: 400px !important; padding-top: 2rem !important; }

    
    .ios-display {
        background-color: #000000;
        color: white;
        font-size: 80px;
        text-align: right;
        font-family: sans-serif;
        min-height: 100px;
        margin-bottom: 20px;
    }

    
    .stButton > button {
        border-radius: 50% !important;
        width: 80px !important;
        height: 80px !important;
        font-size: 30px !important;
        border: none !important;
        margin: 5px auto !important;
        display: block !important;
        color: white !important;
    }

    

    
    .stButton > button {
        background-color: #ff9f0a !important;
    }

   
    div[data-testid="stHorizontalBlock"] div:last-child .stButton > button {
        background-color: #add8e6 !important;
        color: black !important;
    }

    div[data-testid="stHorizontalBlock"]:nth-of-type(2) div:nth-child(-n+3) .stButton > button {
        background-color: #a5a5a5 !important;
        color: black !important;
    }

    div[data-testid="stHorizontalBlock"]:last-child div:last-child .stButton > button {
        background-color: #add8e6 !important;
        color: black !important;
    }

    div[data-testid="stHorizontalBlock"] { gap: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

if 'calc_val' not in st.session_state:
    st.session_state.calc_val = "0"

def click_button(label):
    actual = st.session_state.calc_val
    if label == "AC":
        st.session_state.calc_val = "0"
    elif label == "=":
        try:
            expr = actual.replace('×', '*').replace('÷', '/')
            res = eval(expr)
            st.session_state.calc_val = f"{res:g}" if isinstance(res, float) else str(res)
        except:
            st.session_state.calc_val = "Error"
    else:
        if actual == "0" or actual == "Error":
            st.session_state.calc_val = str(label)
        else:
            if len(actual) < 9:
                st.session_state.calc_val += str(label)

st.markdown(f'<div class="ios-display">{st.session_state.calc_val}</div>', unsafe_allow_html=True)

filas = [
    ['AC', '+/-', '%', '÷'],
    ['7', '8', '9', '×'],
    ['4', '5', '6', '-'],
    ['1', '2', '3', '+'],
    ['0', '.', '=']
]

for i, fila in enumerate(filas):
    cols = st.columns(len(fila))
    for j, label in enumerate(fila):
        cols[j].button(label, key=f"btn_{i}_{j}", on_click=click_button, args=(label,))