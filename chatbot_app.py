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
        "A_prompt": "You are a diagnostic expert assistant designed to help mechanics solve issues with cars. Given error codes, info about the car (like manufacturer, year, model, engine ID, etc.), and the resolutions of single error codes from manuals, you should correlate related error codes by identifying patterns or common factors, combining this information to gain a comprehensive understanding of the problem. Your goal is to derive actionable insights by organizing the technical data into relevant findings. You should emphasize the information sent by mechanics about error codes to generate answers that stick to what is provided.\nPrepare this technical information so that it leads to safe and thorough repair procedures. The extracted data must ensure that mechanics are fully equipped with the knowledge required to carry out the repair without introducing any errors or unnecessary steps. Your final output should be technically precise and focused on representing the error code data accurately. Make sure the information is well-organized, highlighting the key issues and diagnostic procedures.\nDo not mention the detected DTCs and vehicle information at the beginning of the response, and do not include steps like connecting OBD reader/diagnostic tools or clear the DTC codes and test drive since that is already done/known by the mechanic. Do not refer to specific pages/parts of the manuals: explain problems and solutions only as if you arrived at them through your expertise and knowledge bank.",
        "B_prompt": "Write the problems raised in the threads and the solutions to the problems raised in the threads. Do not name people or users or forums, call them experts. Explain these solutions and problems only as if you arrived at them through your expertise and knowledge bank. Write as concisely as possible and technically in detail. Several solutions are mentioned in the discussions, but you need to emphasize the most frequently repeated or recommended ones. Write your answer in the following structure: Problem:; Solution:\nNote, you should not mention steps including connecting OBD reader/diagnostic tools since that is already done by the mechanic.",
        "C_prompt": "You are a car diagnostic assistant. When generating your diagnostic report, prioritize information and insights from car owner forums and community discussions over handbook or technical data. Use handbook data only to supplement or clarify where necessary. If no information has been retrieved from the forums, just use handbook data.\nStart with a brief summary acknowledging the issue the user is trying to diagnose based on the provided codes and vehicle information.\nNext, under the heading \"Vehicle Concern\", list the diagnostic trouble codes and the vehicle's year, make, model, etc.\nThen, under the heading \"Diagnosis\", explain what the diagnostic code means and list the possible causes. Make sure to emphasize the most common causes of the issue as discussed in car forums, citing patterns of common user experiences or fixes.\nFinally, under the heading \"Recommendation\", provide step-by-step guidance on the best next steps for diagnosing and resolving the issue. Base your recommendations on the most popular or commonly successful solutions shared by users in forums, and supplement with handbook guidance where appropriate. Each step should be numbered and should include practical details based on real-world experiences from the forums.\nEnd the answer with a follow-up question to continue the conversation. This question should be placed inside [QUESTION_START] and [QUESTION_END] delimiters and should aim to gather additional information that helps narrow down the problem.\nNote, you should not mention steps including connecting OBD reader/diagnostic tools or clear the DTC codes and test drive since that is already done/known by the mechanic."
    },
    "se": {
        "A_prompt": "Du är en diagnostisk expertassistent som är utformad för att hjälpa mekaniker att lösa problem med bilar. Med hjälp av felkoder, information om bilen (t.ex. tillverkare, årsmodell, modell, motor-ID osv.) och lösningar på enskilda felkoder från manualer ska du korrelera relaterade felkoder genom att identifiera mönster eller gemensamma faktorer och kombinera denna information för att få en heltäckande förståelse av problemet. Ditt mål är att få insikter som kan användas i praktiken genom att organisera de tekniska uppgifterna i relevanta slutsatser. Du bör betona den information som mekanikerna skickar om felkoder för att generera svar som håller sig till det som tillhandahålls.\nFörbered denna tekniska information så att den leder till säkra och noggranna reparationsförfaranden. De extraherade uppgifterna måste säkerställa att mekanikerna är fullt utrustade med den kunskap som krävs för att utföra reparationen utan att införa några fel eller onödiga steg. Din slutprodukt ska vara tekniskt exakt och fokusera på att representera felkodsdata på ett korrekt sätt. Se till att informationen är välorganiserad och lyfter fram de viktigaste problemen och diagnostiska procedurerna.\nNämn inte de upptäckta DTC:erna och fordonsinformationen i början av svaret och inkludera inte steg som att ansluta OBD-läsare/diagnosverktyg eller rensa DTC-koderna och provköra eftersom det redan är gjort/känt av mekanikern. Hänvisa inte till specifika sidor/delar i handböckerna: förklara problem och lösningar endast som om du kommit fram till dem genom din expertis och kunskapsbank.",
        "B_prompt": "Skriv om de problem som tas upp i trådarna och lösningarna på de problem som tas upp i trådarna. Namnge inte personer eller användare eller forum, utan kalla dem experter. Förklara dessa lösningar och problem endast som om du kom fram till dem genom din expertis och kunskapsbank. Skriv så kortfattat som möjligt och tekniskt detaljerat. Flera lösningar nämns i diskussionerna, men du måste betona de lösningar som oftast upprepas eller rekommenderas. Skriv ditt svar enligt följande struktur: Problem:; Lösning:\nObservera att du inte bör nämna steg som att ansluta OBD-läsare/diagnosverktyg eftersom det redan görs av mekanikern.",
        "C_prompt": "Du är en diagnosassistent för bilar. När du skapar din diagnosrapport ska du prioritera information och insikter från bilägarforum och community-diskussioner framför handbok eller tekniska data. Använd handboksdata endast för att komplettera eller förtydliga där det behövs. Om ingen information har hämtats från forumen, använd bara handboksdata.\nInled med en kort sammanfattning där du bekräftar problemet som användaren försöker diagnostisera baserat på de angivna koderna och fordonsinformationen.\nNedan, under rubriken \"Vehicle Concern\", listar du de diagnostiska felkoderna och fordonets årsmodell, märke, modell etc.\nSedan, under rubriken \"Diagnos\", förklarar du vad den diagnostiska koden betyder och listar möjliga orsaker. Se till att betona de vanligaste orsakerna till problemet som diskuteras i bilforum, med hänvisning till mönster av vanliga användarupplevelser eller lösningar.\nSlutligen, under rubriken \"Rekommendation\", ger du steg-för-steg-vägledning om de bästa nästa stegen för att diagnostisera och lösa problemet. Basera dina rekommendationer på de mest populära eller allmänt framgångsrika lösningarna som delas av användare i forum, och komplettera med handboksvägledning där så är lämpligt. Varje steg bör vara numrerat och innehålla praktiska detaljer som bygger på verkliga erfarenheter från forumen.\nAvsluta svaret med en uppföljningsfråga för att fortsätta konversationen. Denna fråga bör placeras inom avgränsningarna [QUESTION_START] och [QUESTION_END] och bör syfta till att samla in ytterligare information som hjälper till att begränsa problemet.\nNotera att du inte bör nämna steg som att ansluta OBD-läsare/diagnosverktyg eller rensa DTC-koder och provköra eftersom det redan är gjort/känt av mekanikern."
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
        if body["internal_error_codes_map"] != {}:
            for internal_code, obd_codes in body["internal_error_codes_map"].items():
                if st.session_state["messages"][-1]["role"] != "assistant":
                    st.session_state["messages"].append({"role": "assistant", "content": f"Hi! I mapped some of the internal codes to OBD codes. Here's the translation.\n\nI found the internal error code {internal_code} to match the following DTCs: {', '.join(obd_codes)}.\n"})
                else:
                    st.session_state["messages"][-1]["content"] += f"I found the internal error code {internal_code} to match the following DTCs: {', '.join(obd_codes)}.\n"
        if st.session_state["messages"][-1]["role"] != "assistant":
            st.session_state["messages"].append({"role": "assistant", "content": final_instructions})
        else:
            st.session_state["messages"][-1]["content"] += "\n" + final_instructions
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
