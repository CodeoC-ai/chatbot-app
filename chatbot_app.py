import streamlit as st
from openai import OpenAI
import os
from time import sleep
import asyncio

import requests
import json
import re

# set the OpenAI API key
client = OpenAI(organization='org-pWvJLxaWnYi652BL7AGbQjXl', project=st.secrets["openai"]["PROJECT_ID"], api_key=st.secrets["openai"]["OPENAI_API_KEY"])

# initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "form_submitted" not in st.session_state:
    st.session_state["form_submitted"] = False
if "pdf_instructions" not in st.session_state:
    st.session_state["pdf_instructions"] = "You can find the PDF instructions here."
if "forum_instructions" not in st.session_state:
    st.session_state["forum_instructions"] = "You can find the forum instructions here."
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "params" not in st.session_state:
    st.session_state["params"] = None
if "fast_instructions" not in st.session_state:
    st.session_state["fast_instructions"] = None

# function to reset chat and form
def reset_chat(params):
    st.session_state.messages = [{"role": "system", "content": "You are a helpful diagnostic assistant for mechanics, solving car issues."}]
    st.session_state["messages"].append({"role": "user", "content": f"Hi, I have a car issue.\n\n{params}"})

# function to send parameters to the CodeoC API and get the first message of the chatbot
async def initialize_chat(params):
    # # dummy response
    # sleep(7) # simulate delay
    # st.session_state["messages"].append({"role": "assistant", "content": "I am here to help you with your car issue."})

    # call the CodeoC API
    response = requests.post(st.secrets["codeoc"]["API_ENDPOINT"], json=params)
    if response.status_code == 200:
        print(response.text)
        body = json.loads(response.text)
        # final instructions from the API
        final_instructions = body["final_instructions"]
        # store the PDF and forum instructions in the session state
        st.session_state["pdf_instructions"] = body["pdf_instructions"]
        st.session_state["forum_instructions"] = body["forum_instructions"]
        st.session_state["messages"].append({"role": "assistant", "content": final_instructions})
    else:
        st.session_state["messages"].append({"role": "assistant", "content": f"Error: {response.status_code} - {response.text}"})

    placeholder = st.empty()
    placeholder.markdown(st.session_state["messages"][-1]["content"])
    with st.expander("A - PDF instructions"):
        st.write(st.session_state["pdf_instructions"])
    with st.expander("B - Forum instructions"):
        st.write(st.session_state["forum_instructions"])

async def get_fast_instructions(params):
    # # # dummy response
    # sleep(1) # simulate delay
    # response = {
    #     "rendered_responses": [
    #         {
    #             "DTC": "P0030",
    #             "llm_rendered_response": "Fast instructions for P0030"
    #         },
    #         {
    #             "DTC": "P0134",
    #             "llm_rendered_response": "Fast instructions for P0134"
    #         }
    #     ]
    # }
    # st.session_state["fast_instructions"] = response["rendered_responses"]
    # for dtc in st.session_state["fast_instructions"]:
    #     with st.expander(f"Fast instructions for {dtc['DTC']}"):
    #         st.write(dtc['llm_rendered_response'])

    # call the CodeoC API
    params["super_fast_instructions"] = True
    response = requests.post(st.secrets["codeoc"]["API_ENDPOINT"], json=params)
    if response.status_code == 200:
        st.session_state["fast_instructions"] = json.loads(response.text)["rendered_responses"]
        for dtc in st.session_state["fast_instructions"]:
            with st.expander(f"Fast instructions for {dtc['DTC']}"):
                st.write(dtc["llm_rendered_response"])
    else:
        st.error("Error getting fast instructions.")

# function to check password
def check_password():
    if st.session_state["authenticated"]:
        return True

    st.write("### Please enter the password to access the app")
    password = st.text_input("Password", type="password", key="password")
    if st.button("Submit") or password:
        if password == st.secrets["password"]:
            st.session_state["authenticated"] = True
            st.rerun()  # force rerun to update the UI
        else:
            st.error("Invalid password")
    return False

