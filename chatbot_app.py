import streamlit as st
from openai import OpenAI
import os
from time import sleep
import asyncio
import copy

import requests
import json
import re

import biluppgifter

# language dictionary
language_dict = {
    "en": {
        "A_prompt": "You are a diagnostic assistant designed to help mechanics solve issues with cars. Given Diagnostic Trouble Codes (DTCs), generic information about the car (like manufacturer, year, model, engine ID, etc.), and the resolutions of single error codes from manuals, you can understand problems by combining knowledge from different errors. You will derive procedures and instructions to propose to mechanics to fix them. You should emphasize the information sent by mechanics about error codes to generate answers that stick to what is provided. You combine this info to truly understand the problem while avoiding generating incorrect or hallucinated answers. You communicate in a technical but clear and accessible manner, suitable for both experienced and new mechanics. Provide step-by-step instructions to ensure thorough and safe troubleshooting and repair.",
        "B_prompt": "Write the problems raised in the threads and the solutions to the problems raised in the threads. Do not name people or users. Explain these solutions and problems only as if you arrived at them through your expertise your knowledge bank. Write as concisely as possible and technically in detail. There are several solutions in the threads so that these are described but with an emphasis on the solution that occurs most often in the threads. Write your answer to the person in the following structure: Problem:; Solution:",
        "C_prompt": "You are a car diagnostic assistant for mechanics. When provided with information about error codes (DTCs), vehicle details (like manufacturer, year, model, engine ID, etc.), and error resolutions from car manufacturer manuals and car repair community (forums), you will intelligently combine this information to offer concise, effective solutions for troubleshooting and fixing issues. The goal is to help mechanics quickly and accurately diagnose and resolve car problems based on the provided data. Emphasize information from forums especially if a combination of DTCs is present, as forums are excellent at identifying the real issue when multiple errors occur. However, also consider the information from manuals as the ground truth. Responses should be short and effective, avoiding hallucinations by grounding solutions in the provided information. Follow information from manuals and forums, understand the issue, and provide clear and concise resolutions to the mechanics. Communicate in a technical but clear and accessible manner, suitable for both experienced and new mechanics."
    },
    "se": {
        "A_prompt": "Du är en diagnostisk assistent som är utformad för att hjälpa mekaniker att lösa problem med bilar. Med hjälp av diagnosfelkoder (DTC), generell information om bilen (som tillverkare, år, modell, motornummer, etc.) och lösningar på enskilda felkoder från manualer kan du förstå problem genom att kombinera kunskap från olika fel. Du kommer att utarbeta procedurer och instruktioner att föreslå för mekaniker för att fixa dem. Du bör betona den information som skickas av mekaniker om felkoder för att generera svar som håller sig till det som tillhandahålls. Du kombinerar denna information för att verkligen förstå problemet samtidigt som du undviker att generera felaktiga eller hallucinerade svar. Du kommunicerar på ett tekniskt men tydligt och tillgängligt sätt, lämpligt för både erfarna och nya mekaniker. Ge steg-för-steg-instruktioner för att säkerställa grundlig och säker felsökning och reparation.",
        "B_prompt": "Skriv problemen som tas upp i trådarna och lösningarna på problemen som tas upp i trådarna. Nämn inte personer eller användare. Förklara dessa lösningar och problem enbart som om du kommit fram till dom via din expertis din kunskapsbank. Skriv så kortfattat som möjligt samt tekniskt detaljerat. Det finns flera olika lösningar i trådarna så att dessa beskrivas men med betoning på lösningen som förekommer oftast i trådarna. Skriv ditt svar till personen i löpande form enligt följande struktur: Problem:; Lösning:",
        "C_prompt": "Du är en diagnostikassistent för bilmekaniker. När du får information om felkoder (DTC), fordonsdetaljer (som tillverkare, årsmodell, modell, motor-ID etc.) och fellösningar från biltillverkarens manualer och bilreparationscommunityn (forum), kombinerar du denna information på ett intelligent sätt för att erbjuda kortfattade och effektiva lösningar för felsökning och problemlösning. Målet är att hjälpa mekaniker att snabbt och korrekt diagnostisera och lösa bilproblem baserat på de tillhandahållna uppgifterna. Betona information från forum, särskilt om en kombination av DTC:er förekommer, eftersom forum är utmärkta på att identifiera det verkliga problemet när flera fel uppstår. Betrakta dock även informationen från manualer som den sanna grunden. Svaren ska vara korta och effektiva och undvika hallucinationer genom att grunda lösningarna i den information som tillhandahålls. Följ information från manualer och forum, förstå problemet och ge mekanikerna tydliga och koncisa lösningar. Kommunicera på ett tekniskt men tydligt och lättillgängligt sätt som passar både erfarna och nya mekaniker."
    },
}