# main function to run the app
async def main():
    # # check if the user is authenticated
    # if not st.session_state["authenticated"]:
    #     check_password()
    #     return
    
    # sidebar form for input parameters
    with st.sidebar.form(key='input_form'):
        # set parameters
        dtcs = st.text_input("dtcs", value="P0030, P0134")
        vags = st.text_input("vags")
        vin = st.text_input("vin")
        manufacturer = st.text_input("manufacturer", value="volkswagen")
        model = st.text_input("model", value="golf")
        engine_id = st.text_input("engine id", value="BEV")
        mileage = st.text_input("mileage")
        year = st.text_input("year")

        submit_button = st.form_submit_button(label='Submit')
    
        if submit_button:
            # dtcs and vags are coma separated lists
            dtcs = [dtc.strip() for dtc in dtcs.split(",") if dtc]
            vags = [vag.strip() for vag in vags.split(",") if vag]

            # check if all dtcs are valid
            pattern = re.compile(r'\b[PCBU0-9](?=[A-Z0-9]*\d)[A-Z0-9]{4}\b')
            no_errors = True
            dtcs_list = []
            for dtc in dtcs:
                if pattern.match(dtc):
                    dtcs_list.append(dtc)
                else:
                    st.error(f"Invalid DTC code: {dtc}")
                    no_errors = False
                    break

            if no_errors and dtcs_list:
                st.session_state["form_submitted"] = True
                st.session_state["params"] = {
                    "dtcs": [str(dtc) for dtc in dtcs_list] if dtcs_list else None,
                    "vags": [str(vag) for vag in vags] if vags else None,
                    "vin": vin if vin else None,
                    "manufacturer": manufacturer if manufacturer else None,
                    "model": model if model else None,
                    "engine_id": engine_id if engine_id else None,
                    "mileage": mileage if mileage else None,
                    "year": year if year else None
                }
                reset_chat(st.session_state["params"])
                st.rerun()
            else:
                st.error("Enter at least one DTC code in the correct format (e.g., P1234).")

    # chat interface
    if st.session_state["form_submitted"]:
        st.title("CodeoC Car Diagnostic Expert")

        # display chat messages skipping the first system message
        for i, message in enumerate(st.session_state.messages[1:], 1):
            if i == 2:
                with st.chat_message(message["role"]):
                    # display fast instructions
                    for fast_inst in st.session_state["fast_instructions"]:
                        with st.expander(f"Fast instructions for {fast_inst['DTC']}"):
                            st.write(fast_inst['llm_rendered_response'])

                    st.markdown(message["content"])

                    # display the PDF and forum instructions
                    with st.expander("A - PDF instructions"):
                        st.write(st.session_state["pdf_instructions"])
                    with st.expander("B - Forum instructions"):
                        st.write(st.session_state["forum_instructions"])
            else:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # user-provided prompt
        if prompt := st.chat_input(disabled=False):
            if st.session_state.messages[-1]["role"] != "user":
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

        # assistant response
        if st.session_state.messages[-1]["role"] != "assistant":
            #print(st.session_state["messages"])
            # if chat has 2 messages, call the CodeoC API to get fast instructions and initialize the chat
            if len(st.session_state["messages"]) == 2:
                print("Initializing chat...")
                with st.chat_message("assistant"):
                    with st.spinner("Processing. Please wait..."):
                        task1 = asyncio.create_task(get_fast_instructions(st.session_state["params"].copy()))
                        task2 = asyncio.create_task(initialize_chat(st.session_state["params"].copy()))
                        await asyncio.gather(task1, task2)
            else:
                print("Chatting...")
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    full_response = ""

                    # # dummy response
                    # full_response = "I am here to help you with your car issue."
                    # placeholder.markdown(full_response)

                    messages = st.session_state["messages"]
                    # call the OpenAI API
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        temperature=0.7,
                        stream=True
                    )

                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            placeholder.markdown(full_response)

                st.session_state["messages"].append({"role": "assistant", "content": full_response})
    else:
        st.write("Please fill in the form on the left to start chatting with the assistant.")

# run the app
if __name__ == "__main__":
    asyncio.run(main())