# set the OpenAI API key
client = OpenAI(organization='org-pWvJLxaWnYi652BL7AGbQjXl', project=st.secrets["openai"]["PROJECT_ID"], api_key=st.secrets["openai"]["OPENAI_API_KEY"])

# initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "form_submitted" not in st.session_state:
    st.session_state["form_submitted"] = False
if "pdf_instructions" not in st.session_state:
    st.session_state["pdf_instructions"] = ""
if "forum_instructions" not in st.session_state:
    st.session_state["forum_instructions"] = ""
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "params" not in st.session_state:
    st.session_state["params"] = dict()
if "fast_instructions" not in st.session_state:
    st.session_state["fast_instructions"] = None
if "selected_language" not in st.session_state:
    st.session_state["selected_language"] = "en"

# language toggle
selected_language = st.sidebar.radio("Select language for prompts:", ("en", "se"), format_func=lambda x: x.upper())
st.session_state["selected_language"] = selected_language

# function to reset chat and form
def reset_chat(params):
    st.session_state.messages = [{"role": "system", "content": "You are a helpful diagnostic assistant for mechanics, solving car issues."}]
    filtered_params = {k: v for k, v in params.items() if k != "meta_params"}
    st.session_state["messages"].append({"role": "user", "content": f"Hi, I have a car issue.\n\n{filtered_params}"})
    st.session_state["fast_instructions"] = None
    st.session_state["pdf_instructions"] = ""
    st.session_state["forum_instructions"] = ""

# function to send parameters to the CodeoC API and get the first message of the chatbot
async def initialize_chat(params):
    # # dummy response
    # sleep(7) # simulate delay
    # st.session_state["messages"].append({"role": "assistant", "content": "I am here to help you with your car issue."})

    # call the CodeoC API
    response = requests.post(st.secrets["codeoc"]["API_ENDPOINT"], json=params)
    if response.status_code == 200:
        body = json.loads(response.text)
        # final instructions from the API
        final_instructions = body["final_instructions"]
        # store the PDF and forum instructions in the session state
        st.session_state["pdf_instructions"] = body["pdf_instructions"]
        st.session_state["forum_instructions"] = body["forum_instructions"]
        st.session_state["messages"].append({"role": "assistant", "content": final_instructions})
    else:
        message = json.loads(response.text)
        st.session_state["messages"].append({"role": "assistant", "content": f"{message['error']}\n\nError code: {response.status_code}\n\nError on A - PDF instructions: {message['A']}\n\nError on B - Forum instructions: {message['B']}"})

    placeholder = st.empty()
    placeholder.markdown(st.session_state["messages"][-1]["content"])
    if st.session_state["pdf_instructions"] != "":
        with st.expander("A - PDF instructions"):
            st.write(st.session_state["pdf_instructions"])
    if st.session_state["forum_instructions"] != "":
        with st.expander("B - Forum instructions"):
            st.write(st.session_state["forum_instructions"])

async def get_fast_instructions(params):
    # # dummy response
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
    params["meta_params"]["super_fast_instructions"] = True
    response = requests.post(st.secrets["codeoc"]["API_ENDPOINT"], json=params)
    if response.status_code == 200:
        st.session_state["fast_instructions"] = json.loads(response.text)["rendered_responses"]
        for dtc in st.session_state["fast_instructions"]:
            with st.expander(f"Fast instructions for {dtc['DTC']}"):
                st.write(dtc["llm_rendered_response"])
    else:
        st.error(f"Error getting fast instructions: {response.text}")

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
        # license plate and vin parameters
        regno = st.text_input("License plate", value="NLA828")
        vin = st.text_input("VIN")
        country_code = st.text_input("Country code", value="SE")

        st.markdown("---")

        # other parameters
        dtcs = st.text_input("dtcs", value="P0030, P0134")
        internal_error_codes = st.text_input("internal error codes")
        manufacturer = st.text_input("manufacturer", value=st.session_state["params"].get("manufacturer", "volkswagen"))
        model = st.text_input("model", value=st.session_state["params"].get("model", "golf gti"))
        engine_id = st.text_input("engine id", value=st.session_state["params"].get("engine_id", "BEV"))
        mileage = st.text_input("mileage")
        year = st.text_input("year", value=st.session_state["params"].get("year", ""))

        st.markdown("---")

        # prompt text fields and temperature slider
        A_prompt = st.text_area("Prompt A - PDF instructions", value=language_dict[st.session_state["selected_language"]]["A_prompt"])
        A_temperature = st.slider("Prompt A - Temperature", min_value=0.0, max_value=2.0, value=0.7, step=0.1)
        B_prompt = st.text_area("Prompt B - Forum instructions", value=language_dict[st.session_state["selected_language"]]["B_prompt"])
        B_temperature = st.slider("Prompt B - Temperature", min_value=0.0, max_value=2.0, value=0.7, step=0.1)
        C_prompt = st.text_area("Prompt C - Final instructions", value=language_dict[st.session_state["selected_language"]]["C_prompt"])
        C_temperature = st.slider("Prompt C - Temperature", min_value=0.0, max_value=2.0, value=0.7, step=0.1)

        submit_button = st.form_submit_button(label='Submit')
    
        if submit_button:
            # dtcs and internal_error_codes are coma separated lists
            dtcs = [dtc.strip() for dtc in dtcs.split(",") if dtc]
            internal_error_codes = [internal_error_code.strip() for internal_error_code in internal_error_codes.split(",") if internal_error_code]

            # check if all dtcs are valid
            pattern = re.compile(r'\b[PCBU0-9](?=[A-Z0-9]*\d)[A-Z0-9]{4}\b')
            no_errors = True
            dtcs_list = []
            internal_error_codes_list = []
            for dtc in dtcs:
                if pattern.match(dtc.replace(" ", "")):
                    dtcs_list.append(dtc)
                else:
                    st.error(f"Invalid DTC code: {dtc}")
                    no_errors = False
                    break
            #pattern = re.compile(r'\b[0-9](?=[A-Z0-9]*\d)[A-Z0-9]{4}\b')
            for internal_error_code in internal_error_codes:
                if pattern.match(internal_error_code.replace(" ", "")):
                    internal_error_codes_list.append(internal_error_code)
                else:
                    st.error(f"Invalid internal error code: {internal_error_code}")
                    no_errors = False
                    break

            if no_errors and (dtcs_list or internal_error_codes_list):
                st.session_state["form_submitted"] = True
                st.session_state["params"] = {
                    "dtcs": [str(dtc) for dtc in dtcs_list] if dtcs_list else None,
                    "internal_error_codes": [str(internal_error_code) for internal_error_code in internal_error_codes_list] if internal_error_codes_list else None,
                    "vin": vin if vin else None,
                    "regno": regno if regno else None,
                    "manufacturer": manufacturer if manufacturer else None,
                    "model": model if model else None,
                    "engine_id": engine_id if engine_id else None,
                    "mileage": mileage if mileage else None,
                    "year": year if year else None,
                    "meta_params": {
                        "language": st.session_state["selected_language"],
                        "A_prompt": A_prompt,
                        "A_temperature": A_temperature,
                        "B_prompt": B_prompt,
                        "B_temperature": B_temperature,
                        "C_prompt": C_prompt,
                        "C_temperature": C_temperature,
                        "country_code": country_code
                    }
                }
                # get vehicle information if regno or vin is provided
                if regno or vin:
                    res = biluppgifter.get_car_info(regno=regno, vin=vin, country_code=country_code)
                    if res["statusCode"] != 200:
                        st.error(res["body"])
                        st.session_state["form_submitted"] = False
                        no_errors = False
                    else:
                        vehicle_info = json.loads(res["body"])
                        # update manufacturer, model, engine_id, and year
                        st.session_state["params"]["manufacturer"] = vehicle_info["data"]["basic"]["data"].get("make")
                        st.session_state["params"]["model"] = vehicle_info["data"]["basic"]["data"].get("model")
                        st.session_state["params"]["engine_id"] = vehicle_info["data"]["basic"]["data"].get("engine_id")
                        st.session_state["params"]["year"] = vehicle_info["data"]["basic"]["data"].get("vehicle_year")
                if no_errors:
                    reset_chat(copy.deepcopy(st.session_state["params"]))
                    st.rerun()
            else:
                st.error("Enter at least one DTC/internal error code in the correct format (e.g., DTCS: P0030, P0134; Internal error codes: 00001, 00002)")

    # chat interface
    if st.session_state["form_submitted"]:
        st.title("CodeoC Car Diagnostic Expert")

        # display chat messages skipping the first system message
        print("Loading chat messages...")
        for i, message in enumerate(st.session_state.messages[1:], 1):
            if i == 2:
                with st.chat_message(message["role"]):
                    # display fast instructions
                    if st.session_state["fast_instructions"]:
                        for fast_inst in st.session_state["fast_instructions"]:
                            with st.expander(f"Fast instructions for {fast_inst['DTC']}"):
                                st.write(fast_inst['llm_rendered_response'])

                    st.markdown(message["content"])

                    # display the PDF and forum instructions
                    if st.session_state["pdf_instructions"] != "":
                        with st.expander("A - PDF instructions"):
                            st.write(st.session_state["pdf_instructions"])
                    if st.session_state["forum_instructions"] != "":
                        with st.expander("B - Forum instructions"):
                            st.write(st.session_state["forum_instructions"])
            else:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # user-provided prompt
        if prompt := st.chat_input(disabled=False):
            print("User prompt received.")
            if st.session_state.messages[-1]["role"] != "user":
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

        # assistant response
        if st.session_state.messages[-1]["role"] != "assistant":
            print("Assistant response.")
            #print(st.session_state["messages"])
            # if chat has 2 messages, call the CodeoC API to get fast instructions and initialize the chat
            if len(st.session_state["messages"]) == 2:
                print("Initializing chat...")
                with st.chat_message("assistant"):
                    with st.spinner("Processing. Please wait..."):
                        task1 = asyncio.create_task(get_fast_instructions(copy.deepcopy(st.session_state["params"])))
                        task2 = asyncio.create_task(initialize_chat(copy.deepcopy(st.session_state["params"])))
                        await asyncio.gather(task1, task2)
                        st.rerun()
            else:
                print("Chatting...")
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    full_response = ""

                    # # dummy response
                    # full_response = "I am here to help you with your car issue."
                    # placeholder.markdown(full_response)

                    try:
                        messages = st.session_state["messages"]

                        # call the OpenAI API - stream the response
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

                        # # call the OpenAI API - get the full response
                        # response = client.chat.completions.create(
                        #     model="gpt-4o-mini",
                        #     messages=messages,
                        #     temperature=0.7
                        # )
                        # full_response = response.choices[0].message.content.strip()
                        # placeholder.markdown(full_response)
                    except Exception as e:
                        st.error(f"An error occurred: {e}. Please refresh the page and try again.")
                        st.stop()

                st.session_state["messages"].append({"role": "assistant", "content": full_response})
    else:
        st.write("Please fill in the form on the left to start chatting with the assistant.")

# run the app
if __name__ == "__main__":
    asyncio.run(main())
